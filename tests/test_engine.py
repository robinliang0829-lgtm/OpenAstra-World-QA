import copy
import json
import math
import unittest

from worldqa.engine import DEFAULT_CONFIG, inspect_scene


def scene(objects=None, links=None, routes=None):
    return {"schema_version": "worldqa.scene.v1", "scene_id": "unit-scene",
            "evidence_kind": "synthetic", "units": "meters",
            "coordinate_system": "RH_Y_UP", "objects": objects or [],
            "track_links": links or [], "routes": routes or []}


def obj(oid, role, **kwargs):
    return {"id": oid, "role": role, "position": [0, 0, 0], **kwargs}


def check(report, cid):
    return next(item for item in report["checks"] if item["id"] == cid)


def train(oid, role="train_head", **kwargs):
    return obj(oid, role, **{"consist_id": "train-1", "forward": [0, 0, 1],
        "expected_forward": [0, 0, 1], "body_width": 2.0, "body_height": 3.0,
        **kwargs})


def tracks():
    return scene([
        obj("track-A", "track", endpoints={"a": [0, 0, 0], "b": [0, 0, 4]}),
        obj("track-B", "track", endpoints={"a": [0, 0, 4], "b": [0, 0, 8]})
    ], links=[{"id": "joint", "from": {"object_id": "track-A", "endpoint": "b"},
                          "to": {"object_id": "track-B", "endpoint": "a"}}])


def route(**kwargs):
    return {"id": "walk-1", "waypoints": [[0, 0, 0], [0, 0, 2], [0, 0, 4]],
            "trace": [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 4]],
            "trace_kind": "synthetic", "completed": True, **kwargs}


