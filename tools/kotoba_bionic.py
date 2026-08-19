#!/usr/bin/env python3
"""Token-efficient Bionic bootstrap and session facade for Kotoba."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ITEM_ID = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z0-9-]+)+$")
SCORES = {"0", "0.25", "0.5", "0.75", "1", "1.0"}
MODES = {"meaning", "reading-with-furigana", "reading-no-furigana", "production", "grammar", "anki"}
REQUIRED_FILES = (
    "bionic/kotoba/SKILL.md",
    "bionic/INSTALL_PROMPT.md",
    "curriculum/catalog.json",
    "tools/kotoba_state.py",
    "tools/kotoba_session.py",
)
RUNTIME_DIRS = ("learner", "lessons", "exports/anki")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def tool_path(name: str) -> Path:
    return Path(__file__).resolve().with_name(name)


def run_tool(name: str, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(tool_path(name)), "--root", str(root), *arguments],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or f"{name} failed"
        raise RuntimeError(message)
    return result


def writable(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        descriptor, probe = tempfile.mkstemp(prefix=".kotoba-write-", dir=path)
        os.close(descriptor)
        Path(probe).unlink()
        return True
    except OSError:
        return False


def valid_skill(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    match = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return False
    frontmatter = match.group(1).splitlines()
    name_ok = any(line.strip() == "name: kotoba" for line in frontmatter)
    description_ok = any(
        line.strip().startswith('description: "') and line.strip().endswith('"') for line in frontmatter
    )
    return name_ok and description_ok and "[TODO:" not in text


def doctor_payload(root: Path) -> dict[str, Any]:
    missing = [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]
    invalid = []
    try:
        catalog = read_json(root / "curriculum" / "catalog.json")
        if catalog.get("schema_version") != 1 or not isinstance(catalog.get("items"), dict):
            invalid.append("curriculum/catalog.json")
    except (OSError, json.JSONDecodeError, AttributeError):
        invalid.append("curriculum/catalog.json")
    if not valid_skill(root / "bionic" / "kotoba" / "SKILL.md"):
        invalid.append("bionic/kotoba/SKILL.md")

    unwritable = [relative for relative in RUNTIME_DIRS if not writable(root / relative)]
    python_ok = sys.version_info >= (3, 9)
    ready = not missing and not invalid and not unwritable and python_ok
    return {
        "ready": ready,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "skill": "bionic/kotoba",
        "missing": missing,
        "invalid": sorted(set(invalid)),
        "unwritable": unwritable,
    }


def command_doctor(args: argparse.Namespace) -> None:
    payload = doctor_payload(args.root.resolve())
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    if not payload["ready"]:
        raise SystemExit(1)


def command_setup(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    for relative in RUNTIME_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    payload = doctor_payload(root)
    if not payload["ready"]:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        raise SystemExit(1)

    tests = "skipped"
    if args.run_tests:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            raise SystemExit(result.returncode)
        tests = "ok"
    print(
        f"OK ready=1 python={payload['python']} tests={tests} "
        f"skill={root / 'bionic' / 'kotoba'} next=install-skill"
    )


def command_prompt(args: argparse.Namespace) -> None:
    print((args.root.resolve() / "bionic" / "INSTALL_PROMPT.md").read_text(encoding="utf-8").strip())


def command_begin(args: argparse.Namespace) -> None:
    result = run_tool("kotoba_session.py", args.root.resolve(), "start")
    print(result.stdout.strip())


def command_items(args: argparse.Namespace) -> None:
    catalog = read_json(args.root.resolve() / "curriculum" / "catalog.json")
    selected = {}
    for item_id in args.item_ids:
        if not ITEM_ID.fullmatch(item_id):
            raise SystemExit(f"Invalid item id: {item_id}")
        if item_id not in catalog.get("items", {}):
            raise SystemExit(f"Unknown catalog item: {item_id}")
        selected[item_id] = catalog["items"][item_id]
    print(json.dumps(selected, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def validate_lesson(root: Path, lesson_arg: Path) -> str:
    path = lesson_arg if lesson_arg.is_absolute() else root / lesson_arg
    path = path.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError("lesson must be inside the project") from error
    lesson = read_json(path)
    required = ("id", "number", "date", "title", "goal", "items")
    missing = [key for key in required if key not in lesson]
    if missing:
        raise RuntimeError("lesson missing fields: " + ", ".join(missing))
    if not isinstance(lesson["items"], list):
        raise RuntimeError("lesson items must be a list")
    for item in lesson["items"]:
        if not isinstance(item, dict) or not ITEM_ID.fullmatch(str(item.get("id", ""))):
            raise RuntimeError("lesson contains an invalid item id")
    return str(relative)


def validate_result(value: str) -> None:
    try:
        item_id, score, mode = value.split(":", 2)
    except ValueError as error:
        raise RuntimeError("result must be ITEM_ID:SCORE:MODE") from error
    if not ITEM_ID.fullmatch(item_id):
        raise RuntimeError(f"invalid result item id: {item_id}")
    if score not in SCORES:
        raise RuntimeError(f"invalid result score: {score}")
    if mode not in MODES:
        raise RuntimeError(f"invalid result mode: {mode}")


def command_finish(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    lesson = validate_lesson(root, args.lesson) if args.lesson else None
    if lesson and not (root / "learner" / "profile.json").exists():
        raise RuntimeError("cannot checkpoint a lesson before profile initialization")
    for item_id in args.known or []:
        if not ITEM_ID.fullmatch(item_id):
            raise RuntimeError(f"invalid known item id: {item_id}")
    for result in args.results or []:
        validate_result(result)
    if args.known:
        run_tool("kotoba_state.py", root, "mark-known", *args.known)
    if args.results:
        arguments = ["record-batch"]
        for result in args.results:
            arguments.extend(("--result", result))
        if lesson:
            arguments.extend(("--lesson", lesson))
        run_tool("kotoba_state.py", root, *arguments)
    checkpoint = run_tool("kotoba_session.py", root, "checkpoint").stdout.strip()
    print(
        f"OK known={len(args.known or [])} results={len(args.results or [])} "
        f"lesson={lesson or '-'} checkpoint={json.dumps(checkpoint, ensure_ascii=False)}"
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=Path.cwd(), help="Kotoba project root")
    commands = result.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="Prepare and validate the Bionic workspace")
    setup.add_argument("--run-tests", action="store_true")
    setup.set_defaults(handler=command_setup)
    doctor = commands.add_parser("doctor", help="Return a compact environment health report")
    doctor.set_defaults(handler=command_doctor)
    prompt = commands.add_parser("prompt", help="Print the Bionic installation prompt")
    prompt.set_defaults(handler=command_prompt)
    begin = commands.add_parser("begin", help="Return compact cross-chat context")
    begin.set_defaults(handler=command_begin)
    items = commands.add_parser("items", help="Return only requested curriculum items")
    items.add_argument("item_ids", nargs="+")
    items.set_defaults(handler=command_items)
    finish = commands.add_parser("finish", help="Batch state changes and checkpoint the chat")
    finish.add_argument("--known", action="append")
    finish.add_argument("--result", dest="results", action="append")
    finish.add_argument("--lesson", type=Path)
    finish.set_defaults(handler=command_finish)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as error:
        print(f"Kotoba Bionic error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
