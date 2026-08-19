#!/usr/bin/env python3
"""Safe, dry-run-first AnkiConnect adapter for Kotoba lessons."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def invoke(url: str, action: str, **params: Any) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            decoded = json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"AnkiConnect unavailable at {url}: {error}") from error
    if decoded.get("error"):
        raise RuntimeError(f"AnkiConnect {action}: {decoded['error']}")
    return decoded.get("result")


def safe_tag(item_id: str) -> str:
    return "kotoba-id-" + re.sub(r"[^a-zA-Z0-9_-]+", "-", item_id).strip("-")


def lesson_cards(path: Path) -> tuple[str, list[dict[str, Any]]]:
    lesson = read_json(path)
    required_lesson = ("number", "title", "items")
    missing = [key for key in required_lesson if key not in lesson]
    if missing:
        raise ValueError(f"lesson missing: {', '.join(missing)}")
    deck = f"Kotoba::{int(lesson['number']):03d} — {lesson['title']}"
    cards: list[dict[str, Any]] = []
    for item in lesson["items"]:
        missing_item = [key for key in ("id", "expression", "reading", "meaning") if not item.get(key)]
        if missing_item:
            raise ValueError(f"item {item.get('id', '?')} missing: {', '.join(missing_item)}")
        tags = ["kotoba-managed", safe_tag(item["id"]), f"lesson-{int(lesson['number']):03d}"]
        tags.extend(str(tag) for tag in item.get("tags", []))
        if item.get("type"):
            tags.append(str(item["type"]))
        example = html.escape(str(item.get("example", "")))
        example_reading = html.escape(str(item.get("example_reading", "")))
        example_block = ""
        if example:
            example_block = f"<br><br>{example}"
            if example_reading:
                example_block += f"<br><small>{example_reading}</small>"
        cards.append({
            "item_id": item["id"],
            "tag": safe_tag(item["id"]),
            "deck": deck,
            "front": html.escape(str(item["expression"])),
            "back": f"{html.escape(str(item['reading']))}<br>{html.escape(str(item['meaning']))}{example_block}",
            "tags": sorted(set(tags)),
        })
    return deck, cards


def ensure_enabled(root: Path) -> None:
    settings_path = root / "learner" / "settings.json"
    if not settings_path.exists():
        raise RuntimeError("Kotoba settings not found. Run kotoba_state.py init first.")
    settings = read_json(settings_path)
    if not settings.get("anki", {}).get("enabled", False):
        raise RuntimeError("Anki is disabled in learner/settings.json. Enable it explicitly first.")


def apply_cards(url: str, deck: str, cards: list[dict[str, Any]]) -> list[dict[str, str]]:
    invoke(url, "version")
    invoke(url, "createDeck", deck=deck)
    results: list[dict[str, str]] = []
    for card in cards:
        note_ids = invoke(url, "findNotes", query=f"tag:kotoba-managed tag:{card['tag']}")
        fields = {"Front": card["front"], "Back": card["back"]}
        if not note_ids:
            note = {
                "deckName": deck,
                "modelName": "Basic",
                "fields": fields,
                "options": {"allowDuplicate": False},
                "tags": card["tags"],
            }
            invoke(url, "addNote", note=note)
            results.append({"item_id": card["item_id"], "action": "created"})
            continue
        if len(note_ids) > 1:
            results.append({"item_id": card["item_id"], "action": "ambiguous-skipped"})
            continue
        info = invoke(url, "notesInfo", notes=note_ids)
        if not info or "kotoba-managed" not in info[0].get("tags", []):
            results.append({"item_id": card["item_id"], "action": "unmanaged-skipped"})
            continue
        note_id = note_ids[0]
        invoke(url, "updateNoteFields", note={"id": note_id, "fields": fields})
        invoke(url, "addTags", notes=[note_id], tags=" ".join(card["tags"]))
        results.append({"item_id": card["item_id"], "action": "updated"})
    return results


def collect_stats(url: str, root: Path) -> dict[str, Any]:
    invoke(url, "version")
    card_ids = invoke(url, "findCards", query="tag:kotoba-managed")
    cards = invoke(url, "cardsInfo", cards=card_ids) if card_ids else []
    note_ids = sorted({card["note"] for card in cards})
    notes = invoke(url, "notesInfo", notes=note_ids) if note_ids else []
    tags_by_note = {note["noteId"]: note.get("tags", []) for note in notes}
    items: dict[str, dict[str, Any]] = {}
    for card in cards:
        item_tag = next((tag for tag in tags_by_note.get(card["note"], []) if tag.startswith("kotoba-id-")), None)
        if not item_tag:
            continue
        items[item_tag] = {
            "card_id": card["cardId"],
            "deck": card.get("deckName"),
            "repetitions": card.get("reps", 0),
            "lapses": card.get("lapses", 0),
            "interval": card.get("interval", card.get("ivl", 0)),
            "due": card.get("due"),
        }
    result = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": items}
    write_json(root / "exports" / "anki" / "stats.json", result)
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("lesson", type=Path, nargs="?")
    result.add_argument("--apply", action="store_true", help="Apply the previewed changes")
    result.add_argument("--stats", action="store_true", help="Read managed-card statistics")
    result.add_argument("--url", default="http://127.0.0.1:8765")
    result.add_argument("--root", type=Path, default=Path.cwd())
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.root.resolve()
    try:
        if args.stats:
            ensure_enabled(root)
            print(json.dumps(collect_stats(args.url, root), ensure_ascii=False, indent=2))
            return 0
        if args.lesson is None:
            raise ValueError("lesson path is required unless --stats is used")
        deck, cards = lesson_cards(args.lesson)
        preview = {"mode": "apply" if args.apply else "dry-run", "deck": deck, "cards": cards}
        write_json(root / "exports" / "anki" / f"{args.lesson.stem}-preview.json", preview)
        if not args.apply:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0
        ensure_enabled(root)
        print(json.dumps(apply_cards(args.url, deck, cards), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Kotoba Anki error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
