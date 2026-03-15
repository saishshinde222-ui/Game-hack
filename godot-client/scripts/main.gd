extends Node3D
## Root scene script — handles text input, routes MCP commands to EntityManager,
## gathers project context and sends to MCP.

@onready var input_field: LineEdit = %InputField
@onready var status_label: Label = %StatusLabel
@onready var entity_root: Node3D = %EntityRoot


func _ready():
	EntityManager.set_scene_root(entity_root)

	input_field.text_submitted.connect(_on_input_submitted)

	CommandServer.command_received.connect(_on_command)
	CommandServer.context_requested.connect(_on_context_requested)
	CommandServer.client_connected.connect(func():
		status_label.text = "MCP connected"
	)
	CommandServer.client_disconnected.connect(func():
		status_label.text = "MCP disconnected — waiting..."
	)


func _on_input_submitted(text: String):
	if text.strip_edges() == "":
		return

	input_field.clear()
	status_label.text = "Sending: %s" % text

	var context = _gather_context()
	CommandServer.send_user_prompt(text, context)


func _on_command(cmd: Dictionary):
	var cmd_type = cmd.get("type", "")

	match cmd_type:
		"spawn_entity":
			var pos = _dict_to_vec3(cmd.get("position", {}))
			var rot = _dict_to_vec3(cmd.get("rotation", {}))
			var scl = _dict_to_vec3(cmd.get("scale", {"x": 1, "y": 1, "z": 1}))
			EntityManager.spawn_entity(
				cmd.get("id", "entity_%d" % randi()),
				cmd.get("model_path", ""),
				pos, rot, scl,
				cmd.get("scripts", [])
			)
			status_label.text = "Spawned: %s" % cmd.get("id", "?")

		"remove_entity":
			EntityManager.remove_entity(cmd.get("id", ""))
			status_label.text = "Removed: %s" % cmd.get("id", "?")

		"attach_behavior":
			EntityManager.attach_behavior(
				cmd.get("entity_id", ""),
				cmd.get("behavior", ""),
				cmd.get("params", {})
			)
			status_label.text = "Behavior attached"

		"detach_behavior":
			EntityManager.detach_behavior(
				cmd.get("entity_id", ""),
				cmd.get("behavior", "")
			)

		"equip_item":
			EntityManager.equip_item(
				cmd.get("holder_id", ""),
				cmd.get("item_id", "")
			)
			status_label.text = "Item equipped"

		"interact":
			EntityManager.interact(
				cmd.get("actor_id", ""),
				cmd.get("target_id", ""),
				cmd.get("action", "")
			)
			status_label.text = "Interaction: %s" % cmd.get("action", "?")

		"add_script":
			_write_script(cmd.get("path", ""), cmd.get("source_code", ""))
			status_label.text = "Script written: %s" % cmd.get("path", "?")

		"status":
			status_label.text = cmd.get("message", "")

		_:
			push_warning("[Main] Unknown command type: %s" % cmd_type)


func _on_context_requested():
	var context = _gather_context()
	CommandServer.send_context(context)


func _gather_context() -> Dictionary:
	var files = _list_files("res://scripts/", [])
	var scripts_content = {}
	for path in files:
		if path.ends_with(".gd"):
			var f = FileAccess.open(path, FileAccess.READ)
			if f:
				scripts_content[path] = f.get_as_text()
				f.close()

	var asset_files = _list_files("res://assets/", [])

	return {
		"script_files": files,
		"script_contents": scripts_content,
		"asset_files": asset_files,
		"entities": EntityManager.get_entity_info(),
	}


func _list_files(path: String, result: Array) -> Array:
	var dir = DirAccess.open(path)
	if dir == null:
		return result

	dir.list_dir_begin()
	var file_name = dir.get_next()
	while file_name != "":
		var full = path.path_join(file_name)
		if dir.current_is_dir():
			if not file_name.begins_with("."):
				_list_files(full, result)
		else:
			result.append(full)
		file_name = dir.get_next()
	dir.list_dir_end()
	return result


func _write_script(path: String, source: String):
	if path == "" or source == "":
		return
	var f = FileAccess.open(path, FileAccess.WRITE)
	if f:
		f.store_string(source)
		f.close()
		print("[Main] Wrote script: %s" % path)


func _dict_to_vec3(d: Dictionary) -> Vector3:
	return Vector3(
		float(d.get("x", 0)),
		float(d.get("y", 0)),
		float(d.get("z", 0))
	)
