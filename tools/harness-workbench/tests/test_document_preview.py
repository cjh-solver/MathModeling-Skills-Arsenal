import csv
import io
import json
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import app


class DocumentPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        (self.project / ".contest").mkdir(parents=True)
        (self.project / ".contest/harness_control.yaml").write_text(
            "active_mode: full-contest-harness\nnodes: {}\n", encoding="utf-8"
        )

        class PreviewHandler(app.Handler):
            def log_message(self, *args):
                pass

        PreviewHandler.project = self.project
        PreviewHandler.links_path = Path(self.temp.name) / "links.json"
        server = ThreadingHTTPServer(("127.0.0.1", 0), PreviewHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_port}"

    def preview(self, path):
        query = urllib.parse.urlencode({"path": path.name})
        with urllib.request.urlopen(self.base + "/api/document?" + query) as response:
            return json.load(response)

    def workbook(self, dimension):
        source, target = self.project / "source.xlsx", self.project / "结果.xlsx"
        workbook = app.openpyxl.Workbook()
        sheet = workbook.active
        for cell, value in {
            "A1": "=1+1", "C1": "第三列", "B3": 0, "D3": False,
            "D4": "x" * 6000, "F29": "尾部文本", "U1": "outside columns", "A31": "outside rows",
        }.items():
            sheet[cell] = value
        workbook.save(source)
        workbook.close()
        with zipfile.ZipFile(source) as archive, zipfile.ZipFile(target, "w") as output:
            for entry in archive.infolist():
                data = archive.read(entry.filename)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    self.assertIn(b'dimension ref="A1:U31"', data)
                    data = data.replace(b'dimension ref="A1:U31"', f'dimension ref="{dimension}"'.encode())
                output.writestr(entry, data)
        return target

    @unittest.skipIf(app.openpyxl is None, "openpyxl is optional")
    def test_understated_dimensions_do_not_hide_bounded_cells(self):
        path = self.workbook("A1:A1")
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        rows = self.preview(path)["rows"]
        self.assertEqual(len(rows), 29)
        self.assertTrue(all(len(row) == 6 for row in rows))
        self.assertEqual(rows[0][:3], ["=1+1", "", "第三列"])
        self.assertEqual(rows[1], [""] * 6)
        self.assertEqual(rows[2][1], "0")
        self.assertEqual(rows[2][3], "False")
        self.assertEqual(len(rows[3][3]), 5000)
        self.assertEqual(rows[28][5], "尾部文本")
        self.assertNotIn("outside columns", str(rows))
        self.assertNotIn("outside rows", str(rows))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    @unittest.skipIf(app.openpyxl is None, "openpyxl is optional")
    def test_overstated_dimensions_remain_within_preview_limits(self):
        path = self.workbook("A1:XFD1048576")
        rows = self.preview(path)["rows"]
        self.assertEqual(len(rows), 29)
        self.assertTrue(all(len(row) == 20 for row in rows))
        self.assertEqual(rows[2][1], "0")
        self.assertEqual(rows[2][3], "False")

    @unittest.skipIf(app.openpyxl is None, "openpyxl is optional")
    def test_short_and_empty_sheets_do_not_expand_to_thirty_blank_rows(self):
        path = self.project / "short.xlsx"
        workbook = app.openpyxl.Workbook()
        workbook.active["C1"] = "one row"
        workbook.save(path)
        self.assertEqual(self.preview(path)["rows"], [["", "", "one row"]])
        workbook.active["C1"] = None
        workbook.save(path)
        workbook.close()
        self.assertEqual(self.preview(path)["rows"], [])

    def test_delimited_previews_preserve_encoding_and_quoted_fields(self):
        for extension, delimiter in (("csv", ","), ("TSV", "\t")):
            for encoding in ("utf-8-sig", "gb18030"):
                with self.subTest(extension=extension, encoding=encoding):
                    rows = [["名称", "数值", "说明"], ["风电", "0", f"a{delimiter}b\n第二行"]]
                    text = io.StringIO(newline="")
                    csv.writer(text, delimiter=delimiter).writerows(rows)
                    path = self.project / ("数据." + extension)
                    path.write_bytes(text.getvalue().encode(encoding))
                    before = (path.read_bytes(), path.stat().st_mtime_ns)
                    preview = self.preview(path)
                    self.assertEqual(preview["type"], extension.lower())
                    self.assertEqual(preview["rows"], rows)
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)


if __name__ == "__main__":
    unittest.main()
