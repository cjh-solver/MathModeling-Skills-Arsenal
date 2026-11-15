import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import skill_health_check


class DependencyLayoutTests(unittest.TestCase):
    def create_skill(self, parent, name):
        directory = parent / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text("---\nname: example\n---\n", encoding="utf-8")

    def test_categorized_repository_checks_packages_without_claiming_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            root = skills / "01-core" / "contest-orchestrator"
            root.mkdir(parents=True)
            self.create_skill(skills / "02-modeling", "data-science-stack")
            self.create_skill(skills / "04-figures", "modelviz")
            report = skill_health_check.check(root)
            self.assertNotIn("missing required dependency: data-science-stack", report["failures"])
            self.assertNotIn("missing required dependency: modelviz", report["failures"])
            self.assertIn("missing required dependency: pyomo", report["failures"])
            self.assertIn("dependency layout: categorized skill packages; installation not checked", report["info"])

    def test_flat_layout_does_not_search_unrelated_category_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            root = skills / "contest-orchestrator"
            root.mkdir(parents=True)
            self.create_skill(skills, "data-science-stack")
            self.create_skill(skills / "02-modeling", "modelviz")
            report = skill_health_check.check(root)
            self.assertNotIn("missing required dependency: data-science-stack", report["failures"])
            self.assertIn("missing required dependency: modelviz", report["failures"])
            self.assertIn("dependency layout: flat skill directory", report["info"])


if __name__ == "__main__":
    unittest.main()
