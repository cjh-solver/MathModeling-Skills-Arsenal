import copy
import unittest

from scripts import check_harness_control as checker
import test_harness_chapter_parallel as fixtures


class H8PlanHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ChapterParallelTests("test_final_graphic_closure_checks_actual_latest_prompt_versions")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.closed_case()
        self.root = self.fixture.root
        self.control = self.fixture.control
        self.log = self.fixture.log
        self.node = self.control["nodes"]["H8"]
        self.node.update(
            writing_started=True, writing_plan=self.fixture.plan["path"],
            writing_plan_sha256=self.fixture.plan["sha256"], plan_approved=True,
            plan_review_packet=self.fixture.prep["plan_review_packet"],
        )

    def source(self, admission_only=False):
        missing, failures = [], []
        result = checker._validate_writer_preparation(
            self.root, self.control, self.log, missing, failures, admission_only=admission_only,
        )
        return result, missing, failures

    def check(self, source):
        missing, failures = [], []
        checker._validate_h8_writing_plan(
            self.root, self.node, missing, failures, control=self.control, chapter_plan=source,
        )
        return missing, failures

    def test_closed_chapter_plan_is_consumed_without_legacy_fields_or_rewriting(self):
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        original_control, original_log = copy.deepcopy(self.control), copy.deepcopy(self.log)
        source, missing, failures = self.source()
        self.assertEqual(source, self.fixture.plan)
        self.assertEqual((missing, failures), ([], []))
        self.assertEqual(self.check(source), ([], []))
        self.assertEqual(self.control, original_control)
        self.assertEqual(self.log, original_log)
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)
        plan = checker.load_mapping(self.root / self.node["writing_plan"])
        self.assertFalse({"status", "sections"} & set(plan))

    def test_main_checker_passes_the_existing_closed_plan_to_h8(self):
        control = checker.default_control()
        control.update({key: copy.deepcopy(value) for key, value in self.control.items() if key != "nodes"})
        for node_id, value in self.control["nodes"].items():
            control["nodes"][node_id].update(value)
        self.fixture.put(".contest/harness_control.yaml", control)
        self.fixture.put(".contest/approval_log.yaml", self.log)
        report = checker.check_harness_control(self.root, through="H8")
        plan_errors = [item for item in report["failures"] if item.startswith("H8: writing_plan") or "复用逐章计划" in item]
        self.assertEqual(plan_errors, [], report["failures"])
        self.assertNotEqual(report["status"], "PASS")  # Other formal obligations remain incomplete.

    def test_an_identical_copy_is_not_the_registered_original_plan(self):
        source, _, _ = self.source()
        copied = self.fixture.put("paper/copied-plan.yaml", self.fixture.plan_data)
        self.node.update(writing_plan=copied["path"], writing_plan_sha256=copied["sha256"])
        self.assertEqual(copied["sha256"], source["sha256"])
        self.assertTrue(self.check(source)[1])

    def test_changed_plan_invalidates_a_previously_valid_handoff(self):
        source, _, _ = self.source()
        path = self.root / source["path"]
        path.write_bytes(path.read_bytes() + b"\n# changed after verification\n")
        self.node["writing_plan_sha256"] = checker.digest(path)
        self.assertTrue(self.check(source)[1])

    def test_changed_plan_cannot_produce_a_handoff_by_refreshing_only_h8_hash(self):
        path = self.root / self.fixture.plan["path"]
        path.write_bytes(path.read_bytes() + b"\n# changed approved plan\n")
        self.node["writing_plan_sha256"] = checker.digest(path)
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(missing or failures)
        self.assertTrue(self.check(source)[1])

    def test_h8_registration_must_still_match_the_current_plan_hash(self):
        source, _, _ = self.source()
        self.node["writing_plan_sha256"] = "0" * 64
        self.assertTrue(any("sha256" in item for item in self.check(source)[1]))

    def test_h8_plan_approval_is_not_inferred_from_a_valid_handoff(self):
        source, _, _ = self.source()
        self.node["plan_approved"] = False
        self.assertTrue(any("用户批准" in item for item in self.check(source)[1]))

    def test_h8_still_requires_its_registered_review_packet(self):
        source, _, _ = self.source()
        self.node["plan_review_packet"] = None
        self.assertTrue(any("plan_review_packet" in item for item in self.check(source)[1]))

    def test_missing_actual_plan_approval_blocks_handoff(self):
        self.log["approvals"] = [row for row in self.log["approvals"] if row["gate"] != "H7_WRITING_PLAN"]
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(any("H7_WRITING_PLAN" in item for item in missing + failures))
        self.assertTrue(self.check(source)[1])

    def test_missing_h6_or_chapter_approval_blocks_handoff(self):
        original = copy.deepcopy(self.log["approvals"])
        for gate in ("H6", "H7_CHAPTER:Q1"):
            with self.subTest(gate=gate):
                self.log["approvals"] = [row for row in original if row["gate"] != gate]
                source, missing, failures = self.source()
                self.assertIsNone(source)
                self.assertTrue(missing or failures)
                self.assertTrue(self.check(source)[1])

    def test_stale_approved_chapter_blocks_handoff(self):
        chapter = self.fixture.prep["chapters"][0]
        path = self.root / chapter["draft"]["path"]
        path.write_bytes(path.read_bytes() + b" changed prose")
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(missing or failures)

    def test_changed_frozen_scientific_source_blocks_handoff(self):
        self.fixture.put("results/frozen.yaml", {"result": 2})
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(missing or failures)

    def test_unfinished_graphic_revision_blocks_formal_h8_handoff(self):
        self.fixture.prompt(self.fixture.prep["chapters"][0], revision="r2", start=17)
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(missing or failures)
        self.assertTrue(self.check(source)[1])

    def test_admission_only_validation_does_not_certify_formal_closure(self):
        source, missing, failures = self.source(admission_only=True)
        self.assertEqual((missing, failures), ([], []))
        self.assertIsNone(source)
        self.assertTrue(self.check(source)[1])

    def test_an_open_h7_stage_does_not_certify_formal_closure(self):
        self.control["nodes"]["H7"]["status"] = "draft"
        source, missing, failures = self.source()
        self.assertEqual((missing, failures), ([], []))
        self.assertIsNone(source)
        self.assertTrue(self.check(source)[1])

    def test_invalid_dispatch_receipt_blocks_handoff(self):
        self.control["dispatch_records"][0]["spawn_receipt"]["task_card_sha256"] = "0" * 64
        source, missing, failures = self.source()
        self.assertIsNone(source)
        self.assertTrue(missing or failures)

    def test_legacy_sections_plan_keeps_its_existing_validation(self):
        legacy = {
            "status": "approved", "sections": [{
                "section_id": "Q1", "subproblem_id": "Q1", "page_count": 25,
                "material_refs": [self.fixture.plan], "figure_locations": ["fig-Q1"],
                "claim_ids": ["claim-Q1"], "argument_ids": ["argument-Q1"],
                "reader_question": "Synthetic question", "chapter_answer": "Synthetic answer",
            }],
        }
        reference = self.fixture.put("paper/legacy-plan.yaml", legacy)
        self.node.update(writing_plan=reference["path"], writing_plan_sha256=reference["sha256"])
        self.assertEqual(self.check(None), ([], []))
        legacy["status"] = "review_pending"
        reference = self.fixture.put("paper/legacy-plan.yaml", legacy)
        self.node["writing_plan_sha256"] = reference["sha256"]
        self.assertTrue(any("approved" in item for item in self.check(None)[1]))

    def test_other_workflows_cannot_consume_a_chapter_handoff(self):
        source, _, _ = self.source()
        for workflow in ("writer_first_draft", "legacy"):
            with self.subTest(workflow=workflow):
                self.control["visual_workflow"] = workflow
                self.assertTrue(any("sections" in item for item in self.check(source)[1]))


if __name__ == "__main__":
    unittest.main()