class EngineTests(unittest.TestCase):
    def test_empty_scene_never_passes(self):
        report = inspect_scene(scene())
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertTrue(all(c["status"] == "not_applicable" for c in report["checks"]))

    def test_unknown_role_does_not_become_a_tested_pass(self):
        report = inspect_scene(scene([obj("rock", "decoration")]))
        self.assertEqual(report["summary"]["status"], "blocked")
        self.assertEqual(report["summary"]["checked"], 0)

    def test_grounding_boundaries_and_defects(self):
        data = scene([obj("ok", "building", base_y=0.15, support_y=0),
                      obj("floating", "building", base_y=0.151, support_y=0),
                      obj("embedded", "building", base_y=-0.151, support_y=0)])
        result = check(inspect_scene(data), "grounding")
        self.assertEqual(result["checked"], 3)
        self.assertEqual({f["code"] for f in result["findings"]},
                         {"BUILDING_FLOATING", "BUILDING_EMBEDDED"})

    def test_missing_support_is_blocked(self):
        result = check(inspect_scene(scene([obj("building", "building", base_y=1)])), "grounding")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["checked"], 0)
        self.assertEqual(result["findings"][0]["code"], "MISSING_EVIDENCE")

    def test_failure_precedes_incomplete_evidence(self):
        result = inspect_scene(scene([obj("bad", "building", base_y=2, support_y=0),
                                      obj("unknown", "building")]))
        self.assertEqual(result["summary"]["status"], "fail")
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_track_declared_connection_and_gap(self):
        data = tracks()
        self.assertEqual(check(inspect_scene(data), "track_joints")["status"], "pass")
        data["objects"][1]["endpoints"]["a"][0] = 0.04
        result = check(inspect_scene(data), "track_joints")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["findings"][0]["link_id"], "joint")

    def test_track_no_links_is_blocked(self):
        data = tracks()
        data["track_links"] = []
        self.assertEqual(check(inspect_scene(data), "track_joints")["status"], "blocked")

    def test_track_missing_endpoint_is_blocked(self):
        data = tracks()
        del data["objects"][1]["endpoints"]["a"]
        result = check(inspect_scene(data), "track_joints")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["checked"], 0)

    def test_bad_track_references_and_duplicate_links_are_invalid(self):
        for side in ("from", "to"):
            data = tracks()
            data["track_links"][0][side]["object_id"] = "unknown"
            with self.assertRaisesRegex(ValueError, "unknown object"):
                inspect_scene(data)
        data = tracks()
        link = copy.deepcopy(data["track_links"][0])
        link["id"] = "duplicate"
        link["from"], link["to"] = link["to"], link["from"]
        data["track_links"].append(link)
        with self.assertRaisesRegex(ValueError, "duplicate endpoint connection"):
            inspect_scene(data)

    def test_spacing_respects_role_group_and_boundary(self):
        data = scene([
            obj("lamp-A", "lamp", spacing_group="street", position=[0, 0, 0]),
            obj("lamp-B", "lamp", spacing_group="street", position=[4, 0, 0]),
            obj("lamp-other", "lamp", spacing_group="plaza", position=[0, 0, 0]),
            obj("column-A", "column", spacing_group="street", position=[0, 0, 0]),
        ])
        result = check(inspect_scene(data), "spacing")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["checked"], 1)
        data["objects"][1]["position"][0] = 3.9
        result = check(inspect_scene(data), "spacing")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(len(result["findings"]), 1)

    def test_single_lamp_is_not_spacing_evidence(self):
        result = inspect_scene(scene([obj("one", "lamp", spacing_group="street")]))
        self.assertEqual(check(result, "spacing")["status"], "not_applicable")
        self.assertEqual(result["summary"]["status"], "blocked")

    def test_train_reverse_and_body_scale_are_separate_defects(self):
        data = scene([train("head", forward=[0, 0, -1]),
                      train("car", "train_car", body_width=3)])
        result = check(inspect_scene(data), "train_consistency")
        self.assertEqual({f["code"] for f in result["findings"]},
                         {"TRAIN_WRONG_DIRECTION", "TRAIN_BODY_RATIO"})

    def test_train_direction_vectors_need_not_be_unit(self):
        data = scene([train("head", forward=[0, 0, 1e308], expected_forward=[0, 0, 0.01]),
                      train("car", "train_car")])
        self.assertEqual(check(inspect_scene(data), "train_consistency")["status"], "pass")

    def test_train_missing_or_duplicate_reference_head_blocks(self):
        for objects in ([train("car", "train_car")],
                        [train("a"), train("b"), train("car", "train_car")]):
            with self.subTest(objects=objects):
                result = check(inspect_scene(scene(objects)), "train_consistency")
                self.assertEqual(result["status"], "blocked")

    def test_route_order_and_no_reused_sample(self):
        self.assertEqual(check(inspect_scene(scene(routes=[route()])), "route_trace")["status"], "pass")
        for changed in (
            route(trace=[[0, 0, 4], [0, 0, 2], [0, 0, 0]]),
            route(waypoints=[[0, 0, 0], [0, 0, 0]], trace=[[0, 0, 0]]),
        ):
            result = check(inspect_scene(scene(routes=[changed])), "route_trace")
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["findings"][0]["code"], "ROUTE_WAYPOINT_MISSED")

    def test_route_missing_empty_trace_and_mixed_evidence_block(self):
        for changed in (route(trace=[]), route(waypoints=[])):
            self.assertEqual(check(inspect_scene(scene(routes=[changed])), "route_trace")["status"], "blocked")
        changed = route()
        del changed["trace"]
        self.assertEqual(check(inspect_scene(scene(routes=[changed])), "route_trace")["status"], "blocked")
        data = scene(routes=[route()])
        data["evidence_kind"] = "engine_export"
        self.assertEqual(check(inspect_scene(data), "route_trace")["status"], "blocked")

    def test_route_incomplete_is_failure_even_when_trace_matches(self):
        result = check(inspect_scene(scene(routes=[route(completed=False)])), "route_trace")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["findings"][0]["code"], "ROUTE_INCOMPLETE")

    def test_rejects_nonfinite_bool_zero_direction_and_invalid_config(self):
        for value in (math.nan, math.inf, -math.inf, True, 10**1000):
            data = scene([obj("bad", "building", base_y=value, support_y=0)])
            with self.subTest(value=repr(value)[:40]), self.assertRaises(ValueError):
                inspect_scene(data)
        for fields in ({"forward": [0, 0, 0]}, {"body_width": 0},
                       {"expected_forward": [True, 0, 1]}):
            with self.assertRaises(ValueError):
                inspect_scene(scene([train("bad", **fields)]))
        for config in ({"typo": 1}, {"max_float_m": -1}, {"max_float_m": True},
                       {"max_forward_angle_deg": 181}, {"max_body_ratio_error": 2}):
            with self.assertRaises(ValueError):
                inspect_scene(scene(), config)

    def test_invalid_roots_and_duplicate_ids(self):
        for data in ([], None, {**scene(), "units": "centimeters"},
                     {**scene(), "objects": {}},
                     scene([obj("same", "lamp"), obj("same", "column")])):
            with self.assertRaises(ValueError):
                inspect_scene(data)

    def test_custom_config_determinism_and_inputs_unchanged(self):
        data = scene([obj("b", "building", base_y=0.2, support_y=0),
                      obj("a", "building", base_y=0.1, support_y=0)])
        original = copy.deepcopy(data)
        config = {"max_float_m": 0.3}
        report = inspect_scene(data, config)
        self.assertEqual(report["summary"]["status"], "pass")
        self.assertEqual(data, original)
        self.assertEqual(config, {"max_float_m": 0.3})
        data["objects"].reverse()
        self.assertEqual(report, inspect_scene(data, config))
        self.assertEqual(DEFAULT_CONFIG["max_float_m"], 0.15)
        json.dumps(report, allow_nan=False)

    def test_extreme_computed_geometry_rejected_instead_of_infinity_report(self):
        data = scene([obj("bad", "building", base_y=1e308, support_y=-1e308)])
        with self.assertRaisesRegex(ValueError, "computed geometry"):
            inspect_scene(data)

    def test_submicrometer_real_grounding_and_track_excesses_still_fail(self):
        excess = 1e-7  # 100 times the bounded floating point allowance.
        for base in (100 + 0.15 + excess, 100 - 0.15 - excess):
            result = inspect_scene(scene([obj("base", "building", base_y=base, support_y=100)]))
            self.assertEqual(check(result, "grounding")["status"], "fail")
        data = tracks()
        data["objects"][0]["endpoints"]["b"] = [100, 0, 0]
        data["objects"][1]["endpoints"]["a"] = [100 + 0.03 + excess, 0, 0]
        self.assertEqual(check(inspect_scene(data), "track_joints")["status"], "fail")

    def test_spacing_exact_boundary_and_real_shortfall(self):
        data = scene([obj("a", "lamp", spacing_group="g", position=[100, 0, 0]),
                      obj("b", "lamp", spacing_group="g", position=[100.3, 0, 0])])
        config = {"min_lamp_spacing_m": 0.3}
        self.assertEqual(check(inspect_scene(data, config), "spacing")["status"], "pass")
        data["objects"][1]["position"][0] -= 1e-7
        self.assertEqual(check(inspect_scene(data, config), "spacing")["status"], "fail")

    def test_ratio_exact_boundary_and_real_excess(self):
        data = scene([train("head", body_width=10),
                      train("car", "train_car", body_width=8.5)])
        self.assertEqual(check(inspect_scene(data), "train_consistency")["status"], "pass")
        data["objects"][1]["body_width"] -= 1e-6
        self.assertEqual(check(inspect_scene(data), "train_consistency")["status"], "fail")

    def test_angle_exact_boundary_and_real_excess(self):
        def direction(degrees):
            return [math.sin(math.radians(degrees)), 0, math.cos(math.radians(degrees))]
        data = scene([train("head", forward=direction(15))])
        self.assertEqual(check(inspect_scene(data), "train_consistency")["status"], "pass")
        data["objects"][0]["forward"] = direction(15 + 1e-7)
        self.assertEqual(check(inspect_scene(data), "train_consistency")["status"], "fail")
        data["objects"][0].update(forward=[1, 2, 3], expected_forward=[2, 4, 6])
        self.assertEqual(check(inspect_scene(data, {"max_forward_angle_deg": 0}), "train_consistency")["status"], "pass")

    def test_route_exact_boundary_and_real_excess(self):
        data = scene(routes=[route(waypoints=[[100, 0, 0]], trace=[[100.3, 0, 0]])])
        config = {"route_tolerance_m": 0.3}
        self.assertEqual(check(inspect_scene(data, config), "route_trace")["status"], "pass")
        data["routes"][0]["trace"][0][0] += 1e-7
        self.assertEqual(check(inspect_scene(data, config), "route_trace")["status"], "fail")


if __name__ == "__main__":
    unittest.main()
