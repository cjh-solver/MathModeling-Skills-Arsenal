import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scope_router_results", ROOT / "scripts" / "scope_router.py")
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)


class ScopeRouterResultTests(unittest.TestCase):
    def test_skips_excluded_subtrees_without_skipping_parent_named_reports(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "reports" / "project"
            root.mkdir(parents=True)
            (root / "result.csv").write_text("value\n1\n", encoding="utf-8")
            for name in (".git", "node_modules"):
                (root / name).mkdir()
                (root / name / "hidden_result.csv").write_text("value\n0\n", encoding="utf-8")
            scanned = []
            real_scandir = os.scandir

            def record_scandir(path):
                scanned.append(Path(path))
                return real_scandir(path)

            with patch.object(router.os, "scandir", side_effect=record_scandir):
                evidence = router.classify_evidence(root)
            self.assertEqual(evidence["results"], ["result.csv"])
            self.assertTrue(scanned)
            self.assertFalse(any(path.name in {".git", "node_modules"} for path in scanned), scanned)

    def test_external_file_symlink_is_not_project_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "project"
            root.mkdir()
            outside = base / "result.csv"
            outside.write_text("outside\n", encoding="utf-8")
            try:
                (root / "result.csv").symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"File symlinks unavailable: {exc}")
            self.assertEqual(router.classify_evidence(root)["results"], [])

    def test_resolved_external_file_is_not_project_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw).resolve()
            root = base / "project"
            root.mkdir()
            candidate = root / "result.csv"
            candidate.write_text("fixture\n", encoding="utf-8")
            outside = base / "outside.csv"
            outside.write_text("outside\n", encoding="utf-8")
            real_resolve = Path.resolve

            def resolve(path, *args, **kwargs):
                return outside if path == candidate else real_resolve(path, *args, **kwargs)

            with patch.object(Path, "resolve", resolve):
                self.assertEqual(router.classify_evidence(root)["results"], [])

    def test_result_spreadsheets_are_available_to_read_only_audit(self):
        for name in ("results.csv", "结果.xlsx", "敏感性.tsv", "baseline.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                (root / name).write_text("synthetic fixture", encoding="utf-8")
                plan = router.build_plan("DELIVERY_AUDIT", root)
                self.assertEqual(plan["input_gate"]["status"], "PASS", plan)
                self.assertIn(name, plan["evidence"]["results"])
                self.assertTrue(plan["read_only"])

    def test_unlabelled_input_data_does_not_claim_a_result(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "输入.csv").write_text("synthetic fixture", encoding="utf-8")
            plan = router.build_plan("DELIVERY_AUDIT", root)
            self.assertEqual(plan["input_gate"]["status"], "FAIL", plan)
            self.assertEqual(plan["evidence"]["results"], [])


if __name__ == "__main__":
    unittest.main()
