"""Deterministic, dependency-free inspections of explicitly annotated scenes.

This module does not load an engine, infer semantic roles, mutate a scene, or
approve a release. A pass is restricted to the evidence declared in the input.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from itertools import combinations
import math


DEFAULT_CONFIG = {
    "max_float_m": 0.15,
    "max_embed_m": 0.15,
    "max_track_gap_m": 0.03,
    "min_lamp_spacing_m": 4.0,
    "min_column_spacing_m": 2.0,
    "max_forward_angle_deg": 15.0,
    "max_body_ratio_error": 0.15,
    "route_tolerance_m": 0.75,
}

# Fixed numerical equality allowance, not a percentage of world coordinates or
# the configured business threshold. For distances this is one nanometer; for
# angles/ratios it is 1e-9 in their declared unit. Measured values stay unchanged.
NUMERIC_ABS_TOL = 1e-9


def _above(value, limit):
    return value > limit and not math.isclose(value, limit, rel_tol=0.0,
                                             abs_tol=NUMERIC_ABS_TOL)


def _below(value, limit):
    return value < limit and not math.isclose(value, limit, rel_tol=0.0,
                                             abs_tol=NUMERIC_ABS_TOL)


def _mapping(value, path):
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def _array(value, path):
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected an array")
    return value


def _text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: expected a non-empty string")
    return value


def _number(value, path, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: expected a finite number, not a boolean")
    try:
        valid = math.isfinite(value)
    except (OverflowError, TypeError):
        valid = False
    if not valid:
        raise ValueError(f"{path}: expected a finite representable number")
    if positive and value <= 0:
        raise ValueError(f"{path}: expected a positive number")
    return value


def _vector(value, path, *, nonzero=False):
    _array(value, path)
    if len(value) != 3:
        raise ValueError(f"{path}: expected exactly three coordinates")
    for i, coordinate in enumerate(value):
        _number(coordinate, f"{path}[{i}]")
    if nonzero and not any(value):
        raise ValueError(f"{path}: a direction vector cannot be zero")
    return value


def _required(obj, field, path):
    if field not in obj:
        raise ValueError(f"{path}.{field}: required field is missing")
    return obj[field]


def _config(config):
    result = DEFAULT_CONFIG.copy()
    if config is None:
        return result
    _mapping(config, "config")
    for key, value in config.items():
        if key not in result:
            raise ValueError(f"config.{key}: unknown setting")
        _number(value, f"config.{key}")
        if value < 0:
            raise ValueError(f"config.{key}: expected a non-negative value")
        if key == "max_forward_angle_deg" and value > 180:
            raise ValueError(f"config.{key}: cannot exceed 180 degrees")
        if key == "max_body_ratio_error" and value > 1:
            raise ValueError(f"config.{key}: cannot exceed 1")
        result[key] = float(value)
    return result


def _validate(scene):
    _mapping(scene, "scene")
    for key, expected in (("schema_version", "worldqa.scene.v1"),
                          ("units", "meters"),
                          ("coordinate_system", "RH_Y_UP")):
        if scene.get(key) != expected:
            raise ValueError(f"scene.{key}: expected {expected!r}")
    _text(_required(scene, "scene_id", "scene"), "scene.scene_id")
    if scene.get("evidence_kind") not in ("synthetic", "engine_export"):
        raise ValueError("scene.evidence_kind: expected synthetic or engine_export")
    if "export_warnings" in scene:
        for i, warning in enumerate(_array(scene["export_warnings"],
                                           "scene.export_warnings")):
            _text(warning, f"scene.export_warnings[{i}]")
    if "source" in scene:
        _mapping(scene["source"], "scene.source")
        for key in ("engine", "engine_version", "revision"):
            if key in scene["source"]:
                _text(scene["source"][key], f"scene.source.{key}")

    objects = _array(_required(scene, "objects", "scene"), "scene.objects")
    by_id = {}
    for i, obj in enumerate(objects):
        path = f"scene.objects[{i}]"
        _mapping(obj, path)
        oid = _text(_required(obj, "id", path), f"{path}.id")
        if oid in by_id:
            raise ValueError(f"{path}.id: duplicate object ID {oid!r}")
        by_id[oid] = obj
        role = _text(_required(obj, "role", path), f"{path}.role")
        _vector(_required(obj, "position", path), f"{path}.position")
        if role == "building":
            for key in ("base_y", "support_y"):
                if key in obj:
                    _number(obj[key], f"{path}.{key}")
            if "support_id" in obj:
                _text(obj["support_id"], f"{path}.support_id")
        if role == "track" and "endpoints" in obj:
            _mapping(obj["endpoints"], f"{path}.endpoints")
            for key, point in obj["endpoints"].items():
                if key not in ("a", "b"):
                    raise ValueError(f"{path}.endpoints.{key}: expected a or b")
                _vector(point, f"{path}.endpoints.{key}")
        if role in ("lamp", "column") and "spacing_group" in obj:
            _text(obj["spacing_group"], f"{path}.spacing_group")
        if role in ("train_head", "train_car"):
            if "consist_id" in obj:
                _text(obj["consist_id"], f"{path}.consist_id")
            for key in ("forward", "expected_forward"):
                if key in obj:
                    _vector(obj[key], f"{path}.{key}", nonzero=True)
            for key in ("body_width", "body_height"):
                if key in obj:
                    _number(obj[key], f"{path}.{key}", positive=True)

    links = _array(_required(scene, "track_links", "scene"), "scene.track_links")
    ids = set()
    pairs = set()
    for i, link in enumerate(links):
        path = f"scene.track_links[{i}]"
        _mapping(link, path)
        lid = _text(_required(link, "id", path), f"{path}.id")
        if lid in ids:
            raise ValueError(f"{path}.id: duplicate link ID {lid!r}")
        ids.add(lid)
        points = []
        for side in ("from", "to"):
            ref = _mapping(_required(link, side, path), f"{path}.{side}")
            oid = _text(_required(ref, "object_id", f"{path}.{side}"),
                        f"{path}.{side}.object_id")
            endpoint = _required(ref, "endpoint", f"{path}.{side}")
            if endpoint not in ("a", "b"):
                raise ValueError(f"{path}.{side}.endpoint: expected a or b")
            if oid not in by_id:
                raise ValueError(f"{path}.{side}.object_id: unknown object {oid!r}")
            if by_id[oid]["role"] != "track":
                raise ValueError(f"{path}.{side}.object_id: object is not a track")
            points.append((oid, endpoint))
        if points[0] == points[1]:
            raise ValueError(f"{path}: cannot join an endpoint to itself")
        pair = tuple(sorted(points))
        if pair in pairs:
            raise ValueError(f"{path}: duplicate endpoint connection")
        pairs.add(pair)

    routes = _array(_required(scene, "routes", "scene"), "scene.routes")
    ids = set()
    for i, route in enumerate(routes):
        path = f"scene.routes[{i}]"
        _mapping(route, path)
        rid = _text(_required(route, "id", path), f"{path}.id")
        if rid in ids:
            raise ValueError(f"{path}.id: duplicate route ID {rid!r}")
        ids.add(rid)
        for key in ("waypoints", "trace"):
            if key in route:
                for j, point in enumerate(_array(route[key], f"{path}.{key}")):
                    _vector(point, f"{path}.{key}[{j}]")
        if "trace_kind" in route and route["trace_kind"] not in ("synthetic", "physics"):
            raise ValueError(f"{path}.trace_kind: expected synthetic or physics")
        if "completed" in route and not isinstance(route["completed"], bool):
            raise ValueError(f"{path}.completed: expected a boolean")
    return by_id


def _finite_result(value, path):
    # Python integer arithmetic itself is unbounded. Two individually
    # representable inputs can produce a difference that math.isfinite cannot
    # convert to a float, so that conversion must use the validation protocol too.
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{path}: computed geometry exceeds finite numeric range")
    return value


def _distance(a, b, path):
    return _finite_result(math.dist(a, b), path)


def _finding(code, ids, message, *, position=None, measured=None, limit=None,
             severity="error"):
    result = {"code": code, "severity": severity, "object_ids": list(ids),
              "message": message}
    if position is not None:
        result["position"] = list(position)
    if measured is not None:
        result["measured"] = measured
    if limit is not None:
        result["limit"] = limit
    return result


def _missing(obj, names, *, label=None):
    return _finding("MISSING_EVIDENCE", [obj["id"]],
                    f"{label or obj['id']}: missing {', '.join(names)}; not checked.",
                    position=obj.get("position"), severity="warning")


def _finish(check_id, checked, findings):
    if any(f["severity"] == "error" for f in findings):
        status = "fail"
    elif findings:
        status = "blocked"
    elif checked:
        status = "pass"
    else:
        status = "not_applicable"
    return {"id": check_id, "status": status, "checked": checked, "findings": findings}


def _grounding(objects, config):
    findings, checked = [], 0
    for obj in objects:
        if obj["role"] != "building":
            continue
        missing = [key for key in ("base_y", "support_y") if key not in obj]
        if missing:
            findings.append(_missing(obj, missing))
            continue
        checked += 1
        gap = _finite_result(obj["base_y"] - obj["support_y"],
                             f"{obj['id']}.base_y - {obj['id']}.support_y")
        if _above(gap, config["max_float_m"]):
            findings.append(_finding("BUILDING_FLOATING", [obj["id"]],
                            "Building base is above its declared measured support.",
                            position=obj["position"], measured=gap,
                            limit=config["max_float_m"]))
        elif _below(gap, -config["max_embed_m"]):
            findings.append(_finding("BUILDING_EMBEDDED", [obj["id"]],
                            "Building base is below its declared measured support.",
                            position=obj["position"], measured=-gap,
                            limit=config["max_embed_m"]))
    return _finish("grounding", checked, findings)


def _tracks(objects, by_id, links, config):
    findings, checked, linked = [], 0, set()
    for obj in objects:
        if obj["role"] == "track":
            missing = [f"endpoints.{key}" for key in ("a", "b")
                       if key not in obj.get("endpoints", {})]
            if missing:
                findings.append(_missing(obj, missing))
    for link in sorted(links, key=lambda item: item["id"]):
        refs = [link["from"], link["to"]]
        linked.update(ref["object_id"] for ref in refs)
        objs = [by_id[ref["object_id"]] for ref in refs]
        if any(ref["endpoint"] not in obj.get("endpoints", {})
               for ref, obj in zip(refs, objs)):
            continue
        a, b = [obj["endpoints"][ref["endpoint"]] for ref, obj in zip(refs, objs)]
        checked += 1
        gap = _distance(a, b, f"track link {link['id']}")
        if _above(gap, config["max_track_gap_m"]):
            finding = _finding("TRACK_GAP", [obj["id"] for obj in objs],
                               f"Declared track connection {link['id']} exceeds the gap limit.",
                               position=a, measured=gap, limit=config["max_track_gap_m"])
            finding["link_id"] = link["id"]
            findings.append(finding)
    for obj in objects:
        if obj["role"] == "track" and obj["id"] not in linked:
            findings.append(_missing(obj, ["declared track connection"],
                                     label="Track connection coverage"))
    return _finish("track_joints", checked, findings)


def _spacing(objects, config):
    findings, checked = [], 0
    groups = defaultdict(list)
    for obj in objects:
        if obj["role"] not in ("lamp", "column"):
            continue
        if "spacing_group" not in obj:
            findings.append(_missing(obj, ["spacing_group"]))
            continue
        groups[(obj["role"], obj["spacing_group"])].append(obj)
    for (role, group), members in sorted(groups.items()):
        limit = config[f"min_{role}_spacing_m"]
        for a, b in combinations(members, 2):
            checked += 1
            distance = _distance(a["position"], b["position"], f"spacing group {group}")
            if _below(distance, limit):
                findings.append(_finding("OBJECTS_TOO_CLOSE", [a["id"], b["id"]],
                                f"{role} objects in spacing group {group!r} are too close.",
                                position=a["position"], measured=distance, limit=limit))
    return _finish("spacing", checked, findings)


def _unit(vector):
    scale = max(abs(x) for x in vector)
    scaled = [x / scale for x in vector]
    magnitude = math.sqrt(sum(x*x for x in scaled))
    return [x / magnitude for x in scaled]


def _angle(a, b):
    # atan2(cross, dot) remains stable near zero; acos(dot) amplifies rounding
    # into spurious non-zero angles for nominally parallel vectors.
    u, v = _unit(a), _unit(b)
    dot = math.fsum(x*y for x, y in zip(u, v))
    cross = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2],
             u[0]*v[1] - u[1]*v[0]]
    return math.degrees(math.atan2(math.hypot(*cross), dot))


def _trains(objects, config):
    findings, checked = [], 0
    groups = defaultdict(list)
    for obj in objects:
        if obj["role"] not in ("train_head", "train_car"):
            continue
        missing = [key for key in ("consist_id", "forward", "expected_forward",
                                  "body_width", "body_height") if key not in obj]
        if missing:
            findings.append(_missing(obj, missing))
        if "consist_id" in obj:
            groups[obj["consist_id"]].append(obj)
        if "forward" in obj and "expected_forward" in obj:
            checked += 1
            angle = _angle(obj["forward"], obj["expected_forward"])
            if _above(angle, config["max_forward_angle_deg"]):
                findings.append(_finding("TRAIN_WRONG_DIRECTION", [obj["id"]],
                                "Vehicle forward direction differs from the declared travel direction.",
                                position=obj["position"], measured=angle,
                                limit=config["max_forward_angle_deg"]))
    for consist, members in sorted(groups.items()):
        heads = [obj for obj in members if obj["role"] == "train_head"]
        cars = [obj for obj in members if obj["role"] == "train_car"]
        if len(heads) != 1:
            findings.append(_finding("MISSING_EVIDENCE", [obj["id"] for obj in members],
                            f"Consist {consist!r} needs exactly one reference head for body comparison; found {len(heads)}.",
                            severity="warning"))
            continue
        head = heads[0]
        for car in cars:
            for dimension in ("body_width", "body_height"):
                if dimension not in head or dimension not in car:
                    continue
                checked += 1
                error = _finite_result(abs(car[dimension] / head[dimension] - 1),
                                       f"consist {consist} {dimension}")
                if _above(error, config["max_body_ratio_error"]):
                    finding = _finding("TRAIN_BODY_RATIO", [head["id"], car["id"]],
                                       f"Car {dimension} differs from the reference head body.",
                                       position=car["position"], measured=error,
                                       limit=config["max_body_ratio_error"])
                    finding["dimension"] = dimension
                    findings.append(finding)
    return _finish("train_consistency", checked, findings)


def _routes(routes, config, evidence_kind):
    findings, checked = [], 0
    for route in sorted(routes, key=lambda item: item["id"]):
        missing = [key for key in ("waypoints", "trace", "trace_kind", "completed")
                   if key not in route]
        missing.extend(key for key in ("waypoints", "trace")
                       if key in route and not route[key])
        if route.get("completed") is False:
            findings.append(_finding("ROUTE_INCOMPLETE", [route["id"]],
                            "The recorded route explicitly reports incomplete execution."))
        if missing:
            findings.append(_missing(route, missing, label=f"Route {route['id']}"))
            continue
        if evidence_kind == "engine_export" and route["trace_kind"] != "physics":
            findings.append(_missing(route, ["physical route trace"],
                                     label=f"Route {route['id']} contains only synthetic trace"))
            continue
        checked += 1
        cursor = 0
        for waypoint_index, waypoint in enumerate(route["waypoints"]):
            found = False
            while cursor < len(route["trace"]):
                point = route["trace"][cursor]
                cursor += 1
                if not _above(_distance(point, waypoint, f"route {route['id']}"),
                              config["route_tolerance_m"]):
                    found = True
                    break
            if not found:
                finding = _finding("ROUTE_WAYPOINT_MISSED", [route["id"]],
                                   f"Waypoint {waypoint_index} is not reached by successive trace samples in the declared order.",
                                   position=waypoint, limit=config["route_tolerance_m"])
                finding["waypoint_index"] = waypoint_index
                findings.append(finding)
                break
    result = _finish("route_trace", checked, findings)
    result["scope"] = "Ordered sampled waypoint coverage only; not collision, clearance, or gameplay verification."
    return result


def inspect_scene(scene: dict, config: dict | None = None) -> dict:
    """Validate and inspect a scene manifest without mutation or external access.

    Raises ValueError for malformed data. Missing semantic evidence instead yields
    a blocked check. Definite defects take precedence over blocked coverage.
    """
    config = _config(config)
    by_id = _validate(scene)
    objects = sorted(scene["objects"], key=lambda item: item["id"])
    checks = [
        _grounding(objects, config),
        _tracks(objects, by_id, scene["track_links"], config),
        _spacing(objects, config),
        _trains(objects, config),
        _routes(scene["routes"], config, scene["evidence_kind"]),
    ]
    counts = {status: sum(check["status"] == status for check in checks)
              for status in ("pass", "fail", "blocked", "not_applicable")}
    export_warnings = scene.get("export_warnings", [])
    status = ("fail" if counts["fail"] else "blocked" if counts["blocked"]
              or export_warnings or not counts["pass"] else "pass")
    result = {
        "schema_version": "worldqa.report.v1",
        "scene_id": scene["scene_id"],
        "evidence_kind": scene["evidence_kind"],
        "config": config,
        "numeric_comparison": {"absolute_tolerance": NUMERIC_ABS_TOL,
                               "relative_tolerance": 0.0,
                               "units": "Each measurement's declared unit; no coordinate-scale allowance."},
        "checks": checks,
        "summary": {"status": status, "check_counts": counts,
                    "checked": sum(check["checked"] for check in checks),
                    "error_count": sum(f["severity"] == "error" for c in checks for f in c["findings"]),
                    "warning_count": len(export_warnings) + sum(
                        f["severity"] == "warning" for c in checks for f in c["findings"])},
        "limitations": [
            "Demo thresholds require calibration by the island owner; they are not approved production specifications.",
            "Only declared objects, roles, connections and sampled evidence are inspected; unannotated content is outside coverage.",
            "Synthetic data cannot establish the quality of the actual island.",
            "Engine exports do not establish camera, GPU performance, physics correctness or gameplay acceptance.",
            "A pass is limited to applicable declared checks and is never release approval.",
        ],
    }
    if "source" in scene:
        result["source"] = deepcopy(scene["source"])
    if "export_warnings" in scene:
        result["export_warnings"] = deepcopy(export_warnings)
    return result
