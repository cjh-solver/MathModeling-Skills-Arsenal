"""Verify that historical figure migration preserves evidence and source files."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class FigureRegistryMigrationTests(unittest.TestCase):
    def run_migration(self, source, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPTS / "migrate_figure_registry.py"), str(source), *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def test_recorded_metadata_survives_conversion_and_repeated_preview(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, output = root / "registry.json", root / "candidate.json"
            figure = {
                "id": "Q1", "kind": "data", "generator": "modelviz",
                "legacy_generator": "recorded-old-tool", "generated_by": "older-label",
                "source_files": ["results.csv"], "script": "plot.py",
                "svg": "figures/q1.svg", "png": "figures/q1.png",
                "formats": ["svg", "png"], "insertion_format": "svg",
                "layout_mode": "side_by_side", "layout_group": "comparison",
                "layout_variant": "figure_text", "qa_status": "reviewed",
                "decision_author": "scipilot-figure-skill", "decision_card": "decision.yaml",
                "semantic_qa": "scipilot-figure-skill", "visual_qa": "passed",
                "evidence_refs": [{"path": "results.csv", "sha256": "a" * 64}],
                "custom_metadata": {"subproblem_id": "Q1", "caption": "合成图例"},
            }
            source.write_text(json.dumps({
                "schema_version": "2.0", "figures": {"Q1": figure},
                "migrated_at": "2026-11-01T00:00:00+00:00", "registry_note": "synthetic",
            }, ensure_ascii=False), encoding="utf-8")
            for name in ("results.csv", "plot.py", "decision.yaml"):
                (root / name).write_text("synthetic fixture", encoding="utf-8")
            original = source.read_bytes()
            result = self.run_migration(source, "--out", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            converted = json.loads(output.read_text(encoding="utf-8"))
            for key, value in figure.items():
                self.assertEqual(converted["figures"]["Q1"][key], value, key)
            self.assertEqual(converted["registry_note"], "synthetic")
            self.assertEqual(converted["migrated_at"], "2026-11-01T00:00:00+00:00")
            candidate_bytes = output.read_bytes()
            preview = self.run_migration(output, "--check-only")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(json.loads(preview.stdout), converted)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.read_bytes(), candidate_bytes)
            for registry in (source, output):
                gate = subprocess.run(
                    [sys.executable, "-X", "utf8", str(SCRIPTS / "figure_registry.py"), str(registry), "--workspace", str(root), "--strict"],
                    capture_output=True, text=True, encoding="utf-8", check=False,
                )
                self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)

    def test_missing_layout_and_provenance_are_not_fabricated_or_approved(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, output = root / "legacy.json", root / "candidate.json"
            source.write_text(json.dumps({"old": {
                "type": "data", "generated_by": "python-matplotlib", "formats": ["png"],
                "data_source": "results/a.json； results/b.json",
            }}), encoding="utf-8")
            result = self.run_migration(source, "--out", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            figure = json.loads(output.read_text(encoding="utf-8"))["figures"]["old"]
            self.assertEqual(figure["legacy_generator"], "python-matplotlib")
            self.assertEqual(figure["generator"], "")
            self.assertEqual(figure["source_files"], ["results/a.json", "results/b.json"])
            self.assertEqual(figure["qa_status"], "review")
            for absent in ("layout_mode", "decision_author", "semantic_qa", "verified_by"):
                self.assertNotIn(absent, figure)
            gate = subprocess.run(
                [sys.executable, "-X", "utf8", str(SCRIPTS / "figure_registry.py"), str(output), "--workspace", str(root), "--strict"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertNotEqual(gate.returncode, 0)
            self.assertFalse(json.loads(gate.stdout)["passed"])
            self.assertIn("old: missing layout_mode", json.loads(gate.stdout)["errors"])

    def test_ambiguous_or_malformed_records_do_not_create_output(self):
        cases = (
            '{"figures": [{"id": "same"}, {"id": "same"}]}',
            '{"figures": [{"id": "one"}, null]}',
            '{"figures": {"one": null}}',
            '{"figures": {"same": {}, "same": {"generator": "other"}}}',
            '"not a registry"',
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, output = root / "registry.json", root / "candidate.json"
            for content in cases:
                with self.subTest(content=content):
                    source.write_text(content, encoding="utf-8")
                    before = source.read_bytes()
                    result = self.run_migration(source, "--out", output)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
                    self.assertEqual(source.read_bytes(), before)

    def test_output_cannot_replace_the_original_registry(self):
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "registry.json"
            source.write_text('{"figure": {"type": "data"}}', encoding="utf-8")
            before = source.read_bytes()
            result = self.run_migration(source, "--out", source)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), before)

    def test_output_alias_cannot_replace_the_original_registry(self):
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "registry.json"
            source.write_text('{"figure": {"type": "data"}}', encoding="utf-8")
            alias = Path(raw) / "alias.json"
            try:
                os.link(source, alias)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Hard links unavailable: {exc}")
            before = source.read_bytes()
            result = self.run_migration(source, "--out", alias)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), before)

    def test_default_output_does_not_overwrite_an_existing_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "registry.json"
            source.write_text('{"figure": {"type": "data"}}', encoding="utf-8")
            output = source.with_name("figure_registry.v2.json")
            output.write_text('{"manual_review": "preserve"}', encoding="utf-8")
            before = output.read_bytes()
            result = self.run_migration(source)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), before)
