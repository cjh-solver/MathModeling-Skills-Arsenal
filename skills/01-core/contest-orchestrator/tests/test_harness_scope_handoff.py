import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import check_harness_control as checker
from test_harness_hardening import build_ready_harness
from test_visual_argument_plan import _model_cards, _valid_visual_plan


class ScopeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return path

    def check_visual_plan(self, registered):
        plan = _valid_visual_plan()
        plan["status"] = "draft"
        self.save("visual_argument_plan.yaml", plan)
        self.save("model_summary_cards.yaml", _model_cards())
        control = {"problem_scope": {"subproblems": registered}}
        node = {"status": "draft", "visual_argument_plan": "visual_argument_plan.yaml",
                "model_summary_cards": "model_summary_cards.yaml"}
        original = copy.deepcopy(control)
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        missing, failures = [], []
        checker._validate_h7_visual_argument_plan(
            self.root, node, control, {"approvals": []}, missing, failures,
        )
        self.assertEqual(control, original)
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns)
                          for path in before}, before)
        return missing, failures

    def test_h7_accepts_equivalent_registered_scope_formats(self):
        for registered in (
            ["Q1", "Q2"],
            [{"id": "Q1", "title": "问题一"}, {"id": "Q2", "title": "问题二"}],
            ["Q1", {"id": "Q2", "title": "问题二"}],
            [{"id": " Q1 "}, " Q2 "],
        ):
            with self.subTest(registered=registered):
                self.assertEqual(self.check_visual_plan(registered), ([], []))

    def test_h7_still_rejects_a_plan_missing_a_registered_question(self):
        _, failures = self.check_visual_plan([{"id": "Q1"}, {"id": "Q2"}, {"id": "Q3"}])
        self.assertTrue(any("scope.subproblems" in failure for failure in failures), failures)

    def test_h7_does_not_expand_scope_from_titles_or_plan_content(self):
        _, failures = self.check_visual_plan([{"id": "Q1", "title": "Q2"}])
        self.assertTrue(any("scope.subproblems" in failure for failure in failures), failures)

    def test_h7_preserves_registered_question_order(self):
        _, failures = self.check_visual_plan([{"id": "Q2"}, "Q1"])
        self.assertTrue(any("scope.subproblems" in failure for failure in failures), failures)

    def check_solver_scope(self, registered):
        control, _ = build_ready_harness(self.root, checker)
        control["problem_scope"]["subproblems"] = registered
        missing, failures = [], []
        checker._validate_dispatch_records(
            self.root, control, control["nodes"], checker.AGENT_RUNTIME_BY_NODE,
            "H5", missing, failures,
        )
        return failures

    def test_h5_dispatch_accepts_structured_question_identity(self):
        self.assertEqual(self.check_solver_scope([{"id": " Q1 ", "title": "问题一"}]), [])

    def test_h5_still_rejects_invalid_and_duplicate_question_ids(self):
        for registered in ([None], [1], [True], [{"id": []}], [{"id": " "}],
                           ["Q1", {"id": " Q1 "}]):
            with self.subTest(registered=registered):
                failures = self.check_solver_scope(registered)
                self.assertTrue(any("problem_scope.subproblems" in failure for failure in failures), failures)

    def test_h5_requires_coverage_of_structured_questions(self):
        failures = self.check_solver_scope(["Q1", {"id": "Q2"}])
        self.assertTrue(any("全部小问" in failure for failure in failures), failures)

    def targeted_scope(self, registered, rechecked=None):
        result = self.save("results/Q1.yaml", {"value": 0})
        self.save("h6_scope.yaml", {
            "schema_version": "1.0", "mode": "targeted_recheck", "trigger": "key_result_change",
            "changed_artifacts": [{"path": "results/Q1.yaml", "sha256": checker.digest(result)}],
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
            "deep_sample_refs": [], "rechecked_subproblems": rechecked or ["Q1"],
        })
        nodes = {"H6": {"verification_scope": "h6_scope.yaml"}}
        return nodes, {"subproblems": registered}

    def test_h6_targeted_scope_uses_the_same_registered_question_identity(self):
        nodes, scope = self.targeted_scope([{"id": " Q1 "}, " Q2 "])
        self.assertEqual(checker._h6_targeted_scope(self.root, nodes, scope, "H6"), {"Q1"})

    def test_h6_targeted_scope_cannot_narrow_later_stages(self):
        nodes, scope = self.targeted_scope([{"id": " Q1 "}, " Q2 "])
        for stage in ("H7", "H8", "H9"):
            with self.subTest(stage=stage):
                self.assertIsNone(checker._h6_targeted_scope(self.root, nodes, scope, stage))

    def test_unknown_question_cannot_grant_a_targeted_recheck(self):
        nodes, scope = self.targeted_scope([{"id": "Q1"}], ["Q2"])
        self.assertIsNone(checker._h6_targeted_scope(self.root, nodes, scope, "H6"))


if __name__ == "__main__":
    unittest.main()
