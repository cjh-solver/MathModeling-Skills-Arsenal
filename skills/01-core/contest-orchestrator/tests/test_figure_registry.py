import json
import tempfile
import unittest
from pathlib import Path

from scripts import delivery_gate

from scripts.figure_registry import validate


class FigureRegistryTests(unittest.TestCase):
    def test_current_tikz_flow_passes_both_gates_and_requires_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "evidence.yaml").write_text("status: ready\n", encoding="utf-8")
            (root / "route.tex").write_text("% fixture\n", encoding="utf-8")
            (root / "route.json").write_text("{}\n", encoding="utf-8")
            registry = root / "figure_registry.json"
            figure = {
                "kind": "flowchart", "generator": "tikz-scientific-figures",
                "source_files": ["evidence.yaml"], "script": "route.tex",
                "formats": ["svg", "png"], "insertion_format": "svg",
                "layout_mode": "single", "qa_status": "reviewed",
            }
            for script, should_pass in (("route.tex", True), ("route.json", False)):
                with self.subTest(script=script):
                    figure["script"] = script
                    registry.write_text(json.dumps({"schema_version": "2.0", "figures": {"flow": figure}}), encoding="utf-8")
                    self.assertEqual(validate(registry, root)["passed"], should_pass)
                    issues, warnings, info = [], [], []
                    delivery_gate.figure_registry_checks(root, issues, warnings, info, root)
                    self.assertEqual(not issues, should_pass, issues)

    def test_declared_generation_route_must_match_generator(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "results.json").write_text("{}", encoding="utf-8")
            (root / "plot.py").write_text("# fixture\n", encoding="utf-8")
            registry = root / "figure_registry.json"
            registry.write_text(json.dumps({"schema_version": "2.0", "figures": {
                "fig_q1": {
                    "kind": "data", "generator": "modelviz", "generation_route": "tech-route-maker",
                    "template_status": "native", "semantic_qa": "scipilot-figure-skill",
                    "source_files": ["results.json"], "script": "plot.py", "formats": ["svg", "png"],
                    "insertion_format": "svg", "layout_mode": "single", "qa_status": "pass",
                }
            }}), encoding="utf-8")

            report = validate(registry, root)

            self.assertFalse(report["passed"])
            self.assertIn("fig_q1: generation_route must match generator", report["errors"])

    def test_data_figure_requires_scipilot_decision_card(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "results.json").write_text("{}", encoding="utf-8")
            (root / "plot.py").write_text("# fixture\n", encoding="utf-8")
            registry = root / "figure_registry.json"
            registry.write_text(json.dumps({"schema_version": "2.0", "figures": {
                "fig_q1": {
                    "kind": "data", "generator": "modelviz",
                    "semantic_qa": "scipilot-figure-skill", "source_files": ["results.json"],
                    "script": "plot.py", "formats": ["svg", "png"],
                    "insertion_format": "svg", "layout_mode": "single", "qa_status": "pass",
                }
            }}), encoding="utf-8")

            report = validate(registry, root)

            self.assertFalse(report["passed"])
            self.assertIn("fig_q1: missing decision_card", report["errors"])
            self.assertIn("fig_q1: data figure must record decision_author=scipilot-figure-skill", report["errors"])


if __name__ == "__main__":
    unittest.main()
