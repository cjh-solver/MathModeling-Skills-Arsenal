import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicExperienceTests(unittest.TestCase):
    def test_missing_private_experience_loads_no_entries(self):
        script = """
import sys
from pathlib import Path
from memory import retrieval, paper_retrieval

empty = Path(sys.argv[1])
retrieval.DB_FILES = {kind: str(empty / name) for kind, name in (
    ('FD', 'failure.md'), ('SD', 'success.md'),
    ('ST', 'strategy.md'), ('DM', 'decision.md'))}
paper_retrieval.WR_DB = str(empty / 'writing.md')
assert retrieval.load_entries() == []
assert paper_retrieval.load_wr_entries() == []
"""
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run(
                [sys.executable, "-c", script, raw], cwd=ROOT,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
