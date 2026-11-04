"""Independent regression probes for the World Workshop handoff boundary."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from worldqa.engine import inspect_scene
from worldqa.report import render_html, render_markdown


ROOT = Path(os.environ.get("WQA_REVIEW_ROOT", Path(__file__).resolve().parents[1]))


def measured_station():
    return {
        "schema_version": "worldqa.scene.v1",
        "scene_id": "review-station",
        "evidence_kind": "engine_export",
        "units": "meters",
        "coordinate_system": "RH_Y_UP",
        "objects": [{"id": "station", "role": "building", "position": [0, 12, 0],
                     "base_y": 12, "support_y": 12}],
        "track_links": [], "routes": [],
    }


def cli_run(manifest, folder):
    folder = Path(folder)
    source = folder / "input.json"
    source.write_text(json.dumps(manifest), encoding="utf-8")
    output = folder / "result"
    completed = subprocess.run(
        [sys.executable, "-m", "worldqa", "inspect", str(source),
         "--output", str(output)], cwd=ROOT, capture_output=True, text=True,
        check=False,
    )
    return completed, source, output


class WorkshopIndependentReview(unittest.TestCase):
    def test_skipped_exported_object_cannot_disappear_behind_good_station(self):
        scene = measured_station()
        warning = "/root/Island/BrokenPlatform: qainfo is not a Dictionary"
        scene["export_warnings"] = [warning]
        report = inspect_scene(scene)
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report.get("export_warnings"), [warning])

    def test_definite_geometry_failure_does_not_get_downgraded_by_missing_export(self):
        scene = measured_station()
        scene["objects"][0]["base_y"] = 14
        scene["export_warnings"] = ["MissingCarriage: no declared role"]
        report = inspect_scene(scene)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertGreater(report["summary"]["error_count"], 0)
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report.get("export_warnings"), scene["export_warnings"])

    def test_explicit_but_malformed_export_evidence_is_not_ignored(self):
        for value in (None, False, 0, "", "warning", {}, [None], [0], [" "], [[]]):
            with self.subTest(value=value):
                scene = measured_station()
                scene["export_warnings"] = value
                with self.assertRaises(ValueError):
                    inspect_scene(scene)

    def test_legacy_absence_and_explicit_empty_warning_list_remain_valid(self):
        scene = measured_station()
        self.assertEqual(inspect_scene(scene)["summary"]["status"], "pass")
        scene["export_warnings"] = []
        report = inspect_scene(scene)
        self.assertEqual(report["summary"]["status"], "pass")
        self.assertEqual(report["summary"]["warning_count"], 0)

    def test_cli_retains_missing_export_in_all_three_report_formats(self):
        scene = measured_station()
        warning = "LostStation: invalid export annotation"
        scene["export_warnings"] = [warning]
        with tempfile.TemporaryDirectory() as tmp:
            run, source, output = cli_run(scene, tmp)
            self.assertEqual(run.returncode, 3, run.stderr)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report.get("export_warnings"), [warning])
            self.assertEqual(report["provenance"]["manifest_sha256"],
                             hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual((output / "manifest.input.json").read_bytes(), source.read_bytes())
            self.assertIn(warning, (output / "report.md").read_text())
            self.assertIn(warning, (output / "report.html").read_text())

    def test_enormous_integer_difference_returns_cli_invalid_not_traceback(self):
        for sign in (1, -1):
            with self.subTest(sign=sign), tempfile.TemporaryDirectory() as tmp:
                scene = measured_station()
                scene["objects"][0].update(base_y=sign * 10**308,
                                            support_y=-sign * 10**308)
                run, _, output = cli_run(scene, tmp)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertIn("station", run.stderr)
                self.assertFalse(output.exists())

    def test_representable_large_integer_with_zero_difference_is_still_accepted(self):
        scene = measured_station()
        scene["objects"][0].update(base_y=10**308, support_y=10**308)
        self.assertEqual(inspect_scene(scene)["summary"]["status"], "pass")

    def test_export_diagnostics_are_inert_text_in_human_reports(self):
        scene = measured_station()
        scene["export_warnings"] = [
            '<img src=x onerror=alert(1)> [repair](https://unsafe.invalid)'
        ]
        report = inspect_scene(scene)
        html = render_html(report)
        markdown = render_markdown(report)
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("[repair](https://unsafe.invalid)", markdown)
        self.assertIn("onerror", markdown)

    def test_output_diagnostics_are_detached_from_caller_owned_input(self):
        scene = measured_station()
        scene["export_warnings"] = ["UnexportedFence"]
        original = deepcopy(scene)
        report = inspect_scene(scene)
        self.assertEqual(scene, original)
        self.assertIn("export_warnings", report)
        report["export_warnings"].append("human note")
        self.assertEqual(scene, original)

    def test_export_diagnostic_survives_when_every_object_was_skipped(self):
        scene = measured_station()
        scene["objects"] = []
        scene["export_warnings"] = ["Every object failed export"]
        report = inspect_scene(scene)
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertEqual(report["summary"]["checked"], 0)
        self.assertEqual(report["summary"]["warning_count"], 1)
        self.assertEqual(report.get("export_warnings"), scene["export_warnings"])


if __name__ == "__main__":
    unittest.main()
