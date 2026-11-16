#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task 6 integration: sensitivity report contract check in check_model_evidence.

Ensures that when a subproblem declares optimization capability, the
sensitivity_report.yaml or robustness_report.yaml exists and has valid format.
"""
import os
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_model_evidence as checker  # noqa: E402


class SensitivityReportContractTests(unittest.TestCase):
    def test_optimization_subproblem_requires_sensitivity_report(self):
        """Optimization capability subproblem must have sensitivity or robustness report."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            # Create minimal paper.tex
            (root / "paper.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n"
                "\\label{subproblem:Q1}\nTest.\n"
                "\\end{document}\n", encoding="utf-8")
            # Create model_contract.yaml with optimization capability
            contract = {
                "schema_version": "2.1",
                "subproblems": [{
                    "id": "Q1",
                    "capabilities": ["optimization"],
                    "evidence": {
                        "decision_variables": {"status": "pass", "text_anchors": ["决策变量"], "source_files": []},
                        "objective": {"status": "pass", "text_anchors": ["目标函数"], "source_files": []},
                        "constraints": {"status": "pass", "text_anchors": ["约束"], "source_files": []},
                        "feasibility_check": {"status": "pass", "text_anchors": ["可行"], "source_files": []},
                    },
                }],
            }
            (root / "model_contract.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")
            # No sensitivity report created
            report = checker.validate(root, root / "model_contract.yaml", strict=False)
            sensitivity_issues = [i for i in report.get("warnings", []) if "sensitivity" in i.lower() or "灵敏度" in i or "robustness" in i.lower()]
            self.assertTrue(len(sensitivity_issues) > 0,
                            f"Expected sensitivity warning, got warnings: {report.get('warnings', [])}")

    def test_optimization_subproblem_with_valid_report_passes(self):
        """Optimization subproblem with valid sensitivity_report.yaml passes check."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "paper.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n"
                "\\label{subproblem:Q1}\nTest.\n"
                "\\end{document}\n", encoding="utf-8")
            contract = {
                "schema_version": "2.1",
                "subproblems": [{
                    "id": "Q1",
                    "capabilities": ["optimization"],
                    "evidence": {
                        "decision_variables": {"status": "pass", "text_anchors": ["决策变量"], "source_files": []},
                        "objective": {"status": "pass", "text_anchors": ["目标函数"], "source_files": []},
                        "constraints": {"status": "pass", "text_anchors": ["约束"], "source_files": []},
                        "feasibility_check": {"status": "pass", "text_anchors": ["可行"], "source_files": []},
                    },
                }],
            }
            (root / "model_contract.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")
            # Create valid sensitivity_report.yaml (status=verified with real numeric values)
            sensitivity = {
                "schema_version": "1.0",
                "status": "verified",
                "subproblem_id": "Q1",
                "method": "parameter_perturbation",
                "parameters_analyzed": 1,
                "results": [{
                    "parameter": "demand",
                    "baseline": 100,
                    "perturbation_points": [
                        {"value": 80, "objective": 950.0, "feasible": True, "decision_change": "none"},
                        {"value": 100, "objective": 1000.0, "feasible": True, "decision_change": "none"},
                        {"value": 120, "objective": 1050.0, "feasible": True, "decision_change": "none"},
                    ],
                }],
            }
            (root / "sensitivity_report.yaml").write_text(yaml.safe_dump(sensitivity), encoding="utf-8")
            report = checker.validate(root, root / "model_contract.yaml", strict=False)
            sensitivity_issues = [i for i in report.get("warnings", []) + report.get("issues", [])
                                   if "sensitivity" in i.lower() or "灵敏度" in i or "robustness" in i.lower()]
            self.assertEqual(sensitivity_issues, [],
                             f"Unexpected sensitivity issues: {sensitivity_issues}")

    def test_non_optimization_subproblem_skips_sensitivity_check(self):
        """Non-optimization subproblem skips sensitivity report check."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "paper.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n"
                "\\label{subproblem:Q1}\nTest.\n"
                "\\end{document}\n", encoding="utf-8")
            contract = {
                "schema_version": "2.1",
                "subproblems": [{
                    "id": "Q1",
                    "capabilities": ["prediction"],
                    "evidence": {
                        "preprocessing": {"status": "pass", "text_anchors": ["预处理"], "source_files": []},
                        "data_split": {"status": "pass", "text_anchors": ["数据划分"], "source_files": []},
                        "baseline": {"status": "pass", "text_anchors": ["基线"], "source_files": []},
                        "metrics": {"status": "pass", "text_anchors": ["指标"], "source_files": []},
                    },
                }],
            }
            (root / "model_contract.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")
            report = checker.validate(root, root / "model_contract.yaml", strict=False)
            sensitivity_issues = [i for i in report.get("warnings", []) + report.get("issues", [])
                                   if "sensitivity" in i.lower() or "灵敏度" in i or "robustness" in i.lower()]
            self.assertEqual(sensitivity_issues, [])

    def test_sensitivity_report_invalid_format_triggers_warning(self):
        """Sensitivity report with invalid schema_version triggers warning."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "paper.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\n"
                "\\label{subproblem:Q1}\nTest.\n"
                "\\end{document}\n", encoding="utf-8")
            contract = {
                "schema_version": "2.1",
                "subproblems": [{
                    "id": "Q1",
                    "capabilities": ["optimization"],
                    "evidence": {
                        "decision_variables": {"status": "pass", "text_anchors": ["决策变量"], "source_files": []},
                        "objective": {"status": "pass", "text_anchors": ["目标函数"], "source_files": []},
                        "constraints": {"status": "pass", "text_anchors": ["约束"], "source_files": []},
                        "feasibility_check": {"status": "pass", "text_anchors": ["可行"], "source_files": []},
                    },
                }],
            }
            (root / "model_contract.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")
            # Create invalid sensitivity_report.yaml (missing schema_version)
            (root / "sensitivity_report.yaml").write_text("status: invalid\n", encoding="utf-8")
            report = checker.validate(root, root / "model_contract.yaml", strict=False)
            sensitivity_issues = [i for i in report.get("warnings", [])
                                   if "sensitivity" in i.lower() or "灵敏度" in i or "格式" in i or "schema" in i.lower()]
            self.assertTrue(len(sensitivity_issues) > 0,
                            f"Expected format warning, got: {report.get('warnings', [])}")


class QuestionScopedSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_report(self, questions=("Q1",), header=None):
        report = {
            "schema_version": "1.0", "status": "verified", "method": "parameter_perturbation",
            "results": [{
                "subproblem_id": question, "parameter": "demand", "baseline": 100,
                "perturbation_points": [{
                    "value": 110, "objective": 10.0, "feasible": True, "decision_change": "unchanged",
                }],
            } for question in questions],
        }
        if header is not None:
            report["subproblem_id"] = header
        return report

    def write_report(self, report, relative="sensitivity_report.yaml"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(report), encoding="utf-8")

    def test_q1_only_aggregate_cannot_supply_q2_evidence(self):
        self.write_report(self.make_report())
        warnings = checker._check_sensitivity_report(self.root, "Q2")
        self.assertTrue(any("subproblem_id" in item for item in warnings), warnings)

    def test_aggregate_checks_only_the_requested_question(self):
        report = self.make_report(("Q1", "Q2"))
        report["results"][0]["perturbation_points"][0]["objective"] = None
        self.write_report(report)

        self.assertEqual(checker._check_sensitivity_report(self.root, "Q2"), [])
        self.assertTrue(checker._check_sensitivity_report(self.root, "Q1"))

    def test_other_question_does_not_mask_a_matching_report(self):
        self.write_report(self.make_report(header="Q1"))
        self.write_report(self.make_report(("Q2",), header="Q2"), "results/sensitivity_report.yaml")

        self.assertEqual(checker._check_sensitivity_report(self.root, "Q2"), [])

    def test_unbound_report_is_pending_instead_of_assigned_to_any_question(self):
        report = self.make_report()
        report["results"][0].pop("subproblem_id")
        self.write_report(report)

        self.assertTrue(checker._check_sensitivity_report(self.root, "Q1"))

    def test_conflicting_header_and_result_question_are_not_reused(self):
        self.write_report(self.make_report(("Q2",), header="Q1"))

        self.assertTrue(checker._check_sensitivity_report(self.root, "Q1"))
        self.assertTrue(checker._check_sensitivity_report(self.root, "Q2"))

    def test_matching_draft_is_not_hidden_by_a_later_verified_report(self):
        draft = self.make_report(header="Q1")
        draft["status"] = "draft"
        self.write_report(draft)
        self.write_report(self.make_report(header="Q1"), "results/sensitivity_report.yaml")

        warnings = checker._check_sensitivity_report(self.root, "Q1")
        self.assertTrue(any("status" in item for item in warnings), warnings)

    def test_matching_question_needs_real_perturbation_records(self):
        for points in ([], None, [None]):
            with self.subTest(points=points):
                report = self.make_report(header="Q1")
                report["results"][0]["perturbation_points"] = points
                self.write_report(report)
                self.assertTrue(checker._check_sensitivity_report(self.root, "Q1"))

    def test_zero_objective_and_infeasible_scenario_are_real_values(self):
        report = self.make_report(header="Q1")
        report["results"][0]["perturbation_points"][0].update(objective=0.0, feasible=False)
        self.write_report(report)

        self.assertEqual(checker._check_sensitivity_report(self.root, "Q1"), [])

    def test_single_question_header_still_binds_legacy_result_rows(self):
        report = self.make_report(header="Q1")
        report["results"][0].pop("subproblem_id")
        self.write_report(report)

        self.assertEqual(checker._check_sensitivity_report(self.root, "Q1"), [])

    def test_one_aggregate_serves_h5_traceability_and_both_questions(self):
        from check_h5_result_traceability import validate_h5_result_traceability

        report = self.make_report(("Q1", "Q2"))
        contract = self.root / "model_contract.yaml"
        contract.write_text(yaml.safe_dump({
            "schema_version": "2.1",
            "subproblems": [{"id": qid, "capabilities": ["optimization"]} for qid in ("Q1", "Q2")],
        }), encoding="utf-8")
        source = self.root / "results/raw_sweep.yaml"
        source.parent.mkdir()
        source.write_text(yaml.safe_dump({"synthetic_results": report["results"]}), encoding="utf-8")
        reference = {"path": "results/raw_sweep.yaml", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        contract_hash = hashlib.sha256(contract.read_bytes()).hexdigest()
        report.update(canonical_report=reference, model_contract_sha256=contract_hash)
        self.write_report(report)
        manifest = {
            "schema_version": "1.0", "status": "verified", "node_id": "H5", "seed": 0,
            "offline_run": {"command": "python solve.py", "result": reference},
            "formal_tests": {"record_fields": ["case_code", "result_file"], "records": [{"case_code": "synthetic", "result_file": reference}]},
            "formal_interpretation_boundary": "Synthetic fixture only.",
            "model_contract_sha256": contract_hash,
        }
        (self.root / "run_manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")

        self.assertEqual(validate_h5_result_traceability(self.root)["status"], "PASS")
        for question in ("Q1", "Q2"):
            self.assertEqual(checker._check_sensitivity_report(self.root, question), [])


if __name__ == "__main__":
    unittest.main()
