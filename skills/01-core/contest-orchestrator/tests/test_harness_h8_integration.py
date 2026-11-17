import copy
import unittest
from pathlib import Path

import yaml

from scripts import check_harness_control as checker
import test_harness_chapter_parallel as fixtures

ROOT = Path(__file__).resolve().parents[1]


class H8IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ChapterParallelTests("test_final_graphic_closure_checks_actual_latest_prompt_versions")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.closed_case()
        self.root = self.fixture.root
        self.control = self.fixture.control
        self.node = self.control["nodes"]["H8"]
        self.node.update({"writing_started": True, "task_card": "H8C.yaml", "agent_instance_id": "writer",
                          "paper_author_brief": "paper_author_brief.yaml",
                          "abstract_argument_card": "abstract_argument_card.yaml",
                          "model_summary_cards": "model_summary_cards.yaml",
                          "visual_argument_plan": "visual_argument_plan.yaml"})
        self.card = yaml.safe_load((ROOT / "templates/b_project_template/.contest/task_cards/H8.yaml").read_text(encoding="utf-8-sig"))
        self.card["task_id"] = "integration"
        self.card["authoring_protocol"]["stage"] = "H8C"
        self.card["authoring_protocol"]["active_chapter_only"] = False
        self.card["scope"] = "按最终目录整合全部已批准章节与选定图件"
        for item in self.card["inputs"]:
            path = self.root / item["path"]
            if not path.exists():
                self.fixture.put(item["path"], "synthetic input")
            item["sha256"] = checker.digest(path)
        missing, failures = [], []
        self.proof = checker._validate_writer_preparation(self.root, self.control, self.fixture.log, missing, failures)
        self.assertEqual((missing, failures), ([], []))
        refs = [self.proof, self.proof["figure_registry"], *self.proof["approved_chapters"]]
        for ref in refs:
            self.card["inputs"].append({"path": ref["path"], "sha256": ref["sha256"]})
        self.save_card()

    def save_card(self):
        self.fixture.put("H8C.yaml", self.card)

    def check(self, proof=None, control=None):
        missing, failures = [], []
        checker._validate_task_card(self.root, "H8", self.node, checker.AGENT_RUNTIME_BY_NODE["H8"], set(),
                                   missing, failures, control=self.control if control is None else control,
                                   chapter_plan=self.proof if proof is None else proof)
        return missing, failures

    def test_approved_chapters_are_in_final_reading_order_and_h8c_accepts_them(self):
        self.assertEqual([item["chapter_id"] for item in self.proof["approved_chapters"]], ["analysis", "Q1"])
        self.assertEqual(self.check(), ([], []))

    def test_h8c_checks_without_mutating_project_files_or_approval_history(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        control, log = copy.deepcopy(self.control), copy.deepcopy(self.fixture.log)
        self.assertEqual(self.check(), ([], []))
        self.assertEqual(control, self.control)
        self.assertEqual(log, self.fixture.log)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)

    def test_each_approved_chapter_must_be_an_input(self):
        original = copy.deepcopy(self.card["inputs"])
        for chapter in self.proof["approved_chapters"]:
            with self.subTest(chapter=chapter["chapter_id"]):
                self.card["inputs"] = [item for item in original if item["path"] != chapter["path"]]
                self.save_card()
                self.assertTrue(any("已批准章节" in item for item in self.check()[1]))

    def test_copied_chapter_with_same_contents_does_not_replace_original(self):
        original = self.proof["approved_chapters"][0]
        clone = self.fixture.put("copied.tex", (self.root / original["path"]).read_text(encoding="utf-8"))
        self.card["inputs"] = [clone if item["path"] == original["path"] else item for item in self.card["inputs"]]
        self.save_card()
        self.assertTrue(any("已批准章节" in item for item in self.check()[1]))

    def test_stale_approved_chapter_blocks_integration(self):
        path = self.root / self.proof["approved_chapters"][0]["path"]
        path.write_text("changed", encoding="utf-8")
        self.assertTrue(any("已批准章节" in item for item in self.check()[1]))

    def test_selected_registry_and_approved_plan_are_required(self):
        original = copy.deepcopy(self.card["inputs"])
        for ref in (self.proof, self.proof["figure_registry"]):
            with self.subTest(path=ref["path"]):
                self.card["inputs"] = [item for item in original if item["path"] != ref["path"]]
                self.save_card()
                self.assertTrue(self.check()[1])

    def test_missing_actual_chapter_approval_cannot_create_a_proof(self):
        self.fixture.log["approvals"] = [item for item in self.fixture.log["approvals"] if item["gate"] != "H7_CHAPTER:Q1"]
        missing, failures = [], []
        proof = checker._validate_writer_preparation(self.root, self.control, self.fixture.log, missing, failures)
        self.assertIsNone(proof)
        self.assertTrue(missing or failures)
        self.assertTrue(self.check(proof={})[0])

    def test_unfinished_figure_revision_cannot_create_a_proof(self):
        self.fixture.prompt(self.fixture.prep["chapters"][0], revision="r2", start=17)
        missing, failures = [], []
        proof = checker._validate_writer_preparation(self.root, self.control, self.fixture.log, missing, failures)
        self.assertIsNone(proof)
        self.assertTrue(missing or failures)

    def test_h8c_cannot_bypass_other_workflow_modes(self):
        control = copy.deepcopy(self.control)
        control["visual_workflow"] = "writer_first_draft"
        self.assertTrue(self.check(control=control)[1])

    def test_main_checker_passes_verified_chapters_to_h8c_without_waiving_other_gates(self):
        control = checker.default_control()
        control.update({key: copy.deepcopy(value) for key, value in self.control.items() if key != "nodes"})
        for node_id, node in self.control["nodes"].items():
            control["nodes"][node_id].update(node)
        self.fixture.put(".contest/harness_control.yaml", control)
        self.fixture.put(".contest/approval_log.yaml", self.fixture.log)
        report = checker.check_harness_control(self.root, through="H8")
        errors = [item for item in report["missing"] + report["failures"] if item.startswith("H8C:")]
        self.assertEqual(errors, [], report)
        self.assertEqual([item["chapter_id"] for item in report["h8c_handoff"]["approved_chapters"]], ["analysis", "Q1"])
        self.assertNotEqual(report["status"], "PASS")

    def test_main_checker_does_not_offer_handoff_when_chapter_approval_is_missing(self):
        self.fixture.log["approvals"] = [item for item in self.fixture.log["approvals"] if item["gate"] != "H7_CHAPTER:Q1"]
        control = checker.default_control()
        control.update({key: copy.deepcopy(value) for key, value in self.control.items() if key != "nodes"})
        for node_id, node in self.control["nodes"].items():
            control["nodes"][node_id].update(node)
        self.fixture.put(".contest/harness_control.yaml", control)
        self.fixture.put(".contest/approval_log.yaml", self.fixture.log)
        report = checker.check_harness_control(self.root, through="H8")
        self.assertIsNone(report["h8c_handoff"])
        self.assertNotEqual(report["status"], "PASS")

    def test_wrong_registered_author_brief_is_not_accepted(self):
        self.card["authoring_protocol"]["author_brief"] = "other.yaml"
        self.save_card()
        self.assertTrue(any("paper_author_brief" in item for item in self.check()[0]))

    def test_malformed_or_missing_closure_proof_never_grants_integration(self):
        for proof in ({}, {"approved_chapters": [None]}, {"approved_chapters": []}):
            with self.subTest(proof=proof):
                self.assertTrue(self.check(proof=proof)[0])

    def test_integration_cannot_claim_a_single_chapter_scope(self):
        self.card["authoring_protocol"]["active_chapter_only"] = True
        self.save_card()
        self.assertTrue(any("active_chapter_only" in item for item in self.check()[1]))

    def test_integration_template_exposes_required_current_inputs(self):
        card = yaml.safe_load((ROOT / "templates/harness_h8c_task_card.yaml").read_text(encoding="utf-8-sig"))
        self.assertEqual(card["authoring_protocol"]["stage"], "H8C")
        paths = [entry["path"] for entry in card["inputs"]]
        for required in checker.REQUIRED_INPUT_BY_NODE["H8"]:
            self.assertTrue(any(path.endswith(required) for path in paths), required)
        self.assertIn("global_interface_check.yaml", paths)

    def test_h8b_legacy_still_uses_its_existing_rules(self):
        self.card["authoring_protocol"]["stage"] = "H8B"
        self.node["active_chapter_card"] = "chapter_writing_card.yaml"
        self.node["paper_continuity_context"] = "paper_continuity_context.yaml"
        self.save_card()
        self.assertEqual(self.check(), ([], []))

    def continuity(self, current="analysis", completed="Q1"):
        spine = {"core_chapters": ["Q1"], "support_chapters": ["analysis"],
                 "chapter_order": ["analysis", "Q1"],
                 "chapter_edges": [{"from": "analysis", "to": "Q1", "relation": "feeds", "handoff_question": "Why?"}]}
        brief = self.fixture.put("paper_author_brief.yaml", {"paper_spine": spine, "central_thesis": "thesis", "reader_journey": "journey"})
        card = self.fixture.put("chapter_card.yaml", {"chapter_id": current})
        self.fixture.put("continuity.yaml", {"status": "current", "paper_author_brief_sha256": brief["sha256"],
            "chapter_writing_card_sha256": card["sha256"], "central_thesis": "thesis", "reader_journey": "journey",
            "current_chapter_id": current, "previous_section_takeaway": "prior result", "next_section_question": "next?",
            "completed_chapters": [{"section_id": completed, "takeaway": "result"}],
            "terminology_lock": [], "voice": "academic", "paper_spine": spine})
        self.node.update(active_chapter_card="chapter_card.yaml", paper_continuity_context="continuity.yaml")
        for item in self.card["inputs"]:
            if item["path"] == brief["path"]:
                item["sha256"] = brief["sha256"]
        self.save_card()

    def check_continuity(self, proof):
        missing, failures = [], []
        checker._validate_paper_continuity_context(self.root, self.node, missing, failures, chapter_plan=proof)
        return missing, failures

    def test_h8c_continuity_uses_approved_writing_order_not_reader_order(self):
        self.continuity()
        self.assertEqual(self.check_continuity(self.proof), ([], []))
        control = checker.default_control()
        control.update({key: copy.deepcopy(value) for key, value in self.control.items() if key != "nodes"})
        for node_id, node in self.control["nodes"].items():
            control["nodes"][node_id].update(node)
        self.fixture.put(".contest/harness_control.yaml", control)
        self.fixture.put(".contest/approval_log.yaml", self.fixture.log)
        report = checker.check_harness_control(self.root, through="H8")
        self.assertFalse([item for item in report["failures"] if item.startswith("paper_continuity_context:")], report)
        self.assertNotEqual(report["status"], "PASS")

    def test_h8c_continuity_rejects_chapters_after_current_writing_step(self):
        self.continuity(current="Q1", completed="analysis")
        self.assertTrue(any("必须位于当前章节之前" in item for item in self.check_continuity(self.proof)[1]))

    def test_missing_or_stale_plan_does_not_change_legacy_order_check(self):
        self.continuity()
        self.assertTrue(self.check_continuity(None)[1])
        plan_path = self.root / self.proof["path"]
        plan_path.write_bytes(plan_path.read_bytes() + b"\n# changed")
        self.assertTrue(self.check_continuity(self.proof)[1])

    def test_h8b_keeps_existing_continuity_order(self):
        self.continuity()
        self.card["authoring_protocol"]["stage"] = "H8B"
        self.save_card()
        self.assertTrue(any("必须位于当前章节之前" in item for item in self.check_continuity(self.proof)[1]))

    def test_h8c_continuity_requires_plan_to_cover_paper_spine(self):
        self.continuity()
        bad_plan = self.fixture.put("paper/incomplete-plan.yaml", {"writing_order": ["analysis"]})
        self.assertTrue(any("writing_order" in item for item in self.check_continuity(bad_plan)[1]))

    def test_main_checker_does_not_reuse_writing_order_without_approval(self):
        self.continuity()
        self.fixture.log["approvals"] = [row for row in self.fixture.log["approvals"] if row["gate"] != "H7_CHAPTER:Q1"]
        control = checker.default_control()
        control.update({key: copy.deepcopy(value) for key, value in self.control.items() if key != "nodes"})
        for node_id, node in self.control["nodes"].items():
            control["nodes"][node_id].update(node)
        self.fixture.put(".contest/harness_control.yaml", control)
        self.fixture.put(".contest/approval_log.yaml", self.fixture.log)
        report = checker.check_harness_control(self.root, through="H8")
        self.assertIsNone(report["h8c_handoff"])
        self.assertNotEqual(report["status"], "PASS")
        self.assertTrue(any("H8C:" in item for item in report["missing"] + report["failures"]))


if __name__ == "__main__":
    unittest.main()
