import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import app


class PaperSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        (self.project / ".contest").mkdir(parents=True)
        self.links = self.base / "links.json"
        self.addCleanup(patch.stopall)
        patch.object(app, "discover_projects", return_value=[]).start()
        self.plan = {
            "chapter_order": ["abstract", "analysis", "Q1"],
            "writing_order": ["Q1", "analysis", "abstract"],
            "chapters": [{"chapter_id": "analysis", "title": "问题分析"},
                         {"chapter_id": "Q1", "title": "配置模型"}],
        }
        self.save("paper/Q1.tex", "已登记的合成模型章节。")
        self.save("paper/分析.tex", "已登记的合成问题分析。")
        self.save("plan.yaml", self.plan)
        self.control = {
            "active_mode": "full-contest-harness", "visual_workflow": "chapter_parallel",
            "nodes": {"H7": {"writer_preparation": {
                "writing_plan": self.reference("plan.yaml"),
                "chapters": [
                    {"chapter_id": "Q1", "draft": self.reference("paper/Q1.tex")},
                    {"chapter_id": "analysis", "draft": self.reference("paper/分析.tex")},
                ],
            }}},
        }
        self.write_control()

    def save(self, name, value):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, allow_unicode=True) if isinstance(value, dict) else value, encoding="utf-8")
        return path

    def reference(self, name):
        return {"path": name, "sha256": hashlib.sha256((self.project / name).read_bytes()).hexdigest()}

    def write_control(self):
        self.save(".contest/harness_control.yaml", self.control)

    def state(self):
        return app.build_state(self.project, self.links)

    def test_final_order_titles_and_authored_record_order_remain_separate(self):
        state = self.state()
        self.assertEqual(state["writing_plan"]["chapter_order"], ["abstract", "analysis", "Q1"])
        self.assertEqual(state["writing_plan"]["chapters"][1], {"id": "Q1", "title": "配置模型"})
        self.assertEqual([item["id"] for item in state["chapters"]], ["Q1", "analysis"])
        self.assertTrue(all(item["draft_available"] for item in state["chapters"]))
        self.assertTrue(all(item["draft_previewable"] for item in state["chapters"]))
        self.assertIsNone(state["paper_pdf"])
        self.assertEqual(state["approvals"], [])

    def test_reading_does_not_rewrite_files_or_create_approvals(self):
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.project.rglob("*") if path.is_file()}
        self.state()
        after = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                 for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertFalse((self.project / ".contest/approval_log.yaml").exists())

    def test_file_availability_refreshes_without_an_agent_or_new_registration(self):
        path = self.project / "paper/分析.tex"
        path.unlink()
        self.assertFalse(self.state()["chapters"][1]["draft_available"])
        self.save("paper/分析.tex", "重新出现的合成文件。")
        self.assertTrue(self.state()["chapters"][1]["draft_available"])
        self.assertEqual(self.state()["approvals"], [])

    def test_project_external_draft_and_paper_source_are_not_made_readable(self):
        private = self.base / "private.tex"
        private.write_text("never_expose_synthetic_private_contents", encoding="utf-8")
        self.control["nodes"]["H7"]["writer_preparation"]["chapters"][0]["draft"] = {
            "path": "../private.tex", "sha256": hashlib.sha256(private.read_bytes()).hexdigest(),
        }
        self.control["nodes"]["H8"] = {"paper_source": "../private.tex"}
        self.write_control()
        state = self.state()
        self.assertFalse(state["chapters"][0]["draft_available"])
        self.assertFalse(state["paper_source_available"])
        self.assertNotIn("never_expose_synthetic_private_contents", str(state))

    def test_registered_sources_remain_available_when_file_inventory_is_truncated(self):
        self.save("paper/总稿.tex", "合成整合稿。")
        self.control["nodes"]["H8"] = {"paper_source": "paper/总稿.tex"}
        self.write_control()
        with patch.object(app, "list_files", return_value=([], True)):
            state = self.state()
        self.assertEqual(state["files"], [])
        self.assertTrue(state["files_truncated"])
        self.assertTrue(state["paper_source_available"])
        self.assertTrue(state["chapters"][0]["draft_available"])

    def test_duplicate_registrations_are_preserved_for_explicit_conflict_display(self):
        chapters = self.control["nodes"]["H7"]["writer_preparation"]["chapters"]
        self.save("paper/Q1-other.tex", "另一份合成登记。")
        other = copy.deepcopy(chapters[0])
        other["draft"] = self.reference("paper/Q1-other.tex")
        chapters.append(other)
        self.write_control()
        self.assertEqual([row["id"] for row in self.state()["chapters"]], ["Q1", "analysis", "Q1"])

    def test_changed_plan_is_not_reported_as_bound_or_approved(self):
        self.plan["chapter_order"] = ["Q1", "analysis", "abstract"]
        self.save("plan.yaml", self.plan)
        state = self.state()
        self.assertEqual(state["writing_plan"]["hash"], "issues")
        self.assertEqual(state["approvals"], [])

    def test_presence_does_not_make_an_unsupported_file_previewable(self):
        self.save("paper/raw.bin", "synthetic binary placeholder")
        self.control["nodes"]["H7"]["writer_preparation"]["chapters"][0]["draft"] = self.reference("paper/raw.bin")
        self.write_control()
        state = self.state()
        self.assertTrue(state["chapters"][0]["draft_available"])
        self.assertFalse(state["chapters"][0]["draft_previewable"])


if __name__ == "__main__":
    unittest.main()
