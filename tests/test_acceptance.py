"""Independent acceptance examples; all fixtures are synthetic, not island evidence."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from worldqa.engine import inspect_scene


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CHECKS = {"grounding", "track_joints", "spacing", "train_consistency", "route_trace"}


def fixture(name="good.json"):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def indexed(report):
    return {check["id"]: check for check in report["checks"]}


class SyntheticAcceptanceTests(unittest.TestCase):
    def test_good_scene_covers_all_five_declared_checks(self):
        report = inspect_scene(fixture())
        self.assertEqual("synthetic", report["evidence_kind"])
        self.assertEqual("pass", report["summary"]["status"])
        self.assertEqual(CHECKS, set(indexed(report)))
        for check in report["checks"]:
            self.assertEqual("pass", check["status"], check)
            self.assertGreater(check["checked"], 0)

    def test_deliberately_damaged_scene_flags_every_category(self):
        report = inspect_scene(fixture("five_faults.json"))
        self.assertEqual("fail", report["summary"]["status"])
        for check in report["checks"]:
            self.assertEqual("fail", check["status"], check)
            self.assertTrue(check["findings"], check)
            self.assertTrue(any(f["severity"] == "error" for f in check["findings"]))

    def test_missing_evidence_cannot_be_a_green_scene(self):
        report = inspect_scene(fixture("missing_evidence.json"))
        self.assertEqual("blocked", report["summary"]["status"])
        for check in report["checks"]:
            self.assertEqual("blocked", check["status"], check)
            self.assertTrue(any(f["code"] == "MISSING_EVIDENCE" for f in check["findings"]))

    def test_empty_scene_never_means_five_passes(self):
        scene = fixture()
        scene.update(objects=[], track_links=[], routes=[])
        report = inspect_scene(scene)
        self.assertEqual("blocked", report["summary"]["status"])
        self.assertTrue(all(c["status"] == "not_applicable" for c in report["checks"]))

    def test_reverse_route_order_is_failure_even_if_all_points_present(self):
        scene = fixture()
        scene["routes"][0]["trace"].reverse()
        check = indexed(inspect_scene(scene))["route_trace"]
        self.assertEqual("fail", check["status"])

    def test_one_sample_cannot_fulfill_two_waypoints(self):
        scene = fixture()
        scene["routes"][0].update(waypoints=[[0, 12, 0], [0.25, 12, 0]],
                                 trace=[[0, 12, 0]], completed=True)
        self.assertEqual("fail", indexed(inspect_scene(scene))["route_trace"]["status"])

    def test_absent_trace_differs_from_failed_trace(self):
        scene = fixture()
        del scene["routes"][0]["trace"]
        self.assertEqual("blocked", indexed(inspect_scene(scene))["route_trace"]["status"])
        scene["routes"][0]["trace"] = [[0, 12, 0]]
        self.assertEqual("fail", indexed(inspect_scene(scene))["route_trace"]["status"])

    def test_tracks_do_not_gain_connectivity_by_being_near_each_other(self):
        scene = fixture()
        scene["track_links"] = []
        self.assertEqual("blocked", indexed(inspect_scene(scene))["track_joints"]["status"])

    def test_spacing_never_compares_other_roles_or_groups(self):
        scene = fixture()
        scene["objects"][4].update(position=[0, 12, 20], spacing_group="inner-walk")
        # LampA and ColumnA can overlap: one may be mounted on the other.
        scene["objects"][5]["position"] = [0, 12, 20]
        self.assertEqual("pass", indexed(inspect_scene(scene))["spacing"]["status"])

    def test_high_terrace_is_not_a_floating_building(self):
        scene = fixture()
        scene["objects"][0].update(base_y=112.03, support_y=112, position=[0, 112.03, 0])
        self.assertEqual("pass", indexed(inspect_scene(scene))["grounding"]["status"])

    def test_below_support_is_detected_separately(self):
        scene = fixture()
        scene["objects"][0].update(base_y=11.0, position=[0, 11, 0])
        self.assertEqual("fail", indexed(inspect_scene(scene))["grounding"]["status"])

    def test_wheelbase_distance_is_not_body_scale(self):
        scene = fixture()
        scene["objects"][8]["position"] = [-100, 12, 10]
        self.assertEqual("pass", indexed(inspect_scene(scene))["train_consistency"]["status"])

    def test_missing_train_direction_is_not_inferred(self):
        scene = fixture()
        del scene["objects"][7]["expected_forward"]
        self.assertEqual("blocked", indexed(inspect_scene(scene))["train_consistency"]["status"])

    def test_illegal_world_numbers_are_rejected(self):
        for invalid in (float("nan"), float("inf"), True):
            with self.subTest(invalid=invalid):
                scene = fixture()
                scene["objects"][0]["position"][0] = invalid
                with self.assertRaises(ValueError):
                    inspect_scene(scene)

    def test_unknown_track_reference_is_rejected_not_skipped(self):
        scene = fixture()
        scene["track_links"][0]["to"]["object_id"] = "/Missing/Track"
        with self.assertRaises(ValueError):
            inspect_scene(scene)

    def test_unit_and_axis_mismatch_is_rejected(self):
        for key, value in (("units", "centimeters"), ("coordinate_system", "LH_Z_UP")):
            with self.subTest(key=key):
                scene = fixture()
                scene[key] = value
                with self.assertRaises(ValueError):
                    inspect_scene(scene)

    def test_input_is_not_mutated_and_results_are_repeatable(self):
        scene = fixture("five_faults.json")
        before = deepcopy(scene)
        first = inspect_scene(scene)
        self.assertEqual(before, scene)
        self.assertEqual(first, inspect_scene(scene))

    def test_track_gap_at_limit_survives_world_translation(self):
        scene = fixture()
        scene["objects"][1]["endpoints"]["b"] = [100, 12, 10]
        scene["objects"][2]["endpoints"]["a"] = [100.03, 12, 10]
        self.assertEqual("pass", indexed(inspect_scene(scene))["track_joints"]["status"])

    def test_grounding_at_limit_survives_world_translation(self):
        scene = fixture()
        scene["objects"][0].update(base_y=100.15, support_y=100, position=[0, 100.15, 0])
        self.assertEqual("pass", indexed(inspect_scene(scene))["grounding"]["status"])

    def test_train_proportion_at_exact_limit_is_permitted(self):
        scene = fixture()
        scene["objects"][7]["body_width"] = 10
        scene["objects"][8]["body_width"] = 8.5
        self.assertEqual("pass", indexed(inspect_scene(scene))["train_consistency"]["status"])


if __name__ == "__main__":
    unittest.main()
