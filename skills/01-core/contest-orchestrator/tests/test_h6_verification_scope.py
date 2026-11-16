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

    def test_invalid_scope_fields_fail_without_exceptions(self):
        valid = {
            "schema_version": "1.0", "mode": "targeted_recheck", "trigger": "key_result_change",
            "changed_artifacts": [{"path": "results/q1.yaml", "sha256": "a" * 64}],
            "mandatory_checks": sorted(MODULE.MANDATORY_CHECKS), "deep_sample_refs": [],
        }
        cases = (
            ("mode", []), ("trigger", {}), ("mandatory_checks", [{}]),
            ("changed_artifacts", [{"path": None, "sha256": None}]),
            ("changed_artifacts", [{"path": "results/q1.yaml", "sha256": "placeholder"}]),
            ("deep_sample_refs", [{"path": 12, "sha256": "a" * 64}]),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                report = MODULE.check_scope({**valid, field: value})
                self.assertFalse(report["passed"])
                self.assertTrue(any(field in error for error in report["failures"]))
        self.assertTrue(MODULE.check_scope(valid)["passed"])

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
            legacy_nodes = {"H6": {"h6_verification_scope": "scope.yaml"}}
            for mode in ("targeted", "targeted_review"):
                scope["mode"] = mode
                scope["rechecked_subproblems"] = ["Q1"]
                save()
                self.assertEqual(checker._h6_targeted_scope(root, legacy_nodes, problem_scope, "H6"), {"Q1"})
                self.assertIsNone(checker._h6_targeted_scope(root, legacy_nodes, None, "H6"))
                scope["rechecked_subproblems"] = ["Q99"]
                save()
                self.assertIsNone(checker._h6_targeted_scope(root, legacy_nodes, problem_scope, "H6"))
                scope["rechecked_subproblems"] = ["Q1"]
                scope["trigger"] = "ordinary_prose_change"
                save()
                self.assertIsNone(checker._h6_targeted_scope(root, legacy_nodes, problem_scope, "H6"))
                scope["trigger"] = "key_result_change"

    def test_targeted_scope_cannot_hide_other_models_at_later_stages(self):
        spec = importlib.util.spec_from_file_location("h6_scope_stage_boundary", ROOT / "scripts" / "check_harness_control.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cards = [{
                "card_id": f"{qid}-model", "subproblem_id": qid,
                "purpose": "A bounded decision", "model_family": "optimization",
                "decision_variables": [{"symbol": "x", "meaning": "allocation", "unit": "units", "domain": "x>=0"}],
                "parameters": [], "final_formulation": {"kind": "optimization", "expression": "min f(x)"},
                "solver_interface": {"method": "solver", "inputs": ["demand"], "outputs": ["x"]},
                "source_equation_refs": ["eq:allocation"],
                "paper_structure": {"opening_bridge": "A bounded model", "numbered_sections": list(checker.QUESTION_NUMBERED_SECTIONS),
                                    "summary_location": "模型建立小节末尾", "optional_sections": []},
            } for qid in ("Q1", "Q2")]
            del cards[1]["purpose"]
            summary = {"status": "verified", "created_by": "H5", "verified_by": "H6",
                       "verification_agent_instance_id": "H6-agent", "cards": cards}
            summary_path = root / "models.yaml"
            summary_path.write_text(yaml.safe_dump(summary, allow_unicode=True), encoding="utf-8")
            before = summary_path.read_bytes()
            scope_path = root / "scope.yaml"
            for mode in ("targeted_recheck", "targeted", "targeted_review"):
                scope = {"schema_version": "1.0", "mode": mode, "trigger": "key_result_change",
                         "changed_artifacts": [{"path": "results/q1.yaml", "sha256": "a" * 64}],
                         "mandatory_checks": sorted(MODULE.MANDATORY_CHECKS), "deep_sample_refs": [],
                         "rechecked_subproblems": ["Q1"]}
                scope_path.write_text(yaml.safe_dump(scope), encoding="utf-8")
                for registration in ("verification_scope", "h6_verification_scope"):
                    nodes = {"H5": {"model_summary_cards": "models.yaml"},
                             "H6": {"status": "review_pending", "agent_instance_id": "H6-agent",
                                    "model_summary_cards": "models.yaml", registration: "scope.yaml"}}
                    for stage in ("H6", "H7", "H8", "H9"):
                        with self.subTest(mode=mode, registration=registration, stage=stage):
                            missing, failures = [], []
                            checker._validate_model_summary_cards(root, nodes, {"subproblems": ["Q1", "Q2"]}, missing, failures, through=stage)
                            self.assertEqual(missing, [])
                            if stage == "H6":
                                self.assertEqual(failures, [])
                            else:
                                self.assertTrue(any("缺少 purpose" in failure for failure in failures), failures)
            self.assertEqual(summary_path.read_bytes(), before)

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
