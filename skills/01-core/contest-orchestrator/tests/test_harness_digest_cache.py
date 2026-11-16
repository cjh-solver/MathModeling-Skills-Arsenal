"""Avoid repeated evidence reads without retaining digests between gate calls."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import check_harness_control as checker


class HarnessDigestCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".contest").mkdir()
        (self.root / ".contest/harness_control.yaml").write_text(
            yaml.safe_dump(checker.default_control(), allow_unicode=True), encoding="utf-8",
        )
        self.evidence = self.root / "evidence.txt"
        self.evidence.write_bytes(b"original")

    def run_gate(self, action):
        with patch.object(checker, "_validate_narrative", side_effect=lambda *args: action()):
            return checker.check_harness_control(self.root, through="H0")

    def test_repeated_evidence_reads_are_shared_within_one_gate(self):
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
            def inspect():
                first = checker.digest(self.evidence)
                second = checker.digest(self.root / "." / "evidence.txt")
                self.assertEqual(first, hashlib.sha256(b"original").hexdigest())
                self.assertEqual(second, first)
            self.run_gate(inspect)
            self.assertEqual(reads.call_count, 1)

    def test_next_gate_reads_evidence_again(self):
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
            self.run_gate(lambda: checker.digest(self.evidence))
            self.run_gate(lambda: checker.digest(self.evidence))
            self.assertEqual(reads.call_count, 2)

    def test_plain_digest_calls_do_not_reuse_gate_state(self):
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
            checker.digest(self.evidence)
            checker.digest(self.evidence)
            self.assertEqual(reads.call_count, 2)

    def test_same_size_edit_with_restored_mtime_invalidates_digest(self):
        def inspect():
            first = checker.digest(self.evidence)
            original_stat = self.evidence.stat()
            self.evidence.write_bytes(b"modified")
            os.utime(self.evidence, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            second = checker.digest(self.evidence)
            self.assertNotEqual(second, first)
            self.assertEqual(second, hashlib.sha256(b"modified").hexdigest())
        self.run_gate(inspect)

    def test_replaced_file_does_not_keep_previous_digest(self):
        def inspect():
            first = checker.digest(self.evidence)
            original_stat = self.evidence.stat()
            replacement = self.root / "replacement.txt"
            replacement.write_bytes(b"replaced")
            os.utime(replacement, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            replacement.replace(self.evidence)
            self.assertNotEqual(checker.digest(self.evidence), first)
            self.assertEqual(checker.digest(self.evidence), hashlib.sha256(b"replaced").hexdigest())
        self.run_gate(inspect)

    def test_exception_discards_gate_state(self):
        def inspect():
            checker.digest(self.evidence)
            raise RuntimeError("Interrupted gate")
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
            with self.assertRaisesRegex(RuntimeError, "Interrupted gate"):
                self.run_gate(inspect)
            checker.digest(self.evidence)
            self.assertEqual(reads.call_count, 2)

    def test_file_changed_during_read_is_not_cached(self):
        original_read = Path.read_bytes
        reads = []

        def read_then_modify(path):
            value = original_read(path)
            reads.append(path)
            if len(reads) == 1:
                path.write_bytes(b"modified")
            return value

        def inspect():
            checker.digest(self.evidence)
            current = checker.digest(self.evidence)
            self.assertEqual(current, hashlib.sha256(b"modified").hexdigest())
            self.assertEqual(checker.digest(self.evidence), current)

        with patch.object(Path, "read_bytes", read_then_modify):
            self.run_gate(inspect)
        self.assertEqual(len(reads), 2)

    def test_nested_gate_reuses_outer_call_only(self):
        def inspect():
            checker.digest(self.evidence)
            self.run_gate(lambda: checker.digest(self.evidence))
            checker.digest(self.evidence)
        with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
            self.run_gate(inspect)
            self.assertEqual(reads.call_count, 1)

    def test_unknown_change_metadata_disables_reuse(self):
        def inspect():
            checker.digest(self.evidence)
            checker.digest(self.evidence)
        with patch.object(checker, "_digest_signature", return_value=None):
            with patch.object(Path, "read_bytes", autospec=True, side_effect=Path.read_bytes) as reads:
                self.run_gate(inspect)
                self.assertEqual(reads.call_count, 2)

    def test_deleted_file_is_not_satisfied_by_cached_digest(self):
        def inspect():
            checker.digest(self.evidence)
            self.evidence.unlink()
            with self.assertRaises(FileNotFoundError):
                checker.digest(self.evidence)
        self.run_gate(inspect)


if __name__ == "__main__":
    unittest.main()
