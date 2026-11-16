import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_h6_verification_scope.py"
SPEC = importlib.util.spec_from_file_location("check_h6_verification_scope", CHECKER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class H6VerificationScopeTests(unittest.TestCase):
    def test_presentation_only_change_is_not_an_h6_trigger(self):
        scope = {
            "schema_version": "1.0",
            "mode": "targeted_recheck",
            "trigger": "ordinary_prose_change",
            "changed_artifacts": [{"path": "paper/sections/q1.tex", "sha256": "a" * 64}],
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
            "deep_sample_refs": [],
        }
        report = MODULE.check_scope(scope)
        self.assertFalse(report["passed"])
        self.assertTrue(any("不触发 H6" in item for item in report["failures"]))

    def test_targeted_recheck_needs_changed_artifact_and_mandatory_checks(self):
        scope = {
            "schema_version": "1.0",
            "mode": "targeted_recheck",
            "trigger": "key_result_change",
            "changed_artifacts": [],
            "mandatory_checks": ["contract_anchors"],
            "deep_sample_refs": [],
        }
        report = MODULE.check_scope(scope)
        self.assertFalse(report["passed"])
        self.assertTrue(any("changed_artifacts" in item for item in report["failures"]))
        self.assertTrue(any("mandatory_checks" in item for item in report["failures"]))

    def test_canonical_scope_registration_reaches_harness_checker(self):
        spec = importlib.util.spec_from_file_location("h6_scope_harness", ROOT / "scripts" / "check_harness_control.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            scope = {
                "schema_version": "1.0", "mode": "targeted_recheck", "trigger": "key_result_change",
                "changed_artifacts": [{"path": "results/q1.yaml", "sha256": "a" * 64}],
                "mandatory_checks": sorted(MODULE.MANDATORY_CHECKS), "deep_sample_refs": [],
                "rechecked_subproblems": ["Q1"],
            }
            path = root / "scope.yaml"
            def save():
                path.write_text(yaml.safe_dump(scope), encoding="utf-8")
            save()
            nodes = {"H6": {"verification_scope": "scope.yaml"}}
            problem_scope = {"subproblems": ["Q1", "Q2"]}
            self.assertTrue(MODULE.check_scope(scope)["passed"])
            self.assertEqual(checker._h6_targeted_scope(root, nodes, problem_scope, "H6"), {"Q1"})
            for stage in ("H7", "H8", "H9"):
                self.assertIsNone(checker._h6_targeted_scope(root, nodes, problem_scope, stage))
            scope["trigger"] = "ordinary_prose_change"
            save()
            self.assertIsNone(checker._h6_targeted_scope(root, nodes, problem_scope, "H6"))
            scope["trigger"] = "key_result_change"
            for values in ([], [None], [" "], ["Q99"]):
                scope["rechecked_subproblems"] = values
                save()
                self.assertIsNone(checker._h6_targeted_scope(root, nodes, problem_scope, "H6"))
            scope["mode"] = "targeted_review"
            scope["rechecked_subproblems"] = ["Q1"]
            save()
            self.assertEqual(checker._h6_targeted_scope(root, {"H6": {"h6_verification_scope": "scope.yaml"}}), {"Q1"})

    def test_initial_review_with_registered_sample_passes(self):
        scope = {
            "schema_version": "1.0",
            "mode": "initial_review",
            "trigger": "h5_result_freeze",
            "changed_artifacts": [],
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
            "deep_sample_refs": [{"path": "results/q1.yaml", "sha256": "a" * 64}],
        }
        self.assertTrue(MODULE.check_scope(scope)["passed"])


if __name__ == "__main__":
    unittest.main()
