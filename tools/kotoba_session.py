#!/usr/bin/env python3
"""Build a compact chat context and checkpoint changed Kotoba state."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def source_files(root: Path) -> list[Path]:
    files = [root / "learner" / name for name in ("profile.json", "settings.json", "mastery.json")]
    lessons = root / "lessons"
    if lessons.exists():
        files.extend(sorted(lessons.glob("*.json")))
    return [path for path in files if path.exists()]


def source_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in source_files(root):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def item_label(item_id: str, catalog: dict[str, Any]) -> str:
    item = catalog.get("items", {}).get(item_id, {})
    return item.get("label") or item.get("expression") or item.get("meaning") or item_id


def build_context(root: Path) -> dict[str, Any]:
    learner = root / "learner"
    profile = read_json(learner / "profile.json")
    if profile is None:
        return {"schema_version": 1, "initialized": False, "source_hash": source_hash(root)}

    settings = read_json(learner / "settings.json", {})
    mastery = read_json(learner / "mastery.json", {"items": {}})
    catalog = read_json(root / "curriculum" / "catalog.json", {"items": {}})
    items = mastery.get("items", {})
    statuses = {item_id: item.get("status", "new") for item_id, item in items.items()}
    counts = {status: 0 for status in ("new", "reported_known", "learning", "mastered")}
    for status in statuses.values():
        counts[status] = counts.get(status, 0) + 1
    catalog_ids = set(catalog.get("items", {}))
    counts["new"] = len(catalog_ids - set(statuses))

    focus = []
    focus_items = sorted(
        ((item_id, item) for item_id, item in items.items() if item.get("status") in {"learning", "reported_known"}),
        key=lambda pair: (pair[1].get("status") != "learning", pair[1].get("recent_average", 1), pair[0]),
    )
    for item_id, item in focus_items[:12]:
        focus.append(
            {
                "id": item_id,
                "status": item.get("status", "new"),
                "average": item.get("recent_average"),
                "label": item_label(item_id, catalog),
            }
        )

    candidates = []
    for item_id, item in catalog.get("items", {}).items():
        if item_id in statuses:
            continue
        requirements = item.get("requires", [])
        if all(statuses.get(required) in {"reported_known", "mastered"} for required in requirements):
            candidates.append(
                {
                    "id": item_id,
                    "type": item.get("type"),
                    "label": item_label(item_id, catalog),
                }
            )
        if len(candidates) == 8:
            break

    latest_lesson = None
    lesson_paths = sorted((root / "lessons").glob("*.json")) if (root / "lessons").exists() else []
    if lesson_paths:
        lesson = read_json(lesson_paths[-1], {})
        latest_lesson = {
            "path": str(lesson_paths[-1].relative_to(root)),
            "id": lesson.get("id"),
            "date": lesson.get("date"),
            "title": lesson.get("title"),
            "items": [item.get("id") for item in lesson.get("items", []) if item.get("id")],
        }

    return {
        "schema_version": 1,
        "initialized": True,
        "generated_at": now(),
        "source_hash": source_hash(root),
        "learner": {
            "name": profile.get("learner_name"),
            "baseline": profile.get("assumed_baseline"),
        },
        "settings": settings,
        "progress": {"counts": counts, "focus": focus, "candidates": candidates},
        "latest_lesson": latest_lesson,
    }


def context_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    sections = []
    for key in ("learner", "settings", "progress", "latest_lesson"):
        if before.get(key) != after.get(key):
            sections.append(key)
    return sections or ["state"]


def append_checkpoint(root: Path, changes: list[str], reason: str) -> None:
    event = {"type": "chat_checkpoint", "at": now(), "changed": changes, "reason": reason}
    path = root / "learner" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def emit(context: dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def command_start(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    context_path = root / "learner" / "context.json"
    previous = read_json(context_path, {})
    current = build_context(root)
    if current["initialized"]:
        if previous and previous.get("source_hash") != current["source_hash"]:
            append_checkpoint(root, context_changes(previous, current), "recovered-at-start")
        write_json(context_path, current)
    emit(current, args.pretty)


def command_checkpoint(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    context_path = root / "learner" / "context.json"
    previous = read_json(context_path, {})
    current = build_context(root)
    if not current["initialized"]:
        print("Kotoba profile is not initialized; checkpoint skipped.")
        return
    if previous.get("source_hash") == current["source_hash"]:
        print("No learner-state or lesson changes; checkpoint skipped.")
        return
    changes = context_changes(previous, current)
    write_json(context_path, current)
    append_checkpoint(root, changes, "chat-end")
    print("Checkpoint saved: " + ", ".join(changes))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path.cwd(), help="Kotoba project root")
    commands = result.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Print compact context and establish a chat baseline")
    start.add_argument("--pretty", action="store_true")
    start.set_defaults(handler=command_start)
    checkpoint = commands.add_parser("checkpoint", help="Persist compact context only when source state changed")
    checkpoint.set_defaults(handler=command_checkpoint)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Kotoba session error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
