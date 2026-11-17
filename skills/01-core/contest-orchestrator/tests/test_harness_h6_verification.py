import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import check_harness_control as checker
from scripts import check_visual_evidence as visual_checker
from test_visual_argument_plan import _bind_plan_to_packet, _bind_registry_to_packet, _registry_for, _valid_visual_plan
from test_visual_evidence_packet import _packet


ROOT = Path(__file__).resolve().parents[1]
KINDS = ("validation_contract", "model_summary_cards", "result_interpretation_cards", "visual_evidence_packet")


class H6VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        packet = _packet(self.root)
        self.source = packet["subproblems"][0]["information_units"][0]["evidence_refs"][0]
        self.documents = {
            "visual_evidence_packet": packet,
            "validation_contract": {
                "status": "draft", "key_conclusions": ["Synthetic feasible allocation"],
                "interface_values": {"x": 0}, "symbol_definitions": [{"symbol": "x", "unit": "unit"}],
                "self_verified": ["Synthetic source and result checked"],
            },
            "model_summary_cards": {
                "schema_version": "1.0", "status": "draft", "created_by": "H5",
                "model_contract_sha256": checker.digest(self.root / "model_contract.yaml"),
                "cards": [{
                    "card_id": "Q1-model", "subproblem_id": "Q1", "purpose": "Synthetic allocation",
                    "model_family": "optimization", "parameters": [],
                    "decision_variables": [{"symbol": "x", "meaning": "allocation", "unit": "unit", "domain": "x >= 0"}],
                    "final_formulation": {"kind": "optimization", "expression": "min x, x >= 0"},
                    "solver_interface": {"method": "linear programming", "inputs": ["demand"], "outputs": ["x"]},
                    "source_equation_refs": ["eq:synthetic"],
                    "paper_structure": {
                        "opening_bridge": "Solve the synthetic allocation question.",
                        "numbered_sections": ["模型建立", "模型求解与结果分析"],
                        "summary_location": "模型建立小节末尾", "optional_sections": [],
                    },
                }],
            },
            "result_interpretation_cards": {
                "schema_version": "1.0", "status": "draft", "created_by": "H5",
                "cards": [{
                    "card_id": "Q1-result", "subproblem_id": "Q1", "result_statement": "Synthetic result is zero.",
                    "meaning": "A feasible synthetic allocation exists.", "reasoning_basis": "Compare frozen bounds.",
                    "supported_scope": "Synthetic fixture only.", "evidence_refs": [self.source],
                }],
            },
        }
        for kind, document in self.documents.items():
            self.save(kind + ".yaml", document)
        self.save("problem_statement.md", {"problem": "Synthetic verification fixture"})
        self.save("h6_verification_scope.yaml", {
            "schema_version": "1.0", "mode": "initial_review", "trigger": "h5_result_freeze",
            "changed_artifacts": [], "deep_sample_refs": [self.source],
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
        })
        self.nodes = {
            "H5": {"agent_instance_id": "synthetic-solver", "model_contract": "model_contract.yaml",
                   **{kind: kind + ".yaml" for kind in KINDS}, "review_packet": ".contest/reviews/H5.yaml"},
            "H6": {"status": "review_pending", "agent_instance_id": "H6-agent-01",
                   "task_card": ".contest/task_cards/H6.yaml", "global_interface_check": "global_interface_check.yaml",
                   "model_summary_cards": "model_summary_cards.yaml", "visual_evidence_packet": "visual_evidence_packet.yaml"},
            "H7": {"visual_evidence_packet": "visual_evidence_packet.yaml"},
            "H8": {"writing_started": True, "model_summary_cards": "model_summary_cards.yaml"},
        }
        self.scope = {"subproblems": [{"id": "Q1", "title": "合成小问"}]}
        self.freeze()

    def save(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def reference(self, name):
        return {"path": name, "sha256": checker.digest(self.root / name)}

    def freeze(self):
        self.task = yaml.safe_load((ROOT / "templates/b_project_template/.contest/task_cards/H6.yaml").read_text(encoding="utf-8-sig"))
        self.task["task_id"] = "H6-synthetic-verification"
        for item in self.task["inputs"]:
            item["sha256"] = checker.digest(self.root / item["path"])
        self.save(self.nodes["H6"]["task_card"], self.task)
        self.report = {
            "schema_version": "1.0", "status": "PASS", "verified_by": "H6",
            "verification_agent_instance_id": "H6-agent-01",
            "task_card_path": self.nodes["H6"]["task_card"],
            "task_card_sha256": checker.digest(self.root / self.nodes["H6"]["task_card"]),
            "checks": {name: True for name in checker.INTERFACE_CHECKS}, "issues": [],
            "per_subproblem": [{"subproblem_id": "Q1", "interface_fields": [{
                "field": "allocation", "unit": "unit", "time_scale": "static", "comparison_status": "pass",
                "source_path": self.source["path"], "source_sha256": self.source["sha256"],
            }]}],
            "verified_artifacts": {kind: self.reference(self.nodes["H5"][kind]) for kind in KINDS},
        }
        self.save("global_interface_check.yaml", self.report)
        packet = {
            "node_id": "H5", "summary": "Synthetic H5 review",
            "important_artifacts": [self.reference(self.nodes["H5"][kind]) for kind in KINDS],
            "checks": ["Synthetic source check"], "requested_decision": "approve", "proposed_next_node": "H6",
        }
        self.save(self.nodes["H5"]["review_packet"], packet)
        self.log = {"approvals": [{"gate": "H5", "decision": "approved", "artifact_digests": {
            self.nodes["H5"]["review_packet"]: checker.digest(self.root / self.nodes["H5"]["review_packet"]),
            **{self.nodes["H5"][kind]: checker.digest(self.root / self.nodes["H5"][kind]) for kind in KINDS},
        }}]}

    def visual_project(self):
        plan = _bind_plan_to_packet(_valid_visual_plan())
        plan["scope"] = {"subproblems": ["Q1"], "cross_question_dependencies": False}
        plan["subproblems"] = plan["subproblems"][:1]
        plan["global_visual_slots"][0]["information_unit_ids"] = ["Q1-U01", "Q1-U02"]
        plan["coverage_summary"] = {
            "required_visual_slots": 3, "required_figure_slots": 3, "planned_figure_count": 6,
        }
        registry = _bind_registry_to_packet(plan, _registry_for(plan))
        for entry in registry["figures"]:
            self.save(entry["template_fixture"]["report"], {
                "status": "passed", "template_id": entry["template_id"],
                "template_sha256": entry["template_sha256"], "visual_qa": "passed",
            })
        self.save("visual_argument_plan.yaml", plan)
        self.save("figure_registry.yaml", registry)
        self.nodes["H7"].update({
            "status": "approved", "visual_argument_plan": "visual_argument_plan.yaml",
            "model_summary_cards": "model_summary_cards.yaml", "figure_registry": "figure_registry.yaml",
        })
        control = checker.default_control()
        control["problem_scope"] = self.scope
        for node_id, node in self.nodes.items():
            control["nodes"][node_id].update(node)
        self.save(".contest/harness_control.yaml", control)
        self.save(".contest/approval_log.yaml", self.log)
        content_plan = {
            "visual_policy": {"mode": "reader_first_coverage"},
            "content_budget": {"subproblems": [{
                "id": "Q1", "visual_decision": {
                    "status": "not_applicable", "rationale": "Synthetic fixture checks the registered H7 plan separately.",
                }, "visual_evidence": [],
            }]},
        }
        self.save("content_budget_plan.yaml", content_plan)
        return control, content_plan

    def bindings(self, stage="H6"):
        missing, failures = [], []
        verified = checker._validate_h6_interface(self.root, self.nodes, self.scope, missing, failures, stage)
        return verified or {}, missing, failures

    def check(self, stage="H6"):
        verified, missing, failures = self.bindings(stage)
        checker._validate_task_card(self.root, "H6", self.nodes["H6"], checker.AGENT_RUNTIME_BY_NODE["H6"], set(), missing, failures)
        checker._validate_review(self.root, "H5", self.nodes["H5"], self.log, missing, failures)
        checker._validate_validation_contract(self.root, self.nodes, stage, missing, failures, verification=verified)
        checker._validate_result_interpretation_cards(
            self.root, self.nodes, stage, missing, failures, control={"problem_scope": self.scope}, verification=verified,
        )
        checker._validate_model_summary_cards(self.root, self.nodes, self.scope, missing, failures, through=stage, verification=verified)
        checker._validate_visual_evidence_packet(self.root, self.nodes, self.scope, stage, missing, failures, verification=verified)
        return verified, missing, failures

    def test_detached_h6_verification_preserves_h5_approval_and_frozen_task(self):
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        for stage in ("H6", "H7", "H8", "H9"):
            with self.subTest(stage=stage):
                verified, missing, failures = self.check(stage)
                self.assertEqual(set(verified), set(KINDS))
                self.assertEqual((missing, failures), ([], []))
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)
        for kind in KINDS:
            self.assertEqual(yaml.safe_load((self.root / self.nodes["H5"][kind]).read_text(encoding="utf-8"))["status"], "draft")

    def test_h5_still_reads_the_authored_packet_without_verified_metadata(self):
        missing, failures = [], []
        checker._validate_visual_evidence_packet(self.root, self.nodes, self.scope, "H5", missing, failures)
        self.assertEqual((missing, failures), ([], []))

    def test_main_checker_uses_detached_bindings_without_granting_missing_approvals(self):
        control = checker.default_control()
        control["problem_scope"] = self.scope
        for node_id, node in self.nodes.items():
            control["nodes"][node_id].update(node)
        control["nodes"]["H5"]["status"] = "approved"
        self.save(".contest/harness_control.yaml", control)
        self.save(".contest/approval_log.yaml", self.log)
        report = checker.check_harness_control(self.root, through="H6")
        self.assertEqual(set(report["verified_artifacts"]), set(KINDS))
        self.assertNotEqual(report["status"], "PASS")

    def test_source_changes_invalidate_each_verification_binding(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                path = self.root / self.nodes["H5"][kind]
                original = path.read_bytes()
                path.write_bytes(original + b"\n# changed source\n")
                verified, missing, failures = self.bindings()
                self.assertEqual(verified, {})
                self.assertTrue(missing or failures)
                path.write_bytes(original)

    def test_every_artifact_binding_is_required(self):
        original = copy.deepcopy(self.report["verified_artifacts"])
        for kind in KINDS:
            with self.subTest(kind=kind):
                self.report["verified_artifacts"] = {name: value for name, value in original.items() if name != kind}
                self.save("global_interface_check.yaml", self.report)
                verified, missing, failures = self.bindings()
                self.assertEqual(verified, {})
                self.assertTrue(any(kind in item for item in missing + failures))

    def test_matching_hash_cannot_bind_a_different_registered_source(self):
        self.report["verified_artifacts"]["model_summary_cards"] = self.reference("result_interpretation_cards.yaml")
        self.save("global_interface_check.yaml", self.report)
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("model_summary_cards" in item for item in failures))

    def test_unchanged_source_must_be_a_frozen_h6_input(self):
        self.task["inputs"] = [entry for entry in self.task["inputs"] if entry["path"] != "model_summary_cards.yaml"]
        self.save(self.nodes["H6"]["task_card"], self.task)
        self.report["task_card_sha256"] = checker.digest(self.root / self.nodes["H6"]["task_card"])
        self.save("global_interface_check.yaml", self.report)
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("冻结输入" in item for item in failures))

    def test_changes_to_other_task_inputs_also_invalidate_verification(self):
        (self.root / "problem_statement.md").write_text("changed problem\n", encoding="utf-8")
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("任务输入" in item for item in failures))

    def test_failed_interface_check_cannot_grant_verified_views(self):
        self.report["checks"]["units"] = False
        self.save("global_interface_check.yaml", self.report)
        verified, missing, _ = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(missing)

    def test_stale_task_card_or_wrong_verifier_cannot_grant_verified_views(self):
        for field, value in (("task_card_sha256", "0" * 64), ("verification_agent_instance_id", "another-verifier")):
            with self.subTest(field=field):
                original = self.report[field]
                self.report[field] = value
                self.save("global_interface_check.yaml", self.report)
                verified, _, failures = self.bindings()
                self.assertEqual(verified, {})
                self.assertTrue(failures)
                self.report[field] = original

    def test_h5_instance_cannot_sign_its_own_verification(self):
        self.nodes["H5"]["agent_instance_id"] = self.nodes["H6"]["agent_instance_id"]
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("独立" in item for item in failures))

    def test_rejected_or_stale_sources_are_not_released_by_an_attestation(self):
        for status in ("stale", "evidence_gap", "rejected"):
            with self.subTest(status=status):
                data = copy.deepcopy(self.documents["model_summary_cards"])
                data["status"] = status
                self.save("model_summary_cards.yaml", data)
                self.freeze()
                _, _, failures = self.check()
                self.assertTrue(any("源状态" in item for item in failures), failures)

    def test_verification_does_not_waive_missing_model_content(self):
        data = copy.deepcopy(self.documents["model_summary_cards"])
        data["cards"][0]["final_formulation"]["expression"] = ""
        self.save("model_summary_cards.yaml", data)
        self.freeze()
        _, _, failures = self.check()
        self.assertTrue(any("final_formulation" in item for item in failures), failures)

    def test_verified_view_does_not_mutate_its_document_and_detects_report_changes(self):
        verified, missing, failures = self.bindings()
        self.assertEqual((missing, failures), ([], []))
        original = copy.deepcopy(self.documents["model_summary_cards"])
        path = self.root / "model_summary_cards.yaml"
        view = checker._h6_verified_document(self.root, path, original, "model_summary_cards", verified, failures)
        self.assertEqual(view["status"], "verified")
        self.assertEqual(original["status"], "draft")
        (self.root / "global_interface_check.yaml").write_text("status: PAUSE\n", encoding="utf-8")
        view = checker._h6_verified_document(self.root, path, original, "model_summary_cards", verified, failures)
        self.assertEqual(view["status"], "draft")
        self.assertTrue(failures)

    def test_legacy_verified_sources_remain_readable_without_detached_records(self):
        for kind, original in self.documents.items():
            self.save(kind + ".yaml", {**original, "status": "verified", "verified_by": "H6",
                                      "verification_agent_instance_id": "H6-agent-01"})
        self.freeze()
        del self.report["verified_artifacts"]
        self.save("global_interface_check.yaml", self.report)
        verified, missing, failures = self.check()
        self.assertEqual(verified, {})
        self.assertEqual((missing, failures), ([], []))

    def test_h6_verification_record_does_not_replace_human_approval(self):
        packet = {"node_id": "H6", "summary": "Synthetic H6 review",
                  "important_artifacts": [self.reference("global_interface_check.yaml")],
                  "checks": ["Synthetic independent verification"], "requested_decision": "approve",
                  "proposed_next_node": "H7"}
        self.save(".contest/reviews/H6.yaml", packet)
        node = {"review_packet": ".contest/reviews/H6.yaml"}
        missing, failures = [], []
        checker._validate_review(self.root, "H6", node, self.log, missing, failures)
        self.assertTrue(any("user_approval" in item for item in missing))
        self.assertEqual(failures, [])

    def test_malformed_or_unknown_verification_bindings_are_rejected(self):
        for bindings in ([], "verified", {**self.report["verified_artifacts"], "other": self.source}):
            with self.subTest(bindings=bindings):
                report = {**self.report, "verified_artifacts": bindings}
                self.save("global_interface_check.yaml", report)
                verified, _, failures = self.bindings()
                self.assertEqual(verified, {})
                self.assertTrue(failures)

    def test_absolute_source_path_cannot_replace_the_project_relative_binding(self):
        self.report["verified_artifacts"]["model_summary_cards"]["path"] = str(self.root / "model_summary_cards.yaml")
        self.save("global_interface_check.yaml", self.report)
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(failures)

    def test_matching_task_hash_does_not_allow_a_different_task_role(self):
        self.task["node_id"] = "H5"
        self.save(self.nodes["H6"]["task_card"], self.task)
        self.report["task_card_sha256"] = checker.digest(self.root / self.nodes["H6"]["task_card"])
        self.save("global_interface_check.yaml", self.report)
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("H6 验证任务卡" in item for item in failures))

    def test_stale_interface_provenance_cannot_grant_verified_views(self):
        self.report["per_subproblem"][0]["interface_fields"][0]["source_sha256"] = "0" * 64
        self.save("global_interface_check.yaml", self.report)
        verified, _, failures = self.bindings()
        self.assertEqual(verified, {})
        self.assertTrue(any("source_sha256" in item for item in failures))

    def test_targeted_h6_record_cannot_replace_full_downstream_interfaces(self):
        for kind in ("model_summary_cards", "result_interpretation_cards"):
            document = copy.deepcopy(self.documents[kind])
            card = copy.deepcopy(document["cards"][0])
            card.update(card_id="Q2-" + kind, subproblem_id="Q2")
            if kind == "model_summary_cards":
                card["final_formulation"]["expression"] = "min x, 0 <= x <= 5"
            document["cards"].append(card)
            self.save(kind + ".yaml", document)
        self.save("q2_evidence.yaml", {"capacity": 5, "feasible_candidates": [0, 1, 2]})
        packet = copy.deepcopy(self.documents["visual_evidence_packet"])
        second = copy.deepcopy(packet["subproblems"][0])
        second["subproblem_id"] = "Q2"
        for unit, statement, locator in zip(second["information_units"],
                ("Q2 的合成资源上限为 5", "Q2 记录三个合成可行候选配置"),
                ("#/capacity", "#/feasible_candidates")):
            unit["unit_id"] = unit["unit_id"].replace("Q1", "Q2")
            unit["statement"] = statement
            unit["evidence_refs"] = [{**self.reference("q2_evidence.yaml"), "locator": locator}]
        packet["subproblems"].append(second)
        self.save("visual_evidence_packet.yaml", packet)
        self.scope["subproblems"].append("Q2")
        self.nodes["H6"]["verification_scope"] = "h6_verification_scope.yaml"
        self.save("h6_verification_scope.yaml", {
            "schema_version": "1.0", "mode": "targeted_recheck", "trigger": "key_result_change",
            "changed_artifacts": [self.source], "deep_sample_refs": [], "rechecked_subproblems": ["Q1"],
            "mandatory_checks": ["contract_anchors", "cross_question_interfaces", "result_interpretation_cards"],
        })
        self.freeze()
        verified, missing, failures = self.check("H6")
        self.assertEqual(set(verified), set(KINDS))
        self.assertEqual((missing, failures), ([], []))
        for stage in ("H7", "H8", "H9"):
            with self.subTest(stage=stage):
                verified, _, failures = self.bindings(stage)
                self.assertEqual(verified, {})
                self.assertTrue(any("Q2" in item for item in failures))


    def test_h7_final_visual_plan_reads_detached_packet_without_approving_generation(self):
        control, _ = self.visual_project()
        verified, missing, failures = self.bindings("H7")
        checker._validate_h7_visual_argument_plan(
            self.root, self.nodes["H7"], control, self.log, missing, failures, verification=verified,
        )
        self.assertEqual(failures, [])
        self.assertTrue(any("H7_VISUAL_PLAN" in item for item in missing))
        self.assertEqual(checker.load_mapping(self.root / "visual_evidence_packet.yaml")["status"], "draft")

    def test_main_checker_shares_verification_with_final_h7_visual_plan(self):
        self.visual_project()
        report = checker.check_harness_control(self.root, through="H7")
        self.assertEqual(set(report["verified_artifacts"]), set(KINDS))
        self.assertFalse(any("H7 visual_argument_plan:" in item for item in report["failures"]), report["failures"])
        self.assertNotEqual(report["status"], "PASS")
        self.assertTrue(any("H7_VISUAL_PLAN" in item for item in report["missing"]))

    def test_standalone_visual_consumers_read_detached_record_without_rewriting_sources(self):
        _, plan = self.visual_project()
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in self.root.rglob("*") if path.is_file()}
        for stage in ("solution", "paper"):
            with self.subTest(stage=stage):
                report = visual_checker.check(plan, self.root, stage, None)
                self.assertEqual(report["status"], "PASS", report)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_visual_evidence.py"), str(self.root), "--stage", "solution"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)

    def test_standalone_visual_consumer_rejects_changed_or_unchecked_h6_record(self):
        _, plan = self.visual_project()
        for field, value in (("task_card_sha256", "0" * 64), ("verification_agent_instance_id", "different-verifier"),
                             ("checks", {**self.report["checks"], "units": False})):
            with self.subTest(field=field):
                original = self.report[field]
                self.report[field] = value
                self.save("global_interface_check.yaml", self.report)
                report = visual_checker.check(plan, self.root, "solution", None)
                self.assertEqual(report["status"], "BLOCK")
                self.assertTrue(any("H6 核验记录" in item for item in report["errors"]), report)
                self.report[field] = original
        self.save("global_interface_check.yaml", self.report)
        (self.root / "visual_evidence_packet.yaml").write_text("status: verified\n", encoding="utf-8")
        self.assertEqual(visual_checker.check(plan, self.root, "paper", None)["status"], "BLOCK")

    def test_standalone_visual_consumer_preserves_legacy_packet_signatures(self):
        _, plan = self.visual_project()
        self.report.pop("verified_artifacts")
        self.save("global_interface_check.yaml", self.report)
        packet = copy.deepcopy(self.documents["visual_evidence_packet"])
        packet.update(status="verified", verified_by="H6", verification_agent_instance_id="H6-agent-01")
        self.save("visual_evidence_packet.yaml", packet)
        report = visual_checker.check(plan, self.root, "solution", None)
        self.assertEqual(report["status"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
