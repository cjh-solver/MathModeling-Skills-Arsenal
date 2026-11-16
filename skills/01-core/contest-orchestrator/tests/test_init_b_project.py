"""Project initialization must preserve inputs and existing contest records."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import init_b_project


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes() if path.is_file() else None,
            path.stat().st_mtime_ns,
        )
        for path in root.rglob("*")
    }


class BProjectInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.template = self.root / "template"
        for name in (".contest/task_cards", "paper", "figures"):
            (self.template / name).mkdir(parents=True)
        card = self.template / ".contest/task_cards/H5.yaml"
        card.write_text("project: PLACEHOLDER_PROJECT_NAME\ndate: PLACEHOLDER_DATE\n", encoding="utf-8")
        control = {
            "dispatch_records": [{
                "task_card_path": ".contest/task_cards/H5.yaml",
                "task_card_sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
            }],
        }
        (self.template / ".contest/harness_control.yaml").write_text(
            yaml.safe_dump(control), encoding="utf-8",
        )
        (self.template / ".contest/approval_log.yaml").write_text("approvals: []\n", encoding="utf-8")
        (self.template / "model_contract.yaml").write_text(
            "project: PLACEHOLDER_PROJECT_NAME\ndate: '2026-09-XX'\n", encoding="utf-8",
        )
        self.template_patch = patch.object(init_b_project, "TEMPLATE_DIR", self.template)
        self.template_patch.start()
        self.addCleanup(self.template_patch.stop)

    def test_fresh_project_keeps_empty_directories_and_refreshes_task_hash(self):
        result = init_b_project.init_project(self.project, "测试项目", "2026-11-17")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["files_copied"], 4)
        self.assertTrue((self.project / "paper").is_dir())
        self.assertTrue((self.project / "figures").is_dir())
        self.assertTrue((self.project / "README.md").is_file())
        model = yaml.safe_load((self.project / "model_contract.yaml").read_text(encoding="utf-8"))
        self.assertEqual(model, {"project": "测试项目", "date": "2026-11-17"})
        control = yaml.safe_load((self.project / ".contest/harness_control.yaml").read_text(encoding="utf-8"))
        card = self.project / ".contest/task_cards/H5.yaml"
        self.assertEqual(control["dispatch_records"][0]["task_card_sha256"], hashlib.sha256(card.read_bytes()).hexdigest())

    def test_preexisting_input_files_are_not_rewritten(self):
        (self.project / "data").mkdir(parents=True)
        source = self.project / "data/input.yaml"
        source.write_bytes(b"name: PLACEHOLDER_PROJECT_NAME\ndate: 2026-09-XX\n")
        problem = self.project / "problem_statement.md"
        problem.write_text("User-provided problem", encoding="utf-8")
        before = snapshot(self.project)

        init_b_project.init_project(self.project, "New project", "2026-11-17")

        after = snapshot(self.project)
        for name in ("data/input.yaml", "problem_statement.md"):
            self.assertEqual(after[name], before[name], name)

    def test_conflicts_are_rejected_before_any_files_are_created(self):
        for name in ("model_contract.yaml", ".contest/approval_log.yaml", ".contest/harness_control.yaml", "README.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=self.root) as raw:
                project = Path(raw)
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("Existing user record\n", encoding="utf-8")
                before = snapshot(project)

                with self.assertRaises(FileExistsError) as caught:
                    init_b_project.init_project(project)

                self.assertIn(name, str(caught.exception).replace("\\", "/"))
                self.assertEqual(snapshot(project), before)

    def test_file_occupying_a_template_directory_is_rejected_without_writes(self):
        self.project.mkdir()
        (self.project / ".contest").write_text("User input", encoding="utf-8")
        before = snapshot(self.project)

        with self.assertRaises((FileExistsError, NotADirectoryError)):
            init_b_project.init_project(self.project)

        self.assertEqual(snapshot(self.project), before)

    def test_target_must_be_a_directory(self):
        self.project.write_text("User input", encoding="utf-8")

        with self.assertRaises((FileExistsError, NotADirectoryError)):
            init_b_project.init_project(self.project)

        self.assertEqual(self.project.read_text(encoding="utf-8"), "User input")

    def test_repeated_initialization_preserves_records_and_manual_edits(self):
        init_b_project.init_project(self.project)
        (self.project / ".contest/approval_log.yaml").write_text(
            "approvals:\n- gate: H5\n  decision: approved\n", encoding="utf-8",
        )
        before = snapshot(self.project)

        with self.assertRaises(FileExistsError):
            init_b_project.init_project(self.project, "Another name")

        self.assertEqual(snapshot(self.project), before)

    def test_cli_reports_conflicts_without_writing_files(self):
        self.project.mkdir()
        (self.project / "README.md").write_text("User instructions", encoding="utf-8")
        before = snapshot(self.project)

        result = subprocess.run(
            [sys.executable, "-X", "utf8", init_b_project.__file__, str(self.project)],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("README.md", result.stderr)
        self.assertEqual(snapshot(self.project), before)

    def test_linked_template_directory_does_not_receive_generated_files(self):
        self.project.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.project / ".contest").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Directory symlinks are unavailable: {exc}")

        with self.assertRaises(FileExistsError):
            init_b_project.init_project(self.project)

        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual([path.name for path in self.project.iterdir()], [".contest"])

    def test_shipped_template_initializes_without_changing_template_sources(self):
        self.template_patch.stop()
        source_before = snapshot(init_b_project.TEMPLATE_DIR)

        result = init_b_project.init_project(self.project, "初始化测试", "2026-11-17")

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["files_copied"], 20)
        self.assertTrue((self.project / "model_summary_cards.yaml").is_file())
        self.assertTrue((self.project / "h6_verification_scope.yaml").is_file())
        self.assertEqual(snapshot(init_b_project.TEMPLATE_DIR), source_before)


if __name__ == "__main__":
    unittest.main()
