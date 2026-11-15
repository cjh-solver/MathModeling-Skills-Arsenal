import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'import_public_jsonl.py'
spec = importlib.util.spec_from_file_location('public_jsonl_importer', SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class PublicJsonlLimitationsTests(unittest.TestCase):
    def test_import_preserves_scalar_and_list_limitations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [
                {'case_id': 'one', 'model_chosen': 'model', 'model_limitations': '极端天气造成偏差'},
                {'case_id': 'two', 'model_chosen': 'model', 'model_limitations': ['数据较少', '成本较高']},
                {'case_id': 'three', 'model_chosen': 'model', 'model_limitations': None},
            ]
            source = root / 'cases.jsonl'
            source.write_text(''.join(json.dumps(case, ensure_ascii=False) + '\n' for case in cases), encoding='utf-8')
            original_inbox = importer.INBOX
            importer.INBOX = str(root / 'inbox')
            self.addCleanup(setattr, importer, 'INBOX', original_inbox)
            with contextlib.redirect_stdout(io.StringIO()):
                importer.main([str(source), '--apply'])
            outputs = [(root / 'inbox' / 'public_cases' / case['case_id'] / 'sd_model.yaml').read_text(encoding='utf-8') for case in cases]
            self.assertIn('limitations: 极端天气造成偏差\n', outputs[0])
            self.assertIn('limitations: 数据较少；成本较高\n', outputs[1])
            self.assertIn('limitations: \n', outputs[2])

    def test_invalid_limitations_fail_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'cases.jsonl'
            source.write_text(json.dumps({'case_id': 'bad', 'model_chosen': 'model', 'model_limitations': ['valid', 1]}), encoding='utf-8')
            original_inbox = importer.INBOX
            importer.INBOX = str(root / 'inbox')
            self.addCleanup(setattr, importer, 'INBOX', original_inbox)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                importer.main([str(source), '--apply'])
            self.assertFalse((root / 'inbox').exists())

    def test_invalid_or_duplicate_ids_never_write_partial_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'cases.jsonl'
            old = importer.INBOX
            importer.INBOX = str(root / 'inbox')
            self.addCleanup(setattr, importer, 'INBOX', old)
            for bad_id in ('../outside', '/absolute', r'..\outside', 'CON', 'case.', '', 3):
                cases = [{'case_id': 'good'}, {'case_id': bad_id}]
                source.write_text(''.join(json.dumps(case) + '\n' for case in cases), encoding='utf-8')
                with self.subTest(bad_id=bad_id), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    importer.main([str(source), '--apply'])
                self.assertFalse((root / 'inbox').exists())
            source.write_text('{"case_id":"A"}\n{"case_id":"a"}\n', encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                importer.main([str(source), '--apply'])
            self.assertFalse((root / 'inbox').exists())
            source.write_text('{"case_id":"good"}\n', encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                importer.main([str(source), '--prefix', '../', '--apply'])
            self.assertFalse((root / 'inbox').exists())

    def test_linked_case_directory_cannot_escape_inbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'cases.jsonl'
            source.write_text('{"case_id":"linked"}\n', encoding='utf-8')
            inbox = root / 'inbox'
            cases = inbox / 'public_cases'
            cases.mkdir(parents=True)
            outside = root / 'outside'
            outside.mkdir()
            try:
                (cases / 'linked').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks are unavailable')
            old = importer.INBOX
            importer.INBOX = str(inbox)
            self.addCleanup(setattr, importer, 'INBOX', old)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                importer.main([str(source), '--apply'])
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((inbox / 'public_review_manifest.csv').exists())

    def test_case_junction_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'cases.jsonl'
            source.write_text('{"case_id":"linked"}\n', encoding='utf-8')
            old = importer.INBOX
            importer.INBOX = str(root / 'inbox')
            self.addCleanup(setattr, importer, 'INBOX', old)
            with mock.patch.object(importer.os.path, 'isjunction', lambda path: Path(path).name == 'linked', create=True):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    importer.main([str(source), '--apply'])
            self.assertFalse((root / 'inbox').exists())

    def test_import_preserves_prior_manifests_and_existing_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'cases.jsonl'
            source.write_text('{"case_id":"new","model_chosen":"model"}\n', encoding='utf-8')
            inbox = root / 'inbox'
            inbox.mkdir()
            prior_manifest = inbox / 'public_review_manifest.csv'
            prior_manifest.write_text('case_id,review\nold,approved\n', encoding='utf-8')
            old = importer.INBOX
            importer.INBOX = str(inbox)
            self.addCleanup(setattr, importer, 'INBOX', old)
            with contextlib.redirect_stdout(io.StringIO()):
                importer.main([str(source), '--apply'])
            self.assertEqual(prior_manifest.read_text(encoding='utf-8'), 'case_id,review\nold,approved\n')
            generated = list(inbox.glob('public_review_manifest_*.csv'))
            self.assertEqual(len(generated), 1)
            case = inbox / 'public_cases' / 'new' / 'case_card.yaml'
            case.write_text('reviewed', encoding='utf-8')
            source.write_text('{"case_id":"fresh"}\n{"case_id":"new"}\n', encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                importer.main([str(source), '--apply'])
            self.assertEqual(case.read_text(encoding='utf-8'), 'reviewed')
            self.assertFalse((inbox / 'public_cases' / 'fresh').exists())
            self.assertEqual(len(list(inbox.glob('public_review_manifest_*.csv'))), 1)
            source.write_text('{"case_id":"new","model_chosen":"model"}\n', encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                importer.main([str(source), '--prefix', 'second-', '--apply'])
            self.assertEqual(len(list(inbox.glob('public_review_manifest_*.csv'))), 2)
            self.assertEqual(case.read_text(encoding='utf-8'), 'reviewed')


if __name__ == '__main__':
    unittest.main()
