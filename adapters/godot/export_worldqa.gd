extends SceneTree
## Read-only SOURCE export from an explicitly annotated, trusted QA scene copy.
## This is not a sandbox: Godot can execute project autoloads and scene scripts.
## Usage: godot --headless --path <isolated-project> --script <this.gd> -- \
##        --scene res://demo.tscn --output /absolute/outside-project/scene.json

var _scale_m: float = 1.0
var _warnings: Array[String] = []
var _scene: Node
var _records: Array[Dictionary] = []
var _annotation_errors: Array[String] = []
var _vehicles: Array[Node3D] = []

const OBJECT_ROLES = ["building", "track", "lamp", "column", "train_head", "train_car"]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var options: Dictionary = {}
	if args.size() != 4:
		_fail("Expected --scene res://scene.tscn --output /absolute/new-file.json")
		return
	for index in range(0, args.size(), 2):
		if args[index] not in ["--scene", "--output"] or options.has(args[index]):
			_fail("Unknown or repeated option: " + args[index])
			return
		options[args[index]] = args[index + 1]
	if not options.has("--scene") or not options.has("--output"):
		_fail("Both --scene and --output are required")
		return
	var output: String = String(options["--output"]).replace("\\", "/").simplify_path()
	var project_dir: String = ProjectSettings.globalize_path("res://").replace("\\", "/").trim_suffix("/")
	if not output.is_absolute_path() or output.to_lower().begins_with(project_dir.to_lower() + "/"):
		_fail("Output must be an absolute path outside the source project")
		return
	if FileAccess.file_exists(output) or DirAccess.dir_exists_absolute(output):
		_fail("Refusing to replace existing output: " + output)
		return
	var packed: Resource = load(String(options["--scene"]))
	if not packed is PackedScene:
		_fail("Input must load as PackedScene")
		return
	_scene = (packed as PackedScene).instantiate()
	# Prevent processing and _ready handlers after loading. _init/autoload execution
	# is outside this protection: use a reviewed, isolated project, never live state.
	_remove_scripts(_scene)
	root.add_child(_scene)
	var unverified: String = _unverified_dimensions(_scene)
	if not unverified.is_empty():
		_fail("DIMENSIONS_UNVERIFIED at " + unverified + "; calibrate island-baseline and units before metric export")
		return
	# Collect all vehicle roots before walking records: a head can reference a
	# carriage later in the scene tree. Bad explicit annotations are errors, not
	# invisible omissions from an otherwise successful export.
	_validate_annotations(_scene)
	if _fail_annotation_errors():
		return
	await physics_frame
	await physics_frame
	var meta: Dictionary = _info(_scene)
	if not meta.has("meters_per_unit") or not _positive_number(meta["meters_per_unit"]):
		_fail("Root qainfo.meters_per_unit must explicitly be a positive finite number")
		return
	_scale_m = float(meta["meters_per_unit"])
	_walk(_scene)
	if _fail_annotation_errors():
		return
	if _records.is_empty():
		_fail("No annotated objects; an empty scene is not a valid island inspection")
		return
	var manifest: Dictionary = {
		"schema_version": "worldqa.scene.v1",
		"scene_id": String(meta.get("scene_id", _scene.name)),
		"evidence_kind": "synthetic" if meta.get("synthetic", false) == true else "engine_export",
		"units": "meters", "coordinate_system": "RH_Y_UP",
		"objects": _records, "track_links": _links(meta), "routes": _routes(meta),
		"source": {"engine": "Godot", "engine_version": Engine.get_version_info()["string"],
			"revision": String(meta.get("revision", "UNSPECIFIED"))},
		"export_warnings": _warnings
	}
	if DirAccess.make_dir_recursive_absolute(output.get_base_dir()) != OK:
		_fail("Cannot create output directory")
		return
	var file: FileAccess = FileAccess.open(output, FileAccess.WRITE)
	if file == null:
		_fail("Cannot write output, FileAccess error: " + str(FileAccess.get_open_error()))
		return
	file.store_string(JSON.stringify(manifest, "\t") + "\n")
	file.close()
	print("WORLDQA_EXPORTED " + output)
	for warning in _warnings:
		print("WORLDQA_MISSING_EVIDENCE " + warning)
	quit(0)


