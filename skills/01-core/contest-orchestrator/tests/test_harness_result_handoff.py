import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "harness_result_handoff", ROOT / "scripts" / "check_harness_control.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ResultHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.result_path = self.root / "results.csv"
        self.result_path.write_text("question,value\nQ1,42\nQ2,0\n", encoding="utf-8")
        self.reference = {
            "path": "results.csv",
            "sha256": hashlib.sha256(self.result_path.read_bytes()).hexdigest(),
        }
        self.cards_path = self.root / "result_interpretation_cards.yaml"
        self.nodes = {
            "H5": {"result_interpretation_cards": self.cards_path.name},
            "H6": {"agent_instance_id": "independent-verifier"},
        }
        self.control = {"problem_scope": {"subproblems": ["Q1", {"id": "Q2"}]}}

    def card(self, question, suffix="result"):
        return {
            "card_id": f"{question}-{suffix}", "subproblem_id": question,
            "result_statement": "合成数据下的结果满足约束。",
            "meaning": "该方案回答对应小问的任务。",
            "reasoning_basis": "依据已冻结的求解结果与约束比较。",
            "supported_scope": "仅限合成测试数据。",
            "evidence_refs": [self.reference],
        }

    def save(self, cards, **fields):
        document = {
            "schema_version": "1.0", "status": "verified", "created_by": "H5",
            "verified_by": "H6", "verification_agent_instance_id": "independent-verifier",
            "cards": cards, **fields,
        }
        self.cards_path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")

    def check(self, through="H6", control=True):
        missing, failures = [], []
        CHECKER._validate_result_interpretation_cards(
            self.root, self.nodes, through, missing, failures,
            control=self.control if control else None,
        )
        return missing, failures

    def targeted(self, questions):
        scope = {
            "schema_version": "1.0", "mode": "targeted_recheck", "trigger": "key_result_change",
            "changed_artifacts": [self.reference], "rechecked_subproblems": questions,
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
            "deep_sample_refs": [],
        }
        path = self.root / "h6_scope.yaml"
        path.write_text(yaml.safe_dump(scope), encoding="utf-8")
        self.nodes["H6"]["verification_scope"] = path.name

    def test_full_handoff_requires_results_for_every_registered_question(self):
        self.save([self.card("Q1")])
        for stage in ("H6", "H7", "H8", "H9"):
            with self.subTest(stage=stage):
                missing, failures = self.check(stage)
                self.assertEqual(missing, [])
                self.assertTrue(any("Q2" in failure and "覆盖" in failure for failure in failures))

    def test_extra_question_does_not_replace_a_registered_question(self):
        self.save([self.card("Q1"), self.card("Q99")])
        _, failures = self.check()
        self.assertTrue(any("Q99" in failure and "problem_scope" in failure for failure in failures))
        self.assertTrue(any("Q2" in failure and "覆盖" in failure for failure in failures))

    def test_harness_entrypoint_reports_the_missing_question(self):
        self.save([self.card("Q1")])
        control = CHECKER.default_control()
        control["problem_scope"] = self.control["problem_scope"]
        control["nodes"]["H5"].update(self.nodes["H5"])
        control["nodes"]["H6"].update(self.nodes["H6"])
        directory = self.root / ".contest"
        directory.mkdir()
        (directory / "harness_control.yaml").write_text(
            yaml.safe_dump(control, allow_unicode=True), encoding="utf-8"
        )
        report = CHECKER.check_harness_control(self.root, through="H6")
        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(
            "result_interpretation_cards" in failure and "Q2" in failure
            for failure in report["failures"]
        ))

    def test_multiple_distinct_results_per_question_are_allowed(self):
        self.save([self.card("Q1", "baseline"), self.card("Q1", "comparison"), self.card("Q2")])
        for stage in ("H6", "H8", "H9"):
            with self.subTest(stage=stage):
                self.assertEqual(self.check(stage), ([], []))

    def test_duplicate_result_ids_remain_invalid(self):
        self.save([self.card("Q1"), {**self.card("Q2"), "card_id": "Q1-result"}])
        _, failures = self.check()
        self.assertTrue(any("card_id 重复" in failure for failure in failures))

    def test_targeted_h6_limits_work_but_later_stages_require_full_handoff(self):
        self.save([self.card("Q1")])
        self.targeted(["Q1"])
        self.assertEqual(self.check("H6"), ([], []))
        for stage in ("H7", "H8", "H9"):
            with self.subTest(stage=stage):
                _, failures = self.check(stage)
                self.assertTrue(any("Q2" in failure and "覆盖" in failure for failure in failures))

    def test_targeted_h6_cannot_omit_the_affected_question(self):
        self.save([self.card("Q2")])
        self.targeted(["Q1"])
        _, failures = self.check()
        self.assertTrue(any("Q1" in failure and "覆盖" in failure for failure in failures))

    def test_invalid_targeted_scope_cannot_hide_a_missing_question(self):
        self.save([self.card("Q1")])
        self.targeted(["Q99"])
        _, failures = self.check()
        self.assertTrue(any("Q2" in failure and "覆盖" in failure for failure in failures))

    def test_coverage_does_not_replace_fresh_evidence(self):
        self.save([self.card("Q1"), self.card("Q2")])
        self.result_path.write_text("changed\n", encoding="utf-8")
        _, failures = self.check()
        self.assertTrue(any("哈希不匹配" in failure for failure in failures))

    def test_h5_drafts_are_not_required_to_claim_h6_verification(self):
        self.save([self.card("Q1")], status="draft", verified_by=None, verification_agent_instance_id=None)
        self.assertEqual(self.check("H5"), ([], []))

    def test_legacy_call_without_scope_remains_compatible(self):
        self.save([self.card("Q1")])
        self.assertEqual(self.check(control=False), ([], []))

    def test_validation_keeps_result_and_evidence_records_read_only(self):
        self.save([self.card("Q1"), self.card("Q2")])
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.root.iterdir()}
        for stage in ("H6", "H7", "H8", "H9"):
            self.assertEqual(self.check(stage), ([], []))
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)


if __name__ == "__main__":
    unittest.main()
