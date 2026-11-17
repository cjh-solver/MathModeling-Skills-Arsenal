import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_model_evidence as checker
from replay_profiles import write_fixture


def simple_method(result=0):
    return {
        "capabilities": ["optimization"],
        "method_selection": {
            "baseline": {"baseline_method": "linear programming", "baseline_result": result},
            "method_justification": {
                "core_conflict": "Meet demand with limited resources.",
                "method_role": "Solve the linear objective and constraints exactly.",
            },
        },
    }


def upgraded_method():
    item = simple_method()
    item["method_selection"].update({
        "complexity_upgrade": {
            "upgrade_from": "greedy", "upgrade_to": "PSO",
            "upgrade_reason": "Compare alternate feasible orders.",
        },
        "decision_impact": {"impact_level": 2},
    })
    item["method_selection"]["method_justification"].update({
        "simple_method_failure": "Greedy search cannot revisit an earlier assignment.",
        "complex_method_target": "Explore other feasible orders under the same constraints.",
        "cost_benefit": "The bounded search changes the selected feasible allocation.",
    })
    return item


class MethodSelectionTests(unittest.TestCase):
    def test_simple_final_method_does_not_require_an_invented_upgrade(self):
        self.assertEqual(checker._check_method_selection(simple_method(), "Q1"), [])

    def test_zero_and_false_are_recorded_baseline_results(self):
        for value in (0, 0.0, False, {"objective": 0}, {"feasible": False}):
            with self.subTest(value=value):
                self.assertEqual(checker._check_method_selection(simple_method(value), "Q1"), [])

    def test_missing_baseline_results_are_still_reported(self):
        for value in (None, "", [], {}):
            with self.subTest(value=value):
                warnings = checker._check_method_selection(simple_method(value), "Q1")
                self.assertTrue(any("baseline_result" in warning for warning in warnings), warnings)

    def test_both_common_selection_reasons_remain_required(self):
        for field in ("core_conflict", "method_role"):
            with self.subTest(field=field):
                item = simple_method()
                del item["method_selection"]["method_justification"][field]
                warnings = checker._check_method_selection(item, "Q1")
                self.assertTrue(any(field in warning for warning in warnings), warnings)

    def test_no_upgrade_record_and_null_upgrade_have_the_same_requirements(self):
        item = simple_method()
        item["method_selection"]["complexity_upgrade"] = None
        self.assertEqual(checker._check_method_selection(item, "Q1"), [])

    def test_upgrade_record_requires_decision_impact_for_optimization(self):
        item = upgraded_method()
        del item["method_selection"]["decision_impact"]
        warnings = checker._check_method_selection(item, "Q1")
        self.assertTrue(any("decision_impact" in warning for warning in warnings), warnings)

    def test_real_upgrade_requires_each_additional_reason(self):
        for field in ("simple_method_failure", "complex_method_target", "cost_benefit"):
            with self.subTest(field=field):
                item = upgraded_method()
                del item["method_selection"]["method_justification"][field]
                warnings = checker._check_method_selection(item, "Q1")
                self.assertTrue(any(field in warning for warning in warnings), warnings)

    def test_complete_upgrade_evidence_is_accepted(self):
        self.assertEqual(checker._check_method_selection(upgraded_method(), "Q1"), [])

    def test_empty_upgrade_is_not_treated_as_a_completed_simple_route(self):
        item = upgraded_method()
        item["method_selection"]["complexity_upgrade"] = {}
        warnings = checker._check_method_selection(item, "Q1")
        self.assertTrue(any("complexity_upgrade" in warning for warning in warnings), warnings)

    def test_incomplete_upgrade_record_is_reported(self):
        for field in ("upgrade_from", "upgrade_to", "upgrade_reason"):
            with self.subTest(field=field):
                item = upgraded_method()
                del item["method_selection"]["complexity_upgrade"][field]
                warnings = checker._check_method_selection(item, "Q1")
                self.assertTrue(any("complexity_upgrade" in warning for warning in warnings), warnings)

    def test_legacy_complex_capability_still_requires_upgrade_evidence(self):
        item = simple_method()
        item["capabilities"] = ["heuristic"]
        warnings = checker._check_method_selection(item, "Q1")
        self.assertTrue(any("complexity_upgrade" in warning for warning in warnings), warnings)
        self.assertTrue(any("decision_impact" in warning for warning in warnings), warnings)

    def test_low_decision_impact_still_reaches_human_review(self):
        item = upgraded_method()
        item["method_selection"]["decision_impact"]["impact_level"] = 0
        self.assertTrue(checker._check_method_selection(item, "Q1"))

    def test_selection_check_does_not_mutate_the_model_contract(self):
        item = upgraded_method()
        before = copy.deepcopy(item)
        checker._check_method_selection(item, "Q1")
        self.assertEqual(item, before)

    def validate_fixture(self, selection, *, remove_result_source=False):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_fixture(root, "mechanistic")
            path = root / "model_contract.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["subproblems"][0]["method_selection"] = selection
            if remove_result_source:
                del data["subproblems"][0]["evidence"]["result_source"]
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            before = {file: (file.read_bytes(), file.stat().st_mtime_ns)
                      for file in root.rglob("*") if file.is_file()}
            report = checker.validate(root, path, strict=True)
            self.assertEqual({file: (file.read_bytes(), file.stat().st_mtime_ns)
                              for file in before}, before)
            return report

    def test_strict_evidence_validation_accepts_a_simple_final_route(self):
        report = self.validate_fixture(simple_method()["method_selection"])
        self.assertTrue(report["passed"], report)
        self.assertFalse(any("method_justification" in warning or "baseline_result" in warning
                             for warning in report["warnings"]), report)

    def test_upgrade_advice_does_not_become_an_automatic_delivery_gate(self):
        selection = upgraded_method()["method_selection"]
        del selection["decision_impact"]
        report = self.validate_fixture(selection)
        self.assertTrue(report["passed"], report)
        self.assertTrue(any("decision_impact" in warning for warning in report["warnings"]), report)

    def test_method_advice_does_not_waive_missing_scientific_evidence(self):
        report = self.validate_fixture(simple_method()["method_selection"], remove_result_source=True)
        self.assertFalse(report["passed"], report)
        self.assertTrue(any("result_source" in issue for issue in report["issues"]), report)


if __name__ == "__main__":
    unittest.main()
