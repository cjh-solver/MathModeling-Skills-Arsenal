import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_latex_refs.py"


class LatexReferenceChecks(unittest.TestCase):
    def run_check(self, path, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), str(path), *args],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def test_missing_bibliographies_fail_without_citations(self):
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "main.tex"
            for source, args in ((r"\bibliography{missing}", ()), ("No citations", ("--bib", "missing.bib"))):
                with self.subTest(source=source):
                    main.write_text(source, encoding="utf-8")
                    result = self.run_check(main, *args)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("MISSING BIB FILES", result.stdout)
                    self.assertNotIn("PASSED", result.stdout)

    def test_missing_nested_source_fails_but_comments_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            main = root / "main.tex"
            child = root / "part.tex"
            main.write_text("% \\input{commented}\n\\input{part}\n", encoding="utf-8")
            child.write_text("\\begin{verbatim}\n\\input{example}\n\\end{verbatim}\n\\include{absent}\n", encoding="utf-8")
            result = self.run_check(main)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MISSING TEX FILES", result.stdout)
            self.assertIn("absent.tex", result.stdout)
            self.assertNotIn("commented", result.stdout)
            self.assertNotIn("example", result.stdout)
            child.write_text("% \\include{absent}\n", encoding="utf-8")
            result = self.run_check(main)
            self.assertEqual(result.returncode, 0)
            self.assertIn("PASSED", result.stdout)

    def test_existing_nested_source_and_bibliography_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            main = root / "main.tex"
            main.write_text(r"\input{part} \ref{fig:demo} \bibliography{refs}", encoding="utf-8")
            (root / "part.tex").write_text(r"\label{fig:demo} \cite{demo}", encoding="utf-8")
            (root / "refs.bib").write_text("@article{demo, title={Example}}\n", encoding="utf-8")
            result = self.run_check(main)
            self.assertEqual(result.returncode, 0)
            self.assertIn("PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
