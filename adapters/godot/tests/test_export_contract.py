"""Real-engine contract tests; skipped when no Godot binary is available.

Run from any directory:
  WORLDQA_GODOT_BIN=/path/to/godot python adapters/godot/tests/test_export_contract.py -v

Each case runs a copied, isolated synthetic project. It never opens a real island.
These tests are separate from the Python engine's unit tests: a skip is not proof
that GDScript parses or that Godot physics/export behavior works.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ADAPTER = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("WORLDQA_GODOT_BIN") or shutil.which("godot") or shutil.which("godot4")
EXPECTED_ORIGIN = '"expected_forward_origin": "../TrackDirectionStart"'
EXPECTED_TIP = '"expected_forward_tip": "../TrackDirectionEnd"'


@unittest.skipUnless(GODOT, "Godot binary unavailable; target-engine validation remains pending")
class ExportContractTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="worldqa-godot-")
        self.addCleanup(self.workspace.cleanup)
        root = Path(self.workspace.name)
        self.project = root / "project"
        self.project.mkdir()
        self.output = root / "evidence" / "scene.json"
        for filename in ("project.godot", "export_worldqa.gd"):
            shutil.copy2(ADAPTER / filename, self.project / filename)
        self.scene = (ADAPTER / "demo.tscn").read_text(encoding="utf-8")

    def export(self, scene):
        (self.project / "case.tscn").write_text(scene, encoding="utf-8")
        result = subprocess.run(
            [str(GODOT), "--headless", "--path", str(self.project), "--script",
             "res://export_worldqa.gd", "--", "--scene", "res://case.tscn",
             "--output", str(self.output)],
            capture_output=True, text=True, timeout=45, check=False,
        )
        return result, result.stdout + result.stderr

    def assert_refused(self, scene, reason):
        result, log = self.export(scene)
        self.assertEqual(result.returncode, 2, log)
        self.assertIn("WORLDQA_EXPORT_ERROR", log)
        self.assertIn(reason, log)
        self.assertFalse(self.output.exists(), log)

    def test_independent_route_markers_export_original_direction(self):
        result, log = self.export(self.scene)
        self.assertEqual(result.returncode, 0, log)
        manifest = json.loads(self.output.read_text(encoding="utf-8"))
        head = next(item for item in manifest["objects"] if item["id"] == "train-head")
        self.assertEqual(head["forward"], [0, 0, -1])
        self.assertEqual(head["expected_forward"], [0, 0, 1])
        self.assertEqual(manifest["evidence_kind"], "synthetic")
        self.assertIsInstance(manifest["export_warnings"], list)

    def test_malformed_qainfo_does_not_silently_omit_object(self):
        scene = self.scene.replace(
            'metadata/qainfo = {"id": "lamp-02", "role": "lamp", "spacing_group": "east-path"}',
            'metadata/qainfo = "broken metadata"',
        )
        self.assert_refused(scene, "qainfo is not a Dictionary")

    def test_missing_role_is_refused(self):
        scene = self.scene.replace('"id": "lamp-02", "role": "lamp"', '"id": "lamp-02"')
        self.assert_refused(scene, "qainfo.role")

    def test_non_string_role_is_refused(self):
        scene = self.scene.replace('"id": "lamp-02", "role": "lamp"', '"id": "lamp-02", "role": 7')
        self.assert_refused(scene, "qainfo.role")

    def test_unknown_role_is_refused(self):
        scene = self.scene.replace('"id": "lamp-02", "role": "lamp"', '"id": "lamp-02", "role": "lmap"')
        self.assert_refused(scene, "qainfo.role")

    def test_nonspatial_annotation_is_refused(self):
        scene = self.scene.replace(
            '[node name="Lamp02" type="Node3D" parent="."]\nposition = Vector3(7, 0, 1)',
            '[node name="Lamp02" type="Node" parent="."]',
        )
        self.assert_refused(scene, "annotated objects must be Node3D")

    def test_expected_direction_cannot_use_own_vehicle_markers(self):
        scene = self.scene.replace(EXPECTED_ORIGIN, '"expected_forward_origin": "Bottom"', 1)
        scene = scene.replace(EXPECTED_TIP, '"expected_forward_tip": "Nose"', 1)
        self.assert_refused(scene, "expected direction must not alias")

    def test_expected_tip_cannot_live_under_own_vehicle(self):
        # Top is not an actual forward marker, so this tests ancestry separately.
        scene = self.scene.replace(EXPECTED_TIP, '"expected_forward_tip": "Top"', 1)
        self.assert_refused(scene, "outside every vehicle subtree")

    def test_expected_direction_cannot_use_later_carriage(self):
        # TrainCar is serialized after TrainHead: validation must precollect all
        # vehicles, not only reject the current or already-visited vehicle.
        scene = self.scene.replace(EXPECTED_ORIGIN, '"expected_forward_origin": "../TrainCar/Bottom"', 1)
        scene = scene.replace(EXPECTED_TIP, '"expected_forward_tip": "../TrainCar/Nose"', 1)
        self.assert_refused(scene, "outside every vehicle subtree")

    def test_external_markers_cannot_alias_actual_forward(self):
        scene = self.scene.replace('"forward_origin": "Bottom"', '"forward_origin": "../TrackDirectionStart"', 1)
        scene = scene.replace('"forward_tip": "Nose"', '"forward_tip": "../TrackDirectionEnd"', 1)
        self.assert_refused(scene, "expected direction must not alias")


if __name__ == "__main__":
    unittest.main()
