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


if __name__ == "__main__":
    unittest.main()
