import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import check_harness_control as checker
import test_authoring_architecture as authoring


class SupportContributionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        _, brief = authoring.AuthoringArchitectureTests()._write_brief_fixture(self.root)
        self.brief = yaml.safe_load(brief.read_text(encoding="utf-8"))
        self.brief["paper_spine"] = {
            "core_chapters": ["Q1"], "support_chapters": ["analysis"],
            "chapter_order": ["analysis", "Q1"],
            "chapter_edges": [{"from": "analysis", "to": "Q1", "relation": "feeds", "handoff_question": "How?"}],
        }
        self.brief["chapters"][0]["reads_from"] = ["analysis"]
        self.support = {
            "section_id": "analysis", "chapter_kind": "narrative", "chapter_role": "support",
            "reads_from": [], "feeds_to": ["Q1"], "new_claims_allowed": [], "handoff_question": "How?",
            "argument_ids": [], "figure_roles": [], "evidence_refs": [],
        }
        self.brief["chapters"].append(self.support)
        self.write_brief()
        self.card = {
            "status": "ready", "chapter_id": "analysis", "chapter_kind": "narrative",
            **{key: value for key, value in self.support.items() if key != "section_id"},
            "reader_question": "What?", "chapter_purpose": "Context", "chapter_answer": "Context",
            "reader_takeaway": "Context", "writer_instruction": "Write", "excluded_material": [],
            "abstract_contribution": {"status": "not_applicable", "reason": "本章仅分析题意，没有独立摘要主张"},
        }
        self.node = {"paper_author_brief": "paper_author_brief.yaml", "chapter_writing_cards": ["card.yaml"],
                     "active_chapter_card": "card.yaml", "writing_started": True}

    def write_brief(self):
        path = self.root / "paper_author_brief.yaml"
        path.write_text(yaml.safe_dump(self.brief, allow_unicode=True), encoding="utf-8")

    def save_card(self):
        self.card["prepared_from_author_brief_sha256"] = checker.digest(self.root / "paper_author_brief.yaml")
        (self.root / "card.yaml").write_text(yaml.safe_dump(self.card, allow_unicode=True), encoding="utf-8")

    def check(self):
        self.save_card()
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        node = copy.deepcopy(self.node)
        missing, failures = [], []
        checker._validate_chapter_writing_cards(self.root, self.node, missing, failures)
        self.assertEqual(node, self.node)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)
        return missing, failures

    def test_support_chapter_can_explain_why_it_has_no_abstract_claim(self):
        self.assertEqual(self.check(), ([], []))

    def test_support_chapter_with_an_actual_contribution_keeps_the_original_contract(self):
        self.card["abstract_contribution"] = {"method": "method", "result": "result", "meaning": "meaning",
                                              "evidence_refs": ["results/frozen.yaml"]}
        self.assertEqual(self.check(), ([], []))
        self.card["abstract_contribution"].pop("result")
        self.assertTrue(any("缺少 result" in item for item in self.check()[1]))

    def test_not_applicable_requires_a_nonempty_reason(self):
        for reason in (None, "", "   "):
            with self.subTest(reason=reason):
                self.card["abstract_contribution"]["reason"] = reason
                self.assertTrue(any("必须说明原因" in item for item in self.check()[1]))

    def test_not_applicable_cannot_include_contradictory_contributions(self):
        for field, value in (("method", "method"), ("result", "result"), ("meaning", "meaning"),
                             ("evidence_refs", ["results/frozen.yaml"])):
            with self.subTest(field=field):
                self.card["abstract_contribution"] = {"status": "not_applicable", "reason": "无独立摘要主张", field: value}
                self.assertTrue(any("不得同时填写" in item for item in self.check()[1]))

    def test_missing_or_unknown_contribution_is_not_implicitly_waived(self):
        for contribution in (None, {}, {"status": "unknown"}):
            with self.subTest(contribution=contribution):
                self.card["abstract_contribution"] = contribution
                self.assertTrue(any("abstract_contribution" in item for item in self.check()[1]))

    def test_modeling_question_cannot_be_waived_even_if_labeled_support(self):
        self.support["chapter_kind"] = "modeling_question"
        self.brief["chapters"][-1] = self.support
        self.write_brief()
        self.assertTrue(any("仅作者简报" in item for item in self.check()[1]))

    def test_question_id_cannot_be_waived_even_if_labeled_support(self):
        self.support["section_id"] = "Qsupport"
        self.brief["chapters"][-1] = self.support
        self.brief["paper_spine"]["support_chapters"] = ["Qsupport"]
        self.brief["paper_spine"]["chapter_order"] = ["Qsupport", "Q1"]
        self.brief["paper_spine"]["chapter_edges"][0]["from"] = "Qsupport"
        self.brief["chapters"][0]["reads_from"] = ["Qsupport"]
        self.card["chapter_id"] = "Qsupport"
        self.write_brief()
        self.assertTrue(any("仅作者简报" in item for item in self.check()[1]))

    def test_core_chapter_cannot_bypass_evidence_by_claiming_support(self):
        self.card["chapter_id"] = "Q1"
        self.card["chapter_role"] = "support"
        self.assertTrue(any("仅作者简报" in item for item in self.check()[1]))

    def test_core_chapter_cannot_declare_its_contribution_not_applicable(self):
        self.card["chapter_id"] = "Q1"
        self.card["chapter_role"] = "core"
        self.assertTrue(any("仅作者简报" in item for item in self.check()[1]))

    def test_support_card_must_agree_with_the_author_brief(self):
        self.card["chapter_role"] = "core"
        self.assertTrue(any("仅作者简报" in item for item in self.check()[1]))

    def test_main_checker_accepts_the_support_record_but_retains_other_gates(self):
        self.save_card()
        contest = self.root / ".contest"
        contest.mkdir()
        control = checker.default_control()
        control["nodes"]["H8"].update(self.node)
        (contest / "harness_control.yaml").write_text(yaml.safe_dump(control, allow_unicode=True), encoding="utf-8")
        (contest / "approval_log.yaml").write_text("approvals: []\n", encoding="utf-8")
        report = checker.check_harness_control(self.root, through="H8")
        self.assertFalse([item for item in report["failures"] if "abstract_contribution" in item], report)
        self.assertNotEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
