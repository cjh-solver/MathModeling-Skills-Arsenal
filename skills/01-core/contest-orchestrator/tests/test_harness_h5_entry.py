import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import init_b_project


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "harness_h5_entry", ROOT / "scripts" / "check_harness_control.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
TEMPLATE = ROOT / "templates/b_project_template/.contest/task_cards/H5.yaml"
UPSTREAM_INPUTS = {"problem_statement.md", "literature_sources.yaml"}
DESIGN_OUTPUTS = {"method_transfer_map.json", "model_blueprint.yaml", "model_contract.yaml"}


class MergedH5EntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.card = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8-sig"))
        self.card["task_id"] = "H5-model-and-solve"
        self.card["inputs"] = [self.reference(name) for name in sorted(UPSTREAM_INPUTS)]
        self.path = self.root / "H5-task.yaml"
        self.node = {"task_card": self.path.name, "agent_instance_id": "primary-solver"}
        self.runtime = CHECKER.AGENT_RUNTIME_BY_NODE["H5"]

    def reference(self, name):
        path = self.root / name
        path.write_text("synthetic source\n", encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def check(self):
        self.path.write_text(yaml.safe_dump(self.card, allow_unicode=True), encoding="utf-8")
        missing, failures = [], []
        CHECKER._validate_task_card(self.root, "H5", self.node, self.runtime, set(), missing, failures)
        return missing, failures

    def literature(self, status="approved"):
        h3 = {"status": status}
        for field in ("literature_request", "literature_agent_prompt", "literature_sources"):
            filename = field + ".yaml"
            self.reference(filename)
            h3[field] = filename
        h5 = {}
        for field, filename in (("method_transfer_map", "method_transfer_map.json"),
                                ("model_blueprint", "model_blueprint.yaml"),
                                ("chart_requirements", "chart_requirements.yaml")):
            self.reference(filename)
            h5[field] = filename
        return {"H3": h3, "H5": h5}

    def test_primary_task_accepts_upstream_inputs_before_design_exists(self):
        self.assertTrue(all(not (self.root / name).exists() for name in DESIGN_OUTPUTS))
        self.assertEqual(self.check(), ([], []))

    def test_new_template_does_not_freeze_its_own_design_outputs(self):
        template = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8-sig"))
        input_paths = {item["path"] for item in template["inputs"]}
        self.assertTrue(UPSTREAM_INPUTS.issubset(input_paths))
        self.assertEqual(DESIGN_OUTPUTS & input_paths, set())

    def test_new_template_requests_design_and_result_handoff_outputs(self):
        template = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8-sig"))
        outputs = {item.split("（", 1)[0] for item in template["required_outputs"]}
        required = DESIGN_OUTPUTS | {
            "chart_requirements.yaml", "paper_narrative.yaml", "validation_contract.yaml",
            "model_summary_cards.yaml", "result_interpretation_cards.yaml", "run_manifest.yaml",
        }
        self.assertTrue(required.issubset(outputs), required - outputs)

    def test_real_initializer_keeps_design_outputs_out_of_entry_inputs(self):
        project = self.root / "fresh-project"
        result = init_b_project.init_project(project, "Synthetic H5 entry", "2026-11-17")
        self.assertEqual(result["status"], "success")
        path = project / ".contest/task_cards/H5.yaml"
        card = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual({item["path"] for item in card["inputs"]}, UPSTREAM_INPUTS)
        card["task_id"] = "synthetic-H5-entry"
        for reference in card["inputs"]:
            target = project / reference["path"]
            target.write_text("synthetic approved upstream input\n", encoding="utf-8")
            reference["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        path.write_text(yaml.safe_dump(card, allow_unicode=True), encoding="utf-8")
        missing, failures = [], []
        node = {"task_card": ".contest/task_cards/H5.yaml", "agent_instance_id": "synthetic-solver"}
        CHECKER._validate_task_card(project, "H5", node, self.runtime, set(), missing, failures)
        self.assertEqual((missing, failures), ([], []))
        control = yaml.safe_load((project / ".contest/harness_control.yaml").read_text(encoding="utf-8"))
        approvals = yaml.safe_load((project / ".contest/approval_log.yaml").read_text(encoding="utf-8"))
        self.assertEqual(control["nodes"]["H4"]["status"], "merged")
        self.assertEqual(control["nodes"]["H5"]["status"], "not_started")
        self.assertEqual(approvals["approvals"], [])

    def test_internal_design_iterations_do_not_stale_the_entry_inputs(self):
        original_inputs = copy.deepcopy(self.card["inputs"])
        for revision in ("baseline", "refined"):
            for name in DESIGN_OUTPUTS:
                (self.root / name).write_text(revision, encoding="utf-8")
            with self.subTest(revision=revision):
                self.assertEqual(self.check(), ([], []))
        self.assertEqual(self.card["inputs"], original_inputs)

    def test_upstream_input_edits_still_invalidate_the_task(self):
        (self.root / "problem_statement.md").write_text("changed source\n", encoding="utf-8")
        missing, _ = self.check()
        self.assertTrue(any("输入哈希已变化" in item for item in missing))

    def test_each_upstream_input_remains_required(self):
        original = copy.deepcopy(self.card["inputs"])
        for required in sorted(UPSTREAM_INPUTS):
            with self.subTest(required=required):
                self.card["inputs"] = [item for item in original if item["path"] != required]
                missing, _ = self.check()
                self.assertTrue(any(f"inputs 必须包含 {required}" in item for item in missing))

    def test_legacy_explicit_design_inputs_keep_their_hash_binding(self):
        self.card["inputs"].extend(self.reference(name) for name in sorted(DESIGN_OUTPUTS))
        self.assertEqual(self.check(), ([], []))
        (self.root / "model_blueprint.yaml").write_text("changed legacy input\n", encoding="utf-8")
        missing, _ = self.check()
        self.assertTrue(any("输入哈希已变化" in item for item in missing))

    def test_completion_still_requires_design_files(self):
        nodes = self.literature()
        (self.root / "model_blueprint.yaml").unlink()
        missing, failures = [], []
        CHECKER.validate_literature_gate(self.root, nodes, "H5", missing, failures)
        self.assertTrue(any("H5" in item and "model_blueprint" in item for item in missing))

    def test_completion_still_requires_approved_literature(self):
        nodes = self.literature(status="draft")
        missing, failures = [], []
        CHECKER.validate_literature_gate(self.root, nodes, "H5", missing, failures)
        self.assertTrue(any("文献输入门尚未获批" in item for item in missing))

    def test_legacy_inputs_are_not_silently_migrated(self):
        self.card["inputs"].extend(self.reference(name) for name in sorted(DESIGN_OUTPUTS))
        self.path.write_text(yaml.safe_dump(self.card), encoding="utf-8")
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.root.iterdir()}
        missing, failures = [], []
        CHECKER._validate_task_card(self.root, "H5", self.node, self.runtime, set(), missing, failures)
        self.assertEqual((missing, failures), ([], []))
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)


if __name__ == "__main__":
    unittest.main()
