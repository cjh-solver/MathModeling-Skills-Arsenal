import tempfile
import unittest
from pathlib import Path

import yaml

import app


class VerificationSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        (self.project / ".contest").mkdir(parents=True)
        self.links = self.base / "role-links.json"
        self.control = {
            "active_mode": "full-contest-harness", "problem_scope": {"subproblems": ["Q1"]},
            "nodes": {
                "H5": {"result_interpretation_cards": "results.yaml"},
                "H6": {"global_interface_check": "核验/H6.yaml"},
            },
        }
        self.save("results.yaml", {"status": "draft", "cards": [
            {"subproblem_id": "Q1", "result_statement": "Synthetic result"}
        ]})
        self.save("核验/H6.yaml", {"status": "PASS", "verified_artifacts": {}})

    def save(self, name, data):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return path

    def state(self):
        self.save(".contest/harness_control.yaml", self.control)
        return app.build_state(self.project, self.links)

    def test_registered_verification_is_linked_without_promoting_source_status(self):
        self.state()
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.project.rglob("*") if path.is_file()}
        result = app.build_state(self.project, self.links)
        self.assertEqual(result["question_sources"]["verification"], "核验/H6.yaml")
        self.assertIsNone(result["question_sources"]["verification_error"])
        self.assertEqual(result["question_views"][0]["interpretations"][0]["verification"], "draft")
        self.assertEqual(result["approvals"], [])
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)

    def test_absent_verification_registration_stays_absent(self):
        self.control["nodes"]["H6"] = {}
        self.assertIsNone(self.state()["question_sources"]["verification"])

    def test_missing_or_malformed_record_is_reported_without_rewriting_it(self):
        path = self.project / "核验/H6.yaml"
        path.unlink()
        self.assertTrue(self.state()["question_sources"]["verification_error"])
        path.write_text("invalid: [", encoding="utf-8")
        original = path.read_bytes()
        self.assertTrue(self.state()["question_sources"]["verification_error"])
        self.assertEqual(path.read_bytes(), original)

    def test_outside_project_record_is_not_read(self):
        (self.base / "secret.yaml").write_text("private: never_expose_this_value", encoding="utf-8")
        self.control["nodes"]["H6"]["global_interface_check"] = "../secret.yaml"
        result = self.state()
        self.assertTrue(result["question_sources"]["verification_error"])
        self.assertNotIn("never_expose_this_value", str(result))


if __name__ == "__main__":
    unittest.main()
