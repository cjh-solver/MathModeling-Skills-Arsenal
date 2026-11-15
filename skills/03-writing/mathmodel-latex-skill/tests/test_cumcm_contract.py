import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "templates" / "cumcm"


class CumcmTemplateContractTests(unittest.TestCase):
    def test_documented_layout_commands_are_available(self):
        source = (ROOT / "cumcm-extras.sty").read_text(encoding="utf-8")
        for name in ("PaperFigure", "PaperTwoColumn", "PaperWrapFigure", "PaperTallFigure"):
            self.assertIn(r"\NewDocumentCommand{" + "\\" + name + "}", source)
        self.assertIn(r"\includesvg", source)
        self.assertNotIn(r"\includegraphics", source)

    def test_entry_templates_enable_layout_and_do_not_force_tables(self):
        for name in ("main.tex", "main-cumcmthesis.tex", "main-ctexart-fallback.tex"):
            with self.subTest(template=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(r"\usepackage{cumcm-extras}", source)
                self.assertNotIn(r"\begin{table}[H]", source)

    def test_layout_reference_uses_svg_examples(self):
        reference = ROOT.parent.parent / "references" / "latex_layout_cheatsheet.md"
        source = reference.read_text(encoding="utf-8")
        self.assertIn(r"\includesvg", source)
        self.assertNotIn(r"\includegraphics", source)

    @unittest.skipUnless(os.environ.get("CUMCM_RUN_LATEX_TESTS") == "1" and shutil.which("xelatex"), "Optional XeLaTeX integration test")
    def test_figplot_resolves_explicit_and_extensionless_svg(self):
        with tempfile.TemporaryDirectory(prefix="figplot-test-") as folder:
            root = Path(folder)
            work = root / "work"
            work.mkdir()
            (work / "figures").mkdir()
            (root / "02_figures").mkdir()
            shutil.copyfile(ROOT / "cumcm-extras.sty", work / "cumcm-extras.sty")
            for target in (work / "direct.svg", work / "figures" / "nested.svg", root / "02_figures" / "outside.svg"):
                target.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            (work / "image.png").write_bytes(b"not used")
            source = r"""\documentclass{ctexart}
\usepackage{booktabs,tabularx,hyperref}
\usepackage{cumcm-extras}
\RenewDocumentCommand{\PaperSvg}{O{\linewidth} m}{\typeout{INSERTED:#2}found}
\begin{document}
\figplot{A}{fig:a}{direct.svg}{}
\figplot{B}{fig:b}{direct}{}
\figplot{C}{fig:c}{nested.svg}{}
\figplot{D}{fig:d}{outside.svg}{}
\figplot{E}{fig:e}{image.png}{}
\end{document}
"""
            (work / "check.tex").write_text(source, encoding="utf-8")
            command = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "check.tex"]
            if os.name == "nt":
                command.insert(1, "--disable-installer")
            result = subprocess.run(command, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45, check=True)
            lines = set(result.stdout.decode("utf-8", "replace").splitlines())
            self.assertTrue({"INSERTED:direct.svg", "INSERTED:direct", "INSERTED:./figures/nested.svg", "INSERTED:../02_figures/outside.svg"} <= lines)
            self.assertFalse(any("INSERTED:image.png" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
