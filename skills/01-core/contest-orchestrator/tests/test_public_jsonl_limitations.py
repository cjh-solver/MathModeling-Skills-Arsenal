import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
