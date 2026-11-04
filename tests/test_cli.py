"""CLI boundaries and report rendering; run with unittest discovery."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from worldqa.report import render_html, render_markdown


ROOT = Path(__file__).resolve().parents[1]


def scene():
    return {
        "schema_version": "worldqa.scene.v1", "scene_id": "cli-fixture",
        "evidence_kind": "synthetic", "units": "meters",
        "coordinate_system": "RH_Y_UP", "track_links": [], "routes": [],
        "objects": [{"id": "building-1", "role": "building", "position": [0, 0, 0],
                     "base_y": 0, "support_y": 0}],
    }


class ReportTests(unittest.TestCase):
    def test_manifest_strings_cannot_insert_markup(self):
        attack = '<script>alert(1)</script><img src=x onerror=alert(2)>|[click](https://bad.invalid)'
        report = {
            "scene_id": attack, "evidence_kind": "synthetic", "config": {},
            "summary": {"status": "fail"},
            "checks": [{"id": "grounding", "status": "fail", "checked": 1,
                        "findings": [{"code": attack, "severity": "error",
                                      "object_ids": [attack], "message": attack}]}],
        }
        html = render_html(report)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("default-src 'none'", html)
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
        parser = Tags()
        parser.feed(html)
        self.assertNotIn("script", parser.tags)
        self.assertNotIn("img", parser.tags)
        markdown = render_markdown(report)
        self.assertNotIn("[click](https://bad.invalid)", markdown)
        self.assertIn(r"\|", markdown)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "scene.json"

    def put(self, value):
        self.input.write_text(json.dumps(value), encoding="utf-8")

    def run_cli(self, *extra):
        return subprocess.run([sys.executable, "-m", "worldqa", "inspect",
                               str(self.input), *map(str, extra)], cwd=ROOT,
                              text=True, capture_output=True, check=False)

    def test_pass_writes_reproducible_complete_bundle(self):
        self.put(scene())
        raw = self.input.read_bytes()
        out = self.root / "report"
        result = self.run_cli("--output", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(raw, self.input.read_bytes())
        self.assertEqual(raw, (out / "manifest.input.json").read_bytes())
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["provenance"]["manifest_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report["evidence_kind"], "synthetic")
        self.assertEqual(report["summary"]["status"], "pass")
        self.assertTrue((out / "report.html").is_file())
        self.assertTrue((out / "report.md").is_file())
        again = self.root / "again"
        result = self.run_cli("--output", again)
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in out.iterdir():
            self.assertEqual(path.read_bytes(), (again / path.name).read_bytes())

    def test_failure_and_missing_evidence_have_distinct_exit_codes(self):
        floating = scene()
        floating["objects"][0]["base_y"] = 5
        self.put(floating)
        self.assertEqual(self.run_cli("--output", self.root / "fail").returncode, 1)
        incomplete = scene()
        del incomplete["objects"][0]["support_y"]
        self.put(incomplete)
        result = self.run_cli("--output", self.root / "blocked")
        self.assertEqual(result.returncode, 3, result.stderr)

    def test_invalid_json_never_creates_evidence_directory(self):
        for i, raw in enumerate(['{"bad":', '{"x":NaN}', '{"x":1,"x":2}', '[]']):
            with self.subTest(raw=raw):
                self.input.write_text(raw, encoding="utf-8")
                output = self.root / f"invalid-{i}"
                result = self.run_cli("--output", output)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(output.exists())
                self.assertNotIn("Traceback", result.stderr)

    def test_structurally_wrong_input_returns_invalid(self):
        wrong = scene()
        wrong["objects"] = "not an array"
        self.put(wrong)
        result = self.run_cli("--output", self.root / "out")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_no_overwrite_of_input_or_existing_directory(self):
        self.put(scene())
        raw = self.input.read_bytes()
        result = self.run_cli("--output", self.input)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.input.read_bytes(), raw)
        output = self.root / "existing"
        output.mkdir()
        marker = output / "report.json"
        marker.write_text("KEEP", encoding="utf-8")
        result = self.run_cli("--output", output)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(marker.read_text(), "KEEP")
        self.assertEqual(list(output.iterdir()), [marker])

    def test_config_raw_bytes_and_effective_thresholds_are_retained(self):
        self.put(scene())
        config = self.root / "config.json"
        config.write_text('{ "max_float_m": 0.2 }\n', encoding="utf-8")
        out = self.root / "custom"
        result = self.run_cli("--config", config, "--output", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((out / "config.input.json").read_bytes(), config.read_bytes())
        effective = json.loads((out / "config.effective.json").read_text())
        self.assertEqual(effective["max_float_m"], 0.2)
        self.assertIn("max_track_gap_m", effective)

    def test_unknown_flags_or_missing_output_are_usage_errors(self):
        self.put(scene())
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--unknown-option").returncode, 2)


if __name__ == "__main__":
    unittest.main()
