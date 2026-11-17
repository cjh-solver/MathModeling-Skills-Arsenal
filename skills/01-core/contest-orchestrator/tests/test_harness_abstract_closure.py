import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import check_abstract_contract as abstract_checker
from scripts import check_harness_control as harness
from scripts import replay_profiles


ROOT = Path(__file__).resolve().parents[1]


class AbstractClosureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        replay_profiles.write_fixture(self.root, "optimization")
        card = {
            "schema_version": "1.0", "status": "approved", "prepared_by": "academic-writing",
            "reader_contract": "reader", "central_thesis": "thesis", "modeling_line": "line", "final_synthesis": "synthesis",
            "questions": [{"id": "Q1", "reader_question": "question", "method": "method", "result": "result",
                           "meaning": "meaning", "evidence_refs": ["results/q1_results.json"]}],
            "validation": {"method": "method", "result": "result"}, "keywords": ["a", "b", "c", "d"],
        }
        (self.root / "abstract_argument_card.yaml").write_text(yaml.safe_dump(card), encoding="utf-8")
        self.node = {"abstract_argument_card": "abstract_argument_card.yaml", "abstract_written": True,
                     "abstract_contract_report": "report.json", "writing_started": True, "paper_source": "paper/paper.tex"}

    def report(self, strict):
        result = abstract_checker.check(self.root / "paper", self.root, strict=strict)
        self.save_report(result)
        return result

    def save_report(self, report):
        (self.root / "report.json").write_text(json.dumps(report), encoding="utf-8")

    def check(self):
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        missing, failures = [], []
        harness._validate_abstract_argument_card(self.root, self.node, {"subproblems": ["Q1"]}, missing, failures)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)
        return missing, failures

    def short_abstract(self):
        (self.root / "paper/paper.tex").write_text(r"\begin{abstract}短摘要。\end{abstract}", encoding="utf-8")

    def test_actual_non_strict_pass_does_not_close_h8(self):
        self.short_abstract()
        report = self.report(strict=False)
        self.assertIs(report["passed"], True)
        self.assertEqual(report["gate_status"], "WARN")
        self.assertTrue(any("strict=true" in item for item in self.check()[1]))

    def test_actual_strict_pass_can_keep_diagnostic_warnings(self):
        report = self.report(strict=True)
        self.assertIs(report["passed"], True, report)
        self.assertEqual(report["gate_status"], "WARN")
        self.assertEqual(self.check(), ([], []))

    def test_actual_strict_failure_still_blocks_h8(self):
        self.short_abstract()
        report = self.report(strict=True)
        self.assertIs(report["passed"], False)
        self.assertTrue(any("passed 必须为 true" in item for item in self.check()[1]))

    def test_missing_or_non_boolean_strict_marker_does_not_close_h8(self):
        report = self.report(strict=True)
        for value in (None, False, "true", 1):
            with self.subTest(value=value):
                report["strict"] = value
                self.save_report(report)
                self.assertTrue(any("strict=true" in item for item in self.check()[1]))
        report.pop("strict")
        self.save_report(report)
        self.assertTrue(any("strict=true" in item for item in self.check()[1]))

    def test_strict_report_still_requires_current_argument_card_hash(self):
        report = self.report(strict=True)
        report["abstract_argument_card_sha256"] = "0" * 64
        self.save_report(report)
        self.assertTrue(any("未绑定当前" in item for item in self.check()[1]))

    def test_changed_abstract_invalidates_the_real_strict_report(self):
        self.report(strict=True)
        self.short_abstract()
        self.assertTrue(any("摘要或关键词已变化" in item for item in self.check()[1]))

    def test_changed_keywords_invalidate_the_report(self):
        self.report(strict=True)
        path = self.root / "paper/paper.tex"
        path.write_text(path.read_text(encoding="utf-8").replace("机理模型；优化算法", "新关键词；优化算法"), encoding="utf-8")
        self.assertTrue(any("摘要或关键词已变化" in item for item in self.check()[1]))

    def test_unrelated_body_and_pdf_metadata_changes_do_not_repeat_abstract_audit(self):
        self.report(strict=True)
        source = self.root / "paper/paper.tex"
        source.write_text(source.read_text(encoding="utf-8") + "\nUnrelated body paragraph.\n", encoding="utf-8")
        import pymupdf
        with pymupdf.open(self.root / "paper/paper.pdf") as document:
            document.set_metadata({"title": "Updated metadata"})
            document.saveIncr()
        self.assertEqual(self.check(), ([], []))

    def test_changed_numeric_evidence_invalidates_the_report(self):
        self.report(strict=True)
        (self.root / "results/q1_results.json").write_text('{"score": 0.5}', encoding="utf-8")
        self.assertTrue(any("数字来源已变化" in item for item in self.check()[1]))

    def test_unused_new_numeric_file_does_not_invalidate_the_report(self):
        self.report(strict=True)
        (self.root / "results/unrelated.json").write_text('{"unrelated": 99999}', encoding="utf-8")
        self.assertEqual(self.check(), ([], []))

    def test_nested_explicit_source_is_bound_and_include_changes_are_detected(self):
        paper = self.root / "paper"
        text = (paper / "paper.tex").read_text(encoding="utf-8")
        (paper / "sections").mkdir()
        (paper / "sections/abstract.tex").write_text(text, encoding="utf-8")
        (paper / "sections/container.tex").write_text(r"\input{abstract}", encoding="utf-8")
        entry = paper / "custom.tex"
        entry.write_text(r"\input{sections/container}", encoding="utf-8")
        report = abstract_checker.check(paper, self.root, strict=True, source_path=entry)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["content_snapshot"]["abstract_source"], "paper/sections/abstract.tex")
        self.save_report(report)
        self.node["paper_source"] = "paper/custom.tex"
        self.assertEqual(self.check(), ([], []))
        (paper / "sections/copy.tex").write_text(text, encoding="utf-8")
        (paper / "sections/container.tex").write_text(r"\input{copy}", encoding="utf-8")
        self.assertTrue(any("实际摘要来源已变化" in item for item in self.check()[1]))

    def test_report_cannot_substitute_an_identical_registered_main_source(self):
        self.report(strict=True)
        other = self.root / "paper/copied.tex"
        other.write_bytes((self.root / "paper/paper.tex").read_bytes())
        self.node["paper_source"] = "paper/copied.tex"
        self.assertTrue(any("paper_source 不一致" in item for item in self.check()[1]))

    def test_coverage_paper_source_is_bound_to_the_abstract_snapshot(self):
        self.report(strict=True)
        other = self.root / "paper/copied.tex"
        other.write_bytes((self.root / "paper/paper.tex").read_bytes())
        coverage = self.root / "paper_claim_coverage.yaml"
        coverage.write_text("paper_source: paper/copied.tex\n", encoding="utf-8")
        self.node.pop("paper_source")
        self.node["paper_claim_coverage"] = "paper_claim_coverage.yaml"
        self.assertTrue(any("paper_source 不一致" in item for item in self.check()[1]))
        coverage.write_text("paper_source: paper/paper.tex\n", encoding="utf-8")
        self.assertEqual(self.check(), ([], []))

    def test_node_paper_source_takes_precedence_over_coverage(self):
        self.report(strict=True)
        (self.root / "paper_claim_coverage.yaml").write_text(
            "paper_source: paper/other.tex\n", encoding="utf-8")
        self.node["paper_claim_coverage"] = "paper_claim_coverage.yaml"
        self.assertEqual(self.check(), ([], []))

    def test_approved_coverage_source_requires_abstract_closure(self):
        (self.root / "paper_claim_coverage.yaml").write_text(
            "paper_source: paper/paper.tex\n", encoding="utf-8")
        self.node.pop("paper_source")
        self.node.update(paper_claim_coverage="paper_claim_coverage.yaml", abstract_written=False, status="approved")
        self.assertTrue(any("abstract_written=true" in item for item in self.check()[0]))

    def test_snapshot_remains_usable_after_project_relocation(self):
        self.report(strict=True)
        with tempfile.TemporaryDirectory() as moved:
            target = Path(moved) / "project"
            shutil.copytree(self.root, target)
            report = json.loads((target / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(abstract_checker.validate_content_snapshot(report, target, "paper/paper.tex"), [])

    def test_explicit_source_cli_binds_the_requested_main_file(self):
        custom = self.root / "paper/custom.tex"
        custom.write_bytes((self.root / "paper/paper.tex").read_bytes())
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/check_abstract_contract.py"),
                                 str(self.root / "paper"), "--project-root", str(self.root), "--strict",
                                 "--source", str(custom), "--out", str(self.root / "report.json")],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["content_snapshot"]["entry_source"], "paper/custom.tex")
        self.node["paper_source"] = "paper/custom.tex"
        self.assertEqual(self.check(), ([], []))

    def test_source_selection_handles_include_cycles_and_rejects_external_sources(self):
        paper = self.root / "paper"
        (paper / "cycle.tex").write_text(r"\input{loop}", encoding="utf-8")
        (paper / "loop.tex").write_text(r"\input{cycle}", encoding="utf-8")
        entry, source = abstract_checker._source_selection(paper, paper / "cycle.tex", self.root)
        self.assertEqual(entry, source)
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "external.tex"
            external.write_text(r"\begin{abstract}外部摘要\end{abstract}", encoding="utf-8")
            with self.assertRaises(ValueError):
                abstract_checker.check(paper, self.root, strict=True, source_path=external)

    def test_h8c_requires_snapshot_but_legacy_report_is_not_rewritten(self):
        report = self.report(strict=True)
        report.pop("content_snapshot")
        self.save_report(report)
        self.assertEqual(self.check(), ([], []))
        task = self.root / "H8C.yaml"
        task.write_text("authoring_protocol: {stage: H8C}\n", encoding="utf-8")
        self.node["task_card"] = "H8C.yaml"
        missing, _ = self.check()
        self.assertTrue(any("缺少内容快照" in item for item in missing))

    def test_snapshot_rejects_external_paths_and_missing_numeric_bindings(self):
        report = self.report(strict=True)
        report["content_snapshot"]["numeric_sources"] = []
        self.save_report(report)
        self.assertTrue(any("数字来源快照不完整" in item for item in self.check()[1]))
        report = self.report(strict=True)
        report["content_snapshot"]["paper"] = "../external.pdf"
        self.save_report(report)
        self.assertTrue(any("摘要快照来源" in item for item in self.check()[1]))

    def test_pdf_only_snapshot_ignores_metadata_and_detects_changed_abstract_text(self):
        import pymupdf
        paper = self.root / "paper"
        source = paper / "paper.tex"
        source.rename(paper / "old-source.txt")
        abstract, _ = abstract_checker._abstract_text(paper / "old-source.txt", "")
        keywords = "关键词：机理模型；优化算法；数据预处理；稳健性分析"
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_textbox(pymupdf.Rect(40, 40, 560, 790), "摘要\n" + abstract + "\n" + keywords,
                                fontsize=8, fontname="china-s")
            document.save(paper / "paper.pdf")
        report = self.report(strict=True)
        self.assertEqual(report["content_snapshot"]["source_kind"], "pdf")
        self.node["paper_source"] = "paper/paper.pdf"
        self.assertEqual(abstract_checker.validate_content_snapshot(report, self.root, "paper/paper.pdf"), [])
        with pymupdf.open(paper / "paper.pdf") as document:
            document.set_metadata({"title": "Metadata only"})
            document.saveIncr()
        self.assertEqual(abstract_checker.validate_content_snapshot(report, self.root, "paper/paper.pdf"), [])
        with pymupdf.open() as document:
            document.new_page().insert_textbox(pymupdf.Rect(40, 40, 560, 790), "摘要\n改变后的摘要\n" + keywords,
                                                fontsize=8, fontname="china-s")
            document.save(paper / "paper.pdf")
        self.assertTrue(any("摘要或关键词已变化" in item for item in
                            abstract_checker.validate_content_snapshot(report, self.root, "paper/paper.pdf")))

    def test_main_h8_entry_rejects_non_strict_report(self):
        self.short_abstract()
        self.report(strict=False)
        contest = self.root / ".contest"
        contest.mkdir(exist_ok=True)
        control = harness.default_control()
        control["nodes"]["H8"].update(self.node)
        control["problem_scope"] = {"subproblems": ["Q1"]}
        (contest / "harness_control.yaml").write_text(yaml.safe_dump(control), encoding="utf-8")
        (contest / "approval_log.yaml").write_text("approvals: []\n", encoding="utf-8")
        report = harness.check_harness_control(self.root, through="H8")
        self.assertTrue(any("strict=true" in item for item in report["failures"]), report)
        self.assertNotEqual(report["status"], "PASS")

    def test_main_h8_entry_rejects_a_report_for_previous_abstract_text(self):
        self.report(strict=True)
        self.short_abstract()
        contest = self.root / ".contest"
        contest.mkdir(exist_ok=True)
        control = harness.default_control()
        control["nodes"]["H8"].update(self.node)
        control["problem_scope"] = {"subproblems": ["Q1"]}
        (contest / "harness_control.yaml").write_text(yaml.safe_dump(control), encoding="utf-8")
        (contest / "approval_log.yaml").write_text("approvals: []\n", encoding="utf-8")
        report = harness.check_harness_control(self.root, through="H8")
        self.assertTrue(any("摘要或关键词已变化" in item for item in report["failures"]), report)
        self.assertNotEqual(report["status"], "PASS")

    def test_main_h8_entry_rejects_a_report_for_a_different_coverage_source(self):
        self.report(strict=True)
        (self.root / "paper/copied.tex").write_bytes((self.root / "paper/paper.tex").read_bytes())
        (self.root / "paper_claim_coverage.yaml").write_text(
            "paper_source: paper/copied.tex\n", encoding="utf-8")
        self.node.pop("paper_source")
        self.node["paper_claim_coverage"] = "paper_claim_coverage.yaml"
        contest = self.root / ".contest"
        contest.mkdir(exist_ok=True)
        control = harness.default_control()
        control["nodes"]["H8"].update(self.node)
        control["problem_scope"] = {"subproblems": ["Q1"]}
        (contest / "harness_control.yaml").write_text(yaml.safe_dump(control), encoding="utf-8")
        (contest / "approval_log.yaml").write_text("approvals: []\n", encoding="utf-8")
        report = harness.check_harness_control(self.root, through="H8")
        self.assertTrue(any("paper_source 不一致" in item for item in report["failures"]), report)
        self.assertNotEqual(report["status"], "PASS")

    def test_omitting_strict_from_real_cli_does_not_produce_a_closure_report(self):
        self.short_abstract()
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/check_abstract_contract.py"),
                                 str(self.root / "paper"), "--project-root", str(self.root)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.node["abstract_contract_report"] = "abstract_contract_report.json"
        self.assertTrue(any("strict=true" in item for item in self.check()[1]))


if __name__ == "__main__":
    unittest.main()
