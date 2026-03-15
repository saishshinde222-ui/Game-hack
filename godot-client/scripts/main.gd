extends Node2D
## Root 2D scene script — routes MCP commands, handles text input, gathers context.

@onready var input_field: LineEdit = %InputField
@onready var status_label: Label = %StatusLabel
@onready var entity_root: Node2D = %EntityRoot


func _ready():
	EntityManager.set_scene_root(entity_root)

	var character = entity_root.get_node_or_null("Character")
	if character and character is Sprite2D:
		_setup_placeholder(character)
		var tex_path := ""
		if character.texture and character.texture.resource_path != "":
			tex_path = ProjectSettings.globalize_path(character.texture.resource_path)
		EntityManager.register_entity("character", character, tex_path)

	input_field.text_submitted.connect(_on_input_submitted)

	CommandServer.command_received.connect(_on_command)
	CommandServer.context_requested.connect(_on_context_requested)
	CommandServer.client_connected.connect(func():
		status_label.text = "MCP connected — ready"
	)
	CommandServer.client_disconnected.connect(func():
		status_label.text = "MCP disconnected — waiting..."
	)


func _setup_placeholder(sprite: Sprite2D):
	if sprite.texture != null:
		return
	var img := Image.create(32, 48, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.4, 0.6, 0.9))
	sprite.texture = ImageTexture.create_from_image(img)


func _on_input_submitted(text: String):
	if text.strip_edges() == "":
		return

	input_field.clear()
	status_label.text = "Sending: %s" % text

	var context = _gather_context()
	CommandServer.send_user_prompt(text, context)


func _on_command(cmd: Dictionary):
	var cmd_type: String = cmd.get("type", "")

	match cmd_type:
		"spawn_entity":
			var pos = _dict_to_vec2(cmd.get("position", {}))
			var scl = _dict_to_vec2(cmd.get("scale", {"x": 1, "y": 1}))
			var dh = float(cmd.get("desired_height", 0))
			EntityManager.spawn_entity(
				cmd.get("id", "entity_%d" % randi()),
				cmd.get("texture_path", ""),
				pos, scl, dh,
			)
			status_label.text = "Spawned: %s" % cmd.get("id", "?")

		"spawn_animated_entity":
			var pos = _dict_to_vec2(cmd.get("position", {}))
			var scl = _dict_to_vec2(cmd.get("scale", {"x": 1, "y": 1}))
			var dh = float(cmd.get("desired_height", 0))
			EntityManager.spawn_animated_entity(
				cmd.get("id", "entity_%d" % randi()),
				cmd.get("spritesheet_path", ""),
				int(cmd.get("frame_count", 1)),
				int(cmd.get("columns", 1)),
				float(cmd.get("fps", 8)),
				pos, scl, dh,
			)
			status_label.text = "Spawned animated: %s" % cmd.get("id", "?")

		"update_animation":
			EntityManager.update_animation(
				cmd.get("entity_id", ""),
				cmd.get("animation_name", "default"),
				cmd.get("spritesheet_path", ""),
				int(cmd.get("frame_count", 1)),
				int(cmd.get("columns", 1)),
				float(cmd.get("fps", 8)),
			)
			status_label.text = "Animation updated"

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
			status_label.text = "Behavior detached"

		"remove_entity":
			EntityManager.remove_entity(cmd.get("id", ""))
			status_label.text = "Removed: %s" % cmd.get("id", "?")

		"status":
			status_label.text = cmd.get("message", "")

		_:
			push_warning("[Main] Unknown command: %s" % cmd_type)


func _on_context_requested():
	var context = _gather_context()
	CommandServer.send_context(context)


func _gather_context() -> Dictionary:
	var files = _list_files("res://scripts/", [])
	var scripts_content := {}
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
		"ground_y": EntityManager.get_ground_y(),
		"viewport": {"width": 1280, "height": 720},
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


func _dict_to_vec2(d: Dictionary) -> Vector2:
	return Vector2(
		float(d.get("x", 0)),
		float(d.get("y", 0))
	)
