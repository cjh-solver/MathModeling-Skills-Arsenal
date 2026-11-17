import json
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
