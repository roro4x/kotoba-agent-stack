#!/usr/bin/env python3
"""Install Kotoba skills by copying them into a discovery directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex-user", "lmstudio-user", "custom"), default="codex-user")
    parser.add_argument("--path", type=Path, help="Required with --target custom")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    source = root / "skills"
    if args.target == "codex-user":
        target = Path.home() / ".agents" / "skills"
    elif args.target == "lmstudio-user":
        target = Path.home() / ".lmstudio" / "skills"
    else:
        if args.path is None:
            parser.error("--path is required with --target custom")
        target = args.path.expanduser().resolve()

    target.mkdir(parents=True, exist_ok=True)
    for skill in sorted(source.iterdir()):
        if not (skill / "SKILL.md").exists():
            continue
        destination = target / skill.name
        if destination.exists():
            if not args.replace:
                raise SystemExit(f"Already exists: {destination}. Use --replace to update it.")
            shutil.rmtree(destination)
        shutil.copytree(skill, destination)
        print(f"Installed {skill.name} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
