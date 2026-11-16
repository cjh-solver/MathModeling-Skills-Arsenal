import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_evidence_index.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class EvidenceIndexTests(unittest.TestCase):
    def run_script(self, root: Path, *extra: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run([sys.executable, str(SCRIPT), str(root), *extra],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)

    def seed_solution_sources(self, root: Path, legacy_run: bool = True) -> None:
        for name, payload in {
            "model_contract.yaml": "schema_version: '2.1'\nsubproblems: []\n",
            "derivation_registry.yaml": "schema_version: '1.0'\nformulas: []\n",
            "modeling_solution_contract.yaml": "schema_version: '1.0'\nsubproblems: []\n",
        }.items():
            (root / name).write_text(payload, encoding="utf-8")
        if not legacy_run:
            return
        write_json(root / ".contest" / "runs" / "run1" / "run_manifest.json", {
            "schema_version": "1.0", "run_id": "run1", "status": "completed", "exit_code": 0,
            "inputs": [], "outputs": [], "evidence": [], "command": {"argv": ["python"], "cwd": "."}
        })

    def seed_harness_sources(self, root: Path, named: bool = False) -> dict:
        import yaml

        self.seed_solution_sources(root, legacy_run=False)
        paths = {
            "model_contract": "模型/模型.yaml" if named else "model_contract.yaml",
            "run_manifest": "结果/运行.yaml" if named else "run_manifest.yaml",
            "model_summary_cards": "模型/模型卡.yaml" if named else "model_summary_cards.yaml",
            "result_interpretation_cards": "结果/解释.yaml" if named else "result_interpretation_cards.yaml",
            "figure_registry": "图表/图件.yaml" if named else "figure_registry.yaml",
        }
        payloads = {
            "model_contract": {"subproblems": [{"id": "Q1"}]},
            "run_manifest": {"schema_version": "1.0", "node_id": "H5", "status": "verified", "seed": None},
            "model_summary_cards": {"status": "draft", "cards": [{"card_id": "Q1-model", "subproblem_id": "Q1"}]},
            "result_interpretation_cards": {"status": "draft", "cards": [{"card_id": "Q1-result", "subproblem_id": "Q1"}]},
            "figure_registry": {"figures": []},
        }
        for kind, relative in paths.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(payloads[kind], allow_unicode=True), encoding="utf-8")
        control = {"active_mode": "full-contest-harness", "nodes": {
            "H5": {kind: path for kind, path in paths.items() if kind != "figure_registry"},
            "H7": {"figure_registry": paths["figure_registry"]},
        }}
        directory = root / ".contest"
        directory.mkdir(exist_ok=True)
        (directory / "harness_control.yaml").write_text(yaml.safe_dump(control, allow_unicode=True), encoding="utf-8")
        return paths

    def index(self, root: Path) -> dict:
        return json.loads((root / ".contest/evidence_index.json").read_text(encoding="utf-8"))

    def test_current_h5_and_h7_yaml_records_reach_the_delivery_index(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            for name in ("numeric_source_map.json", "citation_map.json"):
                write_json(root / name, {})
            result = self.run_script(root, "--stage", "delivery", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            index = self.index(root)
            self.assertTrue(index["passed"])
            self.assertEqual(index["kinds"]["figure_registry"], "present")
            run = next(source for source in index["sources"] if source["kind"] == "run_manifest")
            self.assertEqual(run["summary"]["status"], "verified")
            self.assertEqual(run["summary"]["node_id"], "H5")

    def test_registered_chinese_paths_override_conventional_and_historical_copies(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root, named=True)
            write_json(root / ".contest/runs/old/run_manifest.json", {"status": "failed"})
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            sources = {source["kind"]: source for source in self.index(root)["sources"]}
            for kind, path in paths.items():
                self.assertEqual(sources[kind]["path"], path)
            self.assertEqual(sources["model_contract"]["summary"]["subproblem_ids"], ["Q1"])

    def test_model_and_result_summaries_preserve_draft_status_and_question_ids(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            sources = {source["kind"]: source for source in self.index(root)["sources"]}
            for kind, card_id in (("model_summary_cards", "Q1-model"), ("result_interpretation_cards", "Q1-result")):
                self.assertIn(kind, sources)
                self.assertEqual(sources[kind]["summary"]["status"], "draft")
                self.assertEqual(sources[kind]["summary"]["subproblem_ids"], ["Q1"])
                self.assertEqual(sources[kind]["summary"]["card_ids"], [card_id])

    def test_current_yaml_names_work_without_control_registration(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            (root / ".contest/harness_control.yaml").unlink()
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(self.index(root)["passed"])

    def test_legacy_file_alias_cannot_read_outside_the_project(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "project"
            root.mkdir()
            self.seed_solution_sources(root)
            external = root.parent / "external.yaml"
            external.write_text("external_marker: untrusted\n", encoding="utf-8")
            source = root / "model_contract.yaml"
            source.unlink()
            try:
                source.symlink_to(external)
            except OSError as error:
                self.skipTest(str(error))
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertFalse(report["passed"])
            self.assertNotIn("external_marker", result.stdout)

    def test_missing_registered_run_is_not_replaced_by_a_default_copy(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root, named=True)
            (root / paths["run_manifest"]).unlink()
            (root / "run_manifest.yaml").write_text("schema_version: '1.0'\nnode_id: H5\nstatus: verified\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            index = self.index(root)
            self.assertFalse(index["passed"])
            self.assertEqual(index["kinds"]["run_manifest"], "missing")
            self.assertTrue(any(paths["run_manifest"] in error for error in index["errors"]))

    def test_malformed_registered_yaml_is_a_structured_gap(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root)
            (root / paths["model_summary_cards"]).write_text("cards: [broken", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            report = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report["passed"])
            self.assertEqual(report["kinds"]["model_summary_cards"], "invalid")

    def test_outside_registration_cannot_borrow_a_default_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "project"
            root.mkdir()
            self.seed_harness_sources(root)
            control = root / ".contest/harness_control.yaml"
            control.write_text("active_mode: full-contest-harness\nnodes: {H5: {model_contract: ../external.yaml}}\n", encoding="utf-8")
            (root.parent / "external.yaml").write_text("external_marker: untrusted\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            index = self.index(root)
            self.assertFalse(index["passed"])
            self.assertFalse(any(source["kind"] == "model_contract" for source in index["sources"]))
            self.assertNotIn("external_marker", result.stdout)

    def test_invalid_registration_shape_cannot_fall_back_to_default(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            control = root / ".contest/harness_control.yaml"
            control.write_text("active_mode: full-contest-harness\nnodes: {H5: {run_manifest: [bad]}}\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.index(root)["passed"])

    def test_malformed_control_does_not_claim_an_authoritative_index(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            (root / ".contest/harness_control.yaml").write_text("nodes: [broken", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            report = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report["passed"])
            self.assertTrue(any("harness_control" in error for error in report["errors"]))

    def test_other_modes_keep_legacy_discovery(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            (root / ".contest/harness_control.yaml").write_text("active_mode: full-contest-mathorcup\nnodes: {H5: {run_manifest: absent.yaml}}\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(self.index(root)["passed"])

    def test_draft_h5_run_is_not_a_completed_result(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root)
            (root / paths["run_manifest"]).write_text("schema_version: '1.0'\nnode_id: H5\nstatus: draft\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("运行清单" in error for error in self.index(root)["errors"]))

    def test_generic_verified_run_is_not_treated_as_a_completed_capture(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root)
            (root / ".contest/harness_control.yaml").unlink()
            (root / paths["run_manifest"]).write_text("schema_version: '1.0'\nstatus: verified\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(any("运行清单" in error for error in self.index(root)["errors"]))

    def test_explicit_h5_registration_supports_legacy_missing_node_id(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = self.seed_harness_sources(root)
            (root / paths["run_manifest"]).write_text("schema_version: '1.0'\nstatus: verified\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            run = next(source for source in self.index(root)["sources"] if source["kind"] == "run_manifest")
            self.assertTrue(run["registered"])
            self.assertIsNone(run["summary"]["node_id"])

    def test_failed_legacy_capture_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            write_json(root / ".contest/runs/run1/run_manifest.json", {"status": "failed", "exit_code": 1})
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.index(root)["passed"])

    def test_output_cannot_overwrite_an_indexed_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            source = root / "model_contract.yaml"
            before = (source.read_bytes(), source.stat().st_mtime_ns)
            result = self.run_script(root, "--stage", "solution", "--strict", "--out", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)

    def test_output_cannot_overwrite_the_control_record(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            source = root / ".contest/harness_control.yaml"
            before = (source.read_bytes(), source.stat().st_mtime_ns)
            result = self.run_script(root, "--stage", "solution", "--strict", "--out", str(source))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)

    def test_hardlinked_output_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            source, alias = root / "model_contract.yaml", root / "index-alias.json"
            try:
                os.link(source, alias)
            except OSError as error:
                self.skipTest(str(error))
            before = source.read_bytes()
            result = self.run_script(root, "--stage", "solution", "--strict", "--out", str(alias))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), before)

    def test_rebuilding_the_derived_index_keeps_source_files_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_harness_sources(root)
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.rglob("*") if path.is_file()}
            for _ in range(2):
                result = self.run_script(root, "--stage", "solution", "--strict")
                self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}, before)

    def test_strict_solution_builds_derived_index(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.seed_solution_sources(root)
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            index = json.loads((root / ".contest" / "evidence_index.json").read_text(encoding="utf-8"))
            self.assertTrue(index["derived"])
            self.assertTrue(index["passed"])
            self.assertEqual(index["kinds"]["run_manifest"], "present")

    def test_strict_solution_fails_with_missing_core_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "model_contract.yaml").write_text("subproblems: []\n", encoding="utf-8")
            result = self.run_script(root, "--stage", "solution", "--strict")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("缺少证据来源", result.stdout)

    def test_non_strict_missing_sources_is_visible_warning(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = self.run_script(root, "--stage", "solution")
            self.assertEqual(result.returncode, 0)
            index = json.loads((root / ".contest" / "evidence_index.json").read_text(encoding="utf-8"))
            self.assertFalse(index["passed"])
            self.assertTrue(index["warnings"])


if __name__ == "__main__":
    unittest.main()
