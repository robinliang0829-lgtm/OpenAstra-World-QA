"""Export completeness failures must remain visible across engine and reports."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from worldqa.engine import inspect_scene
from worldqa.report import render_html, render_markdown


ROOT = Path(__file__).resolve().parents[1]


def scene():
    return {
        "schema_version": "worldqa.scene.v1", "scene_id": "export-completeness",
        "evidence_kind": "engine_export", "units": "meters",
        "coordinate_system": "RH_Y_UP", "track_links": [], "routes": [],
        "objects": [{"id": "station", "role": "building", "position": [0, 0, 0],
                     "base_y": 0, "support_y": 0}],
    }


class ExportEvidenceTests(unittest.TestCase):
    def test_skipped_export_object_blocks_otherwise_passing_scene(self):
        data = scene()
        data["export_warnings"] = ["/Island/MissingStation: qainfo is not a Dictionary"]
        original = copy.deepcopy(data)
        report = inspect_scene(data)
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report["export_warnings"], data["export_warnings"])
        self.assertEqual(len(report["checks"]), 5)
        self.assertEqual(report["checks"][0]["status"], "pass")
        report["export_warnings"].append("report-local modification")
        self.assertEqual(data, original)

    def test_definite_failure_precedes_export_warning_but_retains_it(self):
        data = scene()
        data["objects"][0]["base_y"] = 2
        data["export_warnings"] = ["missing one", "missing two"]
        report = inspect_scene(data)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertEqual(report["summary"]["warning_count"], 2)
        self.assertEqual(report["summary"]["error_count"], 1)
        self.assertEqual(report["export_warnings"], data["export_warnings"])

    def test_semantic_and_export_warnings_both_count(self):
        data = scene()
        del data["objects"][0]["support_y"]
        data["export_warnings"] = ["unreadable neighbor"]
        report = inspect_scene(data)
        self.assertEqual(report["summary"]["warning_count"], 2)

    def test_absent_and_empty_export_warnings_preserve_existing_pass(self):
        for present in (False, True):
            with self.subTest(present=present):
                data = scene()
                if present:
                    data["export_warnings"] = []
                report = inspect_scene(data)
                self.assertEqual(report["summary"]["status"], "pass")
                self.assertEqual(report["summary"]["warning_count"], 0)
                self.assertEqual(report.get("export_warnings", []), [])

    def test_malformed_explicit_export_warnings_rejected(self):
        for value in (None, False, "missing object", {}, [None], [7], [""], ["  "]):
            with self.subTest(value=value):
                data = scene()
                data["export_warnings"] = value
                with self.assertRaisesRegex(ValueError, "scene.export_warnings"):
                    inspect_scene(data)

    def test_export_warning_is_visible_and_escaped_in_both_human_reports(self):
        data = scene()
        warning = '<script>alert(1)</script> /Island/Skipped | [x](https://bad.invalid)'
        data["export_warnings"] = [warning]
        report = inspect_scene(data)
        html = render_html(report)
        markdown = render_markdown(report)
        self.assertIn("/Island/Skipped", html)
        self.assertIn("/Island/Skipped", markdown)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("[x](https://bad.invalid)", markdown)
        self.assertIn(r"\|", markdown)

    def test_cli_keeps_warning_in_bundle_and_exits_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / "scene.json", base / "report"
            data = scene()
            data["export_warnings"] = ["/Island/Skipped: bad metadata"]
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "worldqa", "inspect",
                                     str(source), "--output", str(output)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["export_warnings"], data["export_warnings"])
            self.assertIn("/Island/Skipped", (output / "report.html").read_text())
            self.assertIn("/Island/Skipped", (output / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
