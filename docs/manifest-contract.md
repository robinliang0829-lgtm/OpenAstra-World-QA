# World QA manifest contract v1

JSON root: `schema_version: "worldqa.scene.v1"`, `scene_id` non-empty string,
`evidence_kind: "synthetic" | "engine_export"`, `units: "meters"`,
`coordinate_system: "RH_Y_UP"`, `objects: []`, `track_links: []`,
`routes: []`, optional `source: {engine, engine_version, revision}`,
optional `export_warnings: [non-empty string, ...]`.

`export_warnings` is the exporter-to-inspector evidence gap channel. Omission or
an empty array is allowed for compatibility; an explicit null, scalar, object or
empty/non-string entry is invalid input. Non-empty warnings are preserved verbatim
in report JSON and escaped for display in Markdown/HTML; they count toward
`summary.warning_count`. Any export warning makes the overall result at least
`blocked`, even when all applicable object checks pass; a definite defect still
takes precedence as `fail`. The existing five check IDs/counts describe those
checks only: export completeness is not silently converted into a sixth check.
No warning does not prove the exporter included all real scene objects. A future
independent expected-object inventory is still required for full export coverage.

Every object: unique non-empty `id`, `role`, `position: [x,y,z]`.
Recognized roles: `building`, `track`, `lamp`, `column`, `train_head`, `train_car`.
Unknown roles retained and ignored by current checks. Finite numeric coordinates only.

- building: `base_y`, `support_y` world meter heights (support_y from a measured
  support query at annotated support point, not guessed from mesh); optional `support_id`.
- track: `endpoints: {a:[x,y,z], b:[x,y,z]}`. track_links:
  `{id, from:{object_id, endpoint:"a"|"b"}, to:{object_id, endpoint:"a"|"b"}}`.
  Connectivity is explicit; never guess nearest neighbors.
- lamp / column: `spacing_group` string. Only compare same role and spacing_group.
- train_head / train_car: `consist_id`, `forward:[x,y,z]`,
  `expected_forward:[x,y,z]`, `body_width`, `body_height`, all world meters.
  Compare each car width/height to its unique consist head, never its length.
- routes: `{id, waypoints:[[x,y,z],...], trace:[[x,y,z],...],
  trace_kind:"synthetic"|"physics", completed:bool}`. Missing trace means blocked,
  not pass. Ordered waypoint coverage only; this v1 cannot prove clearance,
  collision validity or playable route from a polyline. Each waypoint must be
  within tolerance of a successive trace sample (no sample reuse).

Default config (override via optional separate config JSON):
`max_float_m:0.15`, `max_embed_m:0.15`, `max_track_gap_m:0.03`,
`min_lamp_spacing_m:4.0`, `min_column_spacing_m:2.0`,
`max_forward_angle_deg:15.0`, `max_body_ratio_error:0.15`,
`route_tolerance_m:0.75`. All finite >=0, angle <=180, ratio <=1.
These are demo defaults pending island-owner calibration, NOT approved island specs.
Comparisons use fixed absolute numeric tolerance `1e-9` (relative tolerance zero),
declared separately in reports. Business thresholds are unchanged. This prevents
floating-point subtraction at larger world coordinates from rejecting exact-limit
cases; meaningful over-limit cases remain failures.

Engine API: `worldqa.engine.inspect_scene(scene:dict, config:dict|None=None)->dict`.
It validates and raises `ValueError` with a useful path on invalid structural input.
This includes derived geometry outside the representable finite numeric range,
including a difference of two individually valid large JSON integers; the CLI
returns 2 before creating any output bundle for this case.
Optional missing semantic evidence yields `blocked` check, never silently passes.
Result JSON: `schema_version:"worldqa.report.v1"`, `scene_id`, `evidence_kind`,
`config`, `checks:[{id,status:"pass"|"fail"|"blocked"|"not_applicable", checked:int,
findings:[{code,severity:"error"|"warning",object_ids:[str],message,position?:[x,y,z],
measured?:number,limit?:number}]}]`, `summary:{status:"pass"|"fail"|"blocked",...}`.
Check IDs: `grounding`, `track_joints`, `spacing`, `train_consistency`, `route_trace`.
Overall fail if any fail; otherwise blocked if any blocked, any export warnings,
or no applicable checks;
otherwise pass. Pass always means these declared checks, NOT release approval.
Missing metadata for relevant objects => blocked for that check unless a definite
failure also exists; include warning `MISSING_EVIDENCE`. Missing all role objects
=> not_applicable (never counts as a tested pass).

CLI exit: 0 declared checks pass; 1 definite failure; 2 invalid input; 3 blocked.
No network access or scene mutations. Report must say synthetic data cannot prove
actual island quality. Engine exports don't prove real camera/GPU/gameplay checks.
