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

    def test_default_interface_language_is_russian(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_state(root, "init", "--name", "Test", "--goal", "conversation")
            settings = json.loads((root / "learner" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["interface_language"], "ru")

    def test_failed_check_downgrades_reported_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_state(root, "init", "--name", "Test", "--goal", "jlpt")
            self.run_state(root, "mark-known", "grammar.topic-wa")
            self.run_state(root, "record", "grammar.topic-wa", "--score", "0.25", "--mode", "grammar")
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"]["grammar.topic-wa"]["status"], "learning")

    def test_batch_records_multiple_results_with_one_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_state(root, "init", "--name", "Test", "--goal", "conversation")
            result = self.run_state(
                root,
                "record-batch",
                "--result",
                "vocab.gakusei:1:meaning",
                "--result",
                "grammar.topic-wa:0.5:grammar",
                "--lesson",
                "lessons/lesson-001.json",
            )
            self.assertEqual(len(json.loads(result.stdout)), 2)
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"]["vocab.gakusei"]["history"][0]["score"], 1)
            self.assertEqual(
                mastery["items"]["grammar.topic-wa"]["history"][0]["lesson"], "lessons/lesson-001.json"
            )


class SessionToolTests(unittest.TestCase):
    def run_tool(self, tool: str, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / tool), "--root", str(root), *arguments],
            check=True,
            text=True,
            capture_output=True,
        )

    def test_checkpoint_writes_only_after_progress_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_tool("kotoba_state.py", root, "init", "--name", "Test", "--goal", "conversation")
            start = self.run_tool("kotoba_session.py", root, "start")
            self.assertTrue(json.loads(start.stdout)["initialized"])

            unchanged = self.run_tool("kotoba_session.py", root, "checkpoint")
            self.assertIn("checkpoint skipped", unchanged.stdout)

            self.run_tool(
                "kotoba_state.py",
                root,
                "record",
                "vocab.gakusei",
                "--score",
                "0.25",
                "--mode",
                "meaning",
            )
            changed = self.run_tool("kotoba_session.py", root, "checkpoint")
            self.assertIn("progress", changed.stdout)
            context = json.loads((root / "learner" / "context.json").read_text(encoding="utf-8"))
            self.assertEqual(context["progress"]["focus"][0]["id"], "vocab.gakusei")
            events = (root / "learner" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(events[-1])["type"], "chat_checkpoint")


class BionicToolTests(unittest.TestCase):
    def run_bionic(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "kotoba_bionic.py"), "--root", str(root), *arguments],
            check=True,
            text=True,
            capture_output=True,
        )

    def test_doctor_accepts_repository_environment(self) -> None:
        result = self.run_bionic(ROOT, "doctor")
        self.assertTrue(json.loads(result.stdout)["ready"])

    def test_finish_batches_results_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "kotoba_state.py"),
                    "--root",
                    str(root),
                    "init",
                    "--name",
                    "Test",
                    "--goal",
                    "conversation",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "kotoba_session.py"),
                    "--root",
                    str(root),
                    "start",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = self.run_bionic(
                root,
                "finish",
                "--known",
                "grammar.topic-wa",
                "--result",
                "vocab.gakusei:0.75:meaning",
            )
            self.assertIn("results=1", result.stdout)
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"]["grammar.topic-wa"]["status"], "reported_known")
            self.assertEqual(mastery["items"]["vocab.gakusei"]["recent_average"], 0.75)
            events = (root / "learner" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(events[-1])["type"], "chat_checkpoint")

    def test_finish_rejects_entire_invalid_batch_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "kotoba_state.py"),
                    "--root",
                    str(root),
                    "init",
                    "--name",
                    "Test",
                    "--goal",
                    "conversation",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "kotoba_bionic.py"),
                    "--root",
                    str(root),
                    "finish",
                    "--known",
                    "grammar.topic-wa",
                    "--result",
                    "invalid:0.75:meaning",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            mastery = json.loads((root / "learner" / "mastery.json").read_text(encoding="utf-8"))
            self.assertEqual(mastery["items"], {})


class AnkiToolTests(unittest.TestCase):
    def test_lesson_preview_uses_subdeck_and_managed_tags(self) -> None:
        deck, cards = lesson_cards(ROOT / "examples" / "lesson-001.json")
        self.assertEqual(deck, "Kotoba::001 — Знакомство")
        self.assertEqual(len(cards), 2)
        self.assertIn("kotoba-managed", cards[0]["tags"])
        self.assertTrue(cards[0]["tag"].startswith("kotoba-id-"))


if __name__ == "__main__":
    unittest.main()
