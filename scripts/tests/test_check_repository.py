import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_repository


class RepositoryCheckTests(unittest.TestCase):
    def test_skill_readme_image_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "CONTRIBUTING.md"):
                (root / name).write_text("", encoding="utf-8")
            skill = root / "skills" / "figures" / "example"
            skill.mkdir(parents=True)
            (skill / "README.md").write_text('<img src="preview.png">', encoding="utf-8")
            with patch.object(check_repository, "ROOT", root), patch.object(
                check_repository.subprocess, "check_output", return_value=b""
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(check_repository.main(), 1)
                self.assertIn("Broken image:", output.getvalue())
                (skill / "preview.png").write_bytes(b"fixture")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(check_repository.main(), 0)


if __name__ == "__main__":
    unittest.main()
