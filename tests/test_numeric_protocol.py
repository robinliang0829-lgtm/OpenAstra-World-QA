"""Derived numeric overflow is a validation error, including integer input."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from worldqa.engine import inspect_scene


ROOT = Path(__file__).resolve().parents[1]


def scene(objects):
    return {
        "schema_version": "worldqa.scene.v1", "scene_id": "numeric-range",
        "evidence_kind": "synthetic", "units": "meters",
        "coordinate_system": "RH_Y_UP", "track_links": [], "routes": [],
        "objects": objects,
    }


def station(base, support):
    return {"id": "station", "role": "building", "position": [0, 0, 0],
            "base_y": base, "support_y": support}


class NumericProtocolTests(unittest.TestCase):
    def test_individually_finite_ints_with_overflowing_difference_are_invalid(self):
        for sign in (-1, 1):
            with self.subTest(sign=sign):
                with self.assertRaisesRegex(ValueError, "station.*computed geometry"):
                    inspect_scene(scene([station(sign * 10**308, -sign * 10**308)]))

    def test_large_finite_integer_difference_remains_valid(self):
        report = inspect_scene(scene([station(10**308, 10**308)]))
        self.assertEqual(report["summary"]["status"], "pass")

    def test_distance_overflow_uses_same_validation_protocol(self):
        lamps = [{"id": f"lamp-{i}", "role": "lamp", "spacing_group": "street",
                  "position": [x, 0, 0]} for i, x in enumerate((10**308, -10**308))]
        with self.assertRaisesRegex(ValueError, "spacing group street.*computed geometry"):
            inspect_scene(scene(lamps))

    def test_ratio_overflow_uses_same_validation_protocol(self):
        vehicles = [{"id": role, "role": role, "position": [0, 0, 0],
                     "consist_id": "train", "forward": [0, 0, 1],
                     "expected_forward": [0, 0, 1], "body_width": width,
                     "body_height": 3}
                    for role, width in (("train_head", 1e-308), ("train_car", 10**308))]
        with self.assertRaisesRegex(ValueError, "consist train body_width.*computed geometry"):
            inspect_scene(scene(vehicles))

    def test_cli_integer_overflow_exits_two_without_traceback_or_partial_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / "scene.json", base / "report"
            source.write_text(json.dumps(scene([station(10**308, -(10**308))])),
                              encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "worldqa", "inspect",
                                     str(source), "--output", str(output)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("station", result.stderr)
            self.assertIn("computed geometry", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