func _fail(message: String) -> void:
	push_error("WORLDQA_EXPORT_ERROR " + message)
	quit(2)


func _positive_number(value: Variant) -> bool:
	return (typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT) and is_finite(float(value)) and float(value) > 0.0


func _remove_scripts(node: Node) -> void:
	for child in node.get_children():
		_remove_scripts(child)
	node.set_script(null)
	node.set_process(false)
	node.set_physics_process(false)
	# Do not set PROCESS_MODE_DISABLED: CollisionObject3D defaults can remove
	# disabled bodies from the physics space, making every support ray miss.


func _unverified_dimensions(node: Node) -> String:
	# Check the complete inspected hierarchy so a parent flag cannot be hidden by
	# setting meters_per_unit on a child. This overrides all declared meter scales.
	if node.get_meta("DIMENSIONS_UNVERIFIED", false) == true:
		return String(node.get_path())
	for child in node.get_children():
		var found: String = _unverified_dimensions(child)
		if not found.is_empty():
			return found
	return ""


func _info(node: Node) -> Dictionary:
	var value: Variant = node.get_meta("qainfo", {})
	if value is Dictionary:
		return value
	_annotation_errors.append(String(node.get_path()) + ": qainfo is not a Dictionary")
	return {}


func _validate_annotations(node: Node) -> void:
	if node.has_meta("qainfo"):
		var value: Variant = node.get_meta("qainfo")
		if not value is Dictionary:
			_annotation_errors.append(String(node.get_path()) + ": qainfo is not a Dictionary")
		else:
			var meta: Dictionary = value
			# The root's qainfo also holds scene-wide settings and need not have
			# an object role. Every other explicit qainfo declares an object.
			if node != _scene or meta.has("role"):
				var role: Variant = meta.get("role", null)
				if typeof(role) != TYPE_STRING or role not in OBJECT_ROLES:
					_annotation_errors.append(String(node.get_path()) + ": qainfo.role must be a supported non-empty role")
				elif not node is Node3D:
					_annotation_errors.append(String(node.get_path()) + ": annotated objects must be Node3D")
				elif role in ["train_head", "train_car"]:
					_vehicles.append(node as Node3D)
	for child in node.get_children():
		_validate_annotations(child)


func _fail_annotation_errors() -> bool:
	if _annotation_errors.is_empty():
		return false
	_fail("Invalid scene annotations: " + "; ".join(PackedStringArray(_annotation_errors)))
	return true


func _marker(owner: Node, value: Variant) -> Node3D:
	if not (value is String or value is NodePath) or String(value).is_empty():
		return null
	var found: Node = owner.get_node_or_null(NodePath(String(value)))
	return found as Node3D


func _vec(value: Vector3) -> Array:
	return [value.x, value.y, value.z]


func _id(node: Node) -> String:
	return String(_info(node).get("id", node.get_path()))


func _walk(node: Node) -> void:
	var meta: Dictionary = _info(node)
	if node is Node3D and meta.has("role"):
		var spatial: Node3D = node as Node3D
		var record: Dictionary = {"id": _id(node), "role": String(meta["role"]),
			"position": _vec(spatial.global_transform.origin * _scale_m)}
		match record["role"]:
			"building":
				_grounding(spatial, meta, record)
			"track":
				var ends: Dictionary = {}
				for key in ["a", "b"]:
					var marker: Node3D = _marker(node, meta.get("endpoint_" + key, ""))
					if marker != null:
						ends[key] = _vec(marker.global_transform.origin * _scale_m)
				record["endpoints"] = ends
			"lamp", "column":
				if meta.has("spacing_group"):
					record["spacing_group"] = meta["spacing_group"]
			"train_head", "train_car":
				_train(spatial, meta, record)
		_records.append(record)
	for child in node.get_children():
		_walk(child)


func _excluded_bodies(node: Node, results: Array[RID]) -> void:
	if node is CollisionObject3D:
		results.append((node as CollisionObject3D).get_rid())
	for child in node.get_children():
		_excluded_bodies(child, results)


