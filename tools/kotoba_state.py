#!/usr/bin/env python3
"""Deterministic local learner-state manager for Kotoba."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ITEM_ID = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z0-9-]+)+$")
FURIGANA = ("always", "learning", "adaptive", "never")
GOALS = ("jlpt", "conversation")
MODES = ("meaning", "reading-with-furigana", "reading-no-furigana", "production", "grammar", "anki")


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


def append_event(root: Path, event: dict[str, Any]) -> None:
    path = root / "learner" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def paths(root: Path) -> tuple[Path, Path, Path]:
    learner = root / "learner"
    return learner / "profile.json", learner / "settings.json", learner / "mastery.json"


def require_profile(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    profile_path, settings_path, mastery_path = paths(root)
    profile = read_json(profile_path)
    if profile is None:
        raise SystemExit("Kotoba profile not found. Run: python3 tools/kotoba_state.py init ...")
    return profile, read_json(settings_path, {}), read_json(mastery_path, {"items": {}})


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def validate_minutes(value: Any) -> int:
    minutes = int(value)
    if not 5 <= minutes <= 180:
        raise argparse.ArgumentTypeError("minutes must be between 5 and 180")
    return minutes


def validate_item_id(item_id: str) -> str:
    if not ITEM_ID.fullmatch(item_id):
        raise SystemExit(f"Invalid item id: {item_id}")
    return item_id


def parse_result(value: str) -> tuple[str, float, str]:
    try:
        item_id, score_text, mode = value.split(":", 2)
        score = float(score_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("result must be ITEM_ID:SCORE:MODE") from error
    if not ITEM_ID.fullmatch(item_id):
        raise argparse.ArgumentTypeError(f"invalid item id: {item_id}")
    if score not in (0, 0.25, 0.5, 0.75, 1):
        raise argparse.ArgumentTypeError("score must be 0, 0.25, 0.5, 0.75, or 1")
    if mode not in MODES:
        raise argparse.ArgumentTypeError(f"invalid mode: {mode}")
    return item_id, score, mode


def command_init(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    profile_path, settings_path, mastery_path = paths(root)
    if profile_path.exists() and not args.force:
        raise SystemExit("Profile already exists. Use configure, or init --force to replace it.")
    timestamp = now()
    profile = {
        "schema_version": 1,
        "learner_name": args.name,
        "assumed_baseline": "kana-known",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    settings = {
        "schema_version": 1,
        "goal": args.goal,
        "lesson_minutes": args.minutes,
        "furigana": args.furigana,
        "interface_language": args.language,
        "anki": {"enabled": args.anki, "parent_deck": "Kotoba"},
    }
    write_json(profile_path, profile)
    write_json(settings_path, settings)
    write_json(mastery_path, {"schema_version": 1, "items": {}})
    events_path = root / "learner" / "events.jsonl"
    if args.force and events_path.exists():
        events_path.rename(events_path.with_name(f"events-{timestamp.replace(':', '-')}.bak.jsonl"))
    append_event(root, {"type": "profile_initialized", "at": timestamp, "settings": settings})
    print(f"Initialized Kotoba profile for {args.name} ({args.goal}, {args.minutes} min).")


def command_configure(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    profile, settings, _ = require_profile(root)
    changed: dict[str, Any] = {}
    for key, value in (("goal", args.goal), ("lesson_minutes", args.minutes), ("furigana", args.furigana)):
        if value is not None:
            settings[key] = value
            changed[key] = value
    if args.anki is not None:
        settings.setdefault("anki", {})["enabled"] = args.anki
        changed["anki.enabled"] = args.anki
    if not changed:
        raise SystemExit("No settings supplied.")
    profile["updated_at"] = now()
    profile_path, settings_path, _ = paths(root)
    write_json(profile_path, profile)
    write_json(settings_path, settings)
    append_event(root, {"type": "settings_changed", "at": now(), "changes": changed})
    print(json.dumps(changed, ensure_ascii=False, sort_keys=True))


def command_mark_known(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    _, _, mastery = require_profile(root)
    for item_id in args.item_ids:
        validate_item_id(item_id)
    timestamp = now()
    events = []
    for item_id in args.item_ids:
        item = mastery.setdefault("items", {}).setdefault(item_id, {"history": [], "modes": {}})
        item["status"] = "reported_known"
        item["reported_known_at"] = timestamp
        events.append({"type": "reported_known", "at": timestamp, "item_id": item_id})
    write_json(paths(root)[2], mastery)
    for event in events:
        append_event(root, event)
    print(f"Marked {len(args.item_ids)} item(s) as reported known.")


def mastery_status(item: dict[str, Any]) -> str:
    history = item.get("history", [])
    if not history:
        return item.get("status", "new")
    recent = [float(entry["score"]) for entry in history[-3:]]
    if recent[-1] < 0.5:
        return "learning"
    if len(recent) == 3 and sum(recent) / 3 >= 0.8:
        return "mastered"
    if item.get("status") == "reported_known" and recent[-1] >= 0.5:
        return "reported_known"
    return "learning"


def record_result(
    mastery: dict[str, Any], item_id: str, score: float, mode_name: str, lesson: Path | None, timestamp: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    entry = {"at": timestamp, "score": score, "mode": mode_name}
    if lesson:
        entry["lesson"] = str(lesson)
    item = mastery.setdefault("items", {}).setdefault(item_id, {"history": [], "modes": {}})
    item.setdefault("history", []).append(entry)
    mode = item.setdefault("modes", {}).setdefault(mode_name, {"attempts": 0, "scores": []})
    mode["attempts"] += 1
    mode["scores"].append(score)
    mode["scores"] = mode["scores"][-10:]
    mode["average"] = round(sum(mode["scores"]) / len(mode["scores"]), 3)
    item["status"] = mastery_status(item)
    item["last_seen_at"] = timestamp
    item["recent_average"] = round(sum(x["score"] for x in item["history"][-3:]) / min(3, len(item["history"])), 3)
    event = {"type": "assessment", "item_id": item_id, **entry, "status": item["status"]}
    result = {"item_id": item_id, "status": item["status"], "recent_average": item["recent_average"]}
    return event, result


def command_record(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    validate_item_id(args.item_id)
    _, _, mastery = require_profile(root)
    event, result = record_result(mastery, args.item_id, args.score, args.mode, args.lesson, now())
    write_json(paths(root)[2], mastery)
    append_event(root, event)
    print(json.dumps(result, ensure_ascii=False))


def command_record_batch(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    _, _, mastery = require_profile(root)
    timestamp = now()
    events = []
    results = []
    for item_id, score, mode_name in args.results:
        event, result = record_result(mastery, item_id, score, mode_name, args.lesson, timestamp)
        events.append(event)
        results.append(result)
    write_json(paths(root)[2], mastery)
    for event in events:
        append_event(root, event)
    print(json.dumps(results, ensure_ascii=False, separators=(",", ":")))


def summary_payload(root: Path) -> dict[str, Any]:
    profile, settings, mastery = require_profile(root)
    grouped: dict[str, list[str]] = {"new": [], "reported_known": [], "learning": [], "mastered": []}
    for item_id, item in sorted(mastery.get("items", {}).items()):
        grouped.setdefault(item.get("status", "new"), []).append(item_id)
    return {"profile": profile, "settings": settings, "progress": grouped, "tracked_items": sum(len(v) for v in grouped.values())}


def command_summary(args: argparse.Namespace) -> None:
    payload = summary_payload(args.root.resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(f"Ученик: {payload['profile']['learner_name']}")
    print(f"Цель: {payload['settings']['goal']}; урок: {payload['settings']['lesson_minutes']} мин; фуригана: {payload['settings']['furigana']}")
    print(f"Anki: {'включён' if payload['settings']['anki']['enabled'] else 'выключен'}")
    for status in ("reported_known", "learning", "mastered"):
        print(f"{status}: {len(payload['progress'][status])}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path.cwd(), help="Kotoba project root")
    subparsers = result.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--name", required=True)
    init.add_argument("--goal", choices=GOALS, required=True)
    init.add_argument("--minutes", type=validate_minutes, default=25)
    init.add_argument("--furigana", choices=FURIGANA, default="adaptive")
    init.add_argument("--language", default="ru")
    init.add_argument("--anki", type=parse_bool, default=False)
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)

    configure = subparsers.add_parser("configure")
    configure.add_argument("--goal", choices=GOALS)
    configure.add_argument("--minutes", type=validate_minutes)
    configure.add_argument("--furigana", choices=FURIGANA)
    configure.add_argument("--anki", type=parse_bool)
    configure.set_defaults(handler=command_configure)

    known = subparsers.add_parser("mark-known")
    known.add_argument("item_ids", nargs="+")
    known.set_defaults(handler=command_mark_known)

    record = subparsers.add_parser("record")
    record.add_argument("item_id")
    record.add_argument("--score", required=True, type=float, choices=(0, 0.25, 0.5, 0.75, 1))
    record.add_argument("--mode", required=True, choices=MODES)
    record.add_argument("--lesson", type=Path)
    record.set_defaults(handler=command_record)

    batch = subparsers.add_parser("record-batch")
    batch.add_argument("--result", dest="results", action="append", type=parse_result, required=True)
    batch.add_argument("--lesson", type=Path)
    batch.set_defaults(handler=command_record_batch)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    summary.set_defaults(handler=command_summary)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Kotoba state error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
