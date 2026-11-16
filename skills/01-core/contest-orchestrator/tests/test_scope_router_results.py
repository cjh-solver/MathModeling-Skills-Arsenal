import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scope_router_results", ROOT / "scripts" / "scope_router.py")
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)


class ScopeRouterResultTests(unittest.TestCase):
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
