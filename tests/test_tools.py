from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from kotoba_anki import lesson_cards  # noqa: E402


class StateToolTests(unittest.TestCase):
    def run_state(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "kotoba_state.py"), "--root", str(root), *arguments],
            check=True,
            text=True,
            capture_output=True,
        )

    def test_reported_known_can_be_verified_as_mastered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_state(root, "init", "--name", "Test", "--goal", "conversation")
            self.run_state(root, "mark-known", "vocab.gakusei")
            self.run_state(root, "record", "vocab.gakusei", "--score", "0.75", "--mode", "meaning")
            self.run_state(root, "record", "vocab.gakusei", "--score", "0.75", "--mode", "reading-no-furigana")
            self.run_state(root, "record", "vocab.gakusei", "--score", "1", "--mode", "production")
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"]["vocab.gakusei"]["status"], "mastered")

    def test_failed_check_downgrades_reported_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_state(root, "init", "--name", "Test", "--goal", "jlpt")
            self.run_state(root, "mark-known", "grammar.topic-wa")
            self.run_state(root, "record", "grammar.topic-wa", "--score", "0.25", "--mode", "grammar")
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"]["grammar.topic-wa"]["status"], "learning")


class AnkiToolTests(unittest.TestCase):
    def test_lesson_preview_uses_subdeck_and_managed_tags(self) -> None:
        deck, cards = lesson_cards(ROOT / "examples" / "lesson-001.json")
        self.assertEqual(deck, "Kotoba::001 — Знакомство")
        self.assertEqual(len(cards), 2)
        self.assertIn("kotoba-managed", cards[0]["tags"])
        self.assertTrue(cards[0]["tag"].startswith("kotoba-id-"))


if __name__ == "__main__":
    unittest.main()