func _grounding(node: Node3D, meta: Dictionary, record: Dictionary) -> void:
	var base: Node3D = _marker(node, meta.get("base_marker", ""))
	var probe: Node3D = _marker(node, meta.get("support_probe", ""))
	if base != null:
		record["base_y"] = base.global_transform.origin.y * _scale_m
	if base == null or probe == null or not meta.has("support_collision_mask"):
		_warnings.append(_id(node) + ": missing base_marker/support_probe/support_collision_mask")
		return
	var up_m: Variant = meta.get("probe_up_m", 2.0)
	var down_m: Variant = meta.get("probe_down_m", 20.0)
	var mask: Variant = meta["support_collision_mask"]
	if not _positive_number(up_m) or not _positive_number(down_m) or typeof(mask) != TYPE_INT or mask <= 0:
		_warnings.append(_id(node) + ": invalid ray probe settings")
		return
	var origin: Vector3 = probe.global_transform.origin
	var exclude: Array[RID] = []
	_excluded_bodies(node, exclude)
	var query: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
		origin + Vector3.UP * float(up_m) / _scale_m,
		origin + Vector3.DOWN * float(down_m) / _scale_m, int(mask), exclude)
	query.collide_with_areas = false
	var hit: Dictionary = node.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		_warnings.append(_id(node) + ": support ray hit nothing; not evidence of supported building")
		return
	var hit_position: Vector3 = hit["position"]
	record["support_y"] = hit_position.y * _scale_m
	if hit["collider"] is Node:
		record["support_id"] = String((hit["collider"] as Node).get_path())


func _train(node: Node3D, meta: Dictionary, record: Dictionary) -> void:
	if meta.has("consist_id"):
		record["consist_id"] = meta["consist_id"]
	var actual_start: Node3D = _marker(node, meta.get("forward_origin", ""))
	var actual_end: Node3D = _marker(node, meta.get("forward_tip", ""))
	for vector_name in ["forward", "expected_forward"]:
		var start: Node3D = _marker(node, meta.get(vector_name + "_origin", ""))
		var end: Node3D = _marker(node, meta.get(vector_name + "_tip", ""))
		if start != null and end != null:
			if vector_name == "expected_forward" and not _expected_direction_is_independent(node, start, end, actual_start, actual_end):
				continue
			var direction: Vector3 = end.global_transform.origin - start.global_transform.origin
			if direction.length_squared() > 0.0:
				record[vector_name] = _vec(direction.normalized())
	for measurement in [["body_width", "body_left", "body_right"], ["body_height", "body_bottom", "body_top"]]:
		var start: Node3D = _marker(node, meta.get(measurement[1], ""))
		var end: Node3D = _marker(node, meta.get(measurement[2], ""))
		if start != null and end != null:
			record[measurement[0]] = start.global_transform.origin.distance_to(end.global_transform.origin) * _scale_m


func _expected_direction_is_independent(owner: Node3D, start: Node3D, end: Node3D, actual_start: Node3D, actual_end: Node3D) -> bool:
	for marker in [start, end]:
		if marker == actual_start or marker == actual_end:
			_annotation_errors.append(_id(owner) + ": expected direction must not alias actual forward markers")
			return false
		for vehicle in _vehicles:
			if marker == vehicle or vehicle.is_ancestor_of(marker):
				_annotation_errors.append(_id(owner) + ": expected direction must be outside every vehicle subtree; found " + String(marker.get_path()))
				return false
	return true


func _links(meta: Dictionary) -> Array:
	# References use explicit exported object IDs, not proximity guesses.
	return meta.get("track_links", [])


func _routes(meta: Dictionary) -> Array:
	var results: Array = []
	for specification in meta.get("routes", []):
		var waypoints: Array = []
		for path in specification.get("waypoint_markers", []):
			var marker: Node3D = _marker(_scene, path)
			if marker != null:
				waypoints.append(_vec(marker.global_transform.origin * _scale_m))
			else:
				_warnings.append("Route " + str(specification.get("id", "")) + ": invalid waypoint marker " + str(path))
				# Preserve the failure as invalid evidence; never silently shorten a route.
				waypoints.append(null)
		# No trace is invented. A separately validated physics recorder is future work.
		results.append({"id": specification.get("id", ""), "waypoints": waypoints})
	return results
