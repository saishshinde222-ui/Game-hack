extends Node
## 2D Entity registry — spawns Sprite2D / AnimatedSprite2D entities,
## attaches/detaches behavior scripts, manages lifecycle.
## Auto-scales sprites to a desired display height and places them on the ground.

const RuntimeLoader = preload("res://scripts/runtime_loader.gd")

const BEHAVIOR_MAP := {
	"wander": "res://scripts/behaviors/wander.gd",
	"move_to": "res://scripts/behaviors/move_to.gd",
}

const GROUND_Y := 597.0

var _entities: Dictionary = {}
var _scene_root: Node2D = null


func set_scene_root(root: Node2D):
	_scene_root = root


func register_entity(id: String, node: Node2D):
	_entities[id] = node


func spawn_entity(id: String, texture_path: String, pos: Vector2, scl := Vector2.ONE, desired_height: float = 0.0) -> Node2D:
	if _entities.has(id):
		push_warning("[EntityMgr] Entity '%s' already exists, removing old" % id)
		remove_entity(id)

	var sprite := Sprite2D.new()
	var tex = RuntimeLoader.load_texture(texture_path)
	if tex:
		sprite.texture = tex
	else:
		sprite.texture = _create_placeholder_texture()

	if desired_height > 0.0 and sprite.texture:
		var tex_h: float = sprite.texture.get_height()
		if tex_h > 0.0:
			var s: float = desired_height / tex_h
			scl = Vector2(s, s)

	sprite.name = id
	sprite.scale = scl

	if pos.y <= 0.0 and sprite.texture:
		var displayed_h: float = sprite.texture.get_height() * scl.y
		pos.y = GROUND_Y - displayed_h * 0.5
	sprite.position = pos

	if _scene_root:
		_scene_root.add_child(sprite)
	else:
		push_error("[EntityMgr] No scene root set")
		return null

	_entities[id] = sprite
	print("[EntityMgr] Spawned '%s' at %s (scale %s)" % [id, pos, scl])
	return sprite


func spawn_animated_entity(id: String, spritesheet_path: String, frame_count: int, columns: int, fps: float, pos: Vector2, scl := Vector2.ONE, desired_height: float = 0.0) -> Node2D:
	if _entities.has(id):
		push_warning("[EntityMgr] Entity '%s' already exists, removing old" % id)
		remove_entity(id)

	var rows := ceili(float(frame_count) / float(columns))
	var sf = RuntimeLoader.load_spritesheet(spritesheet_path, columns, rows, frame_count, fps)

	var animated := AnimatedSprite2D.new()
	if sf:
		animated.sprite_frames = sf
		animated.play("default")
	else:
		push_error("[EntityMgr] Failed to load spritesheet for '%s'" % id)

	if desired_height > 0.0 and sf:
		var first_frame = sf.get_frame_texture("default", 0)
		if first_frame:
			var tex_h: float = first_frame.get_height()
			if tex_h > 0.0:
				var s: float = desired_height / tex_h
				scl = Vector2(s, s)

	animated.name = id
	animated.scale = scl

	if pos.y <= 0.0 and sf:
		var first_frame = sf.get_frame_texture("default", 0)
		if first_frame:
			var displayed_h: float = first_frame.get_height() * scl.y
			pos.y = GROUND_Y - displayed_h * 0.5
	animated.position = pos

	if _scene_root:
		_scene_root.add_child(animated)
	else:
		push_error("[EntityMgr] No scene root set")
		return null

	_entities[id] = animated
	print("[EntityMgr] Spawned animated '%s' at %s (scale %s)" % [id, pos, scl])
	return animated


func update_animation(entity_id: String, anim_name: String, spritesheet_path: String, frame_count: int, columns: int, fps: float):
	if not _entities.has(entity_id):
		push_error("[EntityMgr] Entity '%s' not found" % entity_id)
		return

	var node = _entities[entity_id]
	if not node is AnimatedSprite2D:
		push_error("[EntityMgr] '%s' is not AnimatedSprite2D" % entity_id)
		return

	var animated: AnimatedSprite2D = node
	var rows := ceili(float(frame_count) / float(columns))
	var new_sf = RuntimeLoader.load_spritesheet(spritesheet_path, columns, rows, frame_count, fps)
	if new_sf == null:
		push_error("[EntityMgr] Failed to load spritesheet for animation '%s'" % anim_name)
		return

	var existing = animated.sprite_frames
	if existing == null:
		existing = SpriteFrames.new()
		animated.sprite_frames = existing

	if existing.has_animation(anim_name):
		existing.remove_animation(anim_name)

	existing.add_animation(anim_name)
	existing.set_animation_speed(anim_name, fps)
	existing.set_animation_loop(anim_name, true)

	for i in range(new_sf.get_frame_count("default")):
		existing.add_frame(anim_name, new_sf.get_frame_texture("default", i))

	animated.play(anim_name)
	print("[EntityMgr] Updated animation '%s' on '%s'" % [anim_name, entity_id])


func remove_entity(id: String):
	if not _entities.has(id):
		push_warning("[EntityMgr] Entity '%s' not found" % id)
		return

	var node: Node2D = _entities[id]
	node.queue_free()
	_entities.erase(id)
	print("[EntityMgr] Removed '%s'" % id)


func attach_behavior(entity_id: String, behavior_key: String, params: Dictionary):
	if not _entities.has(entity_id):
		push_error("[EntityMgr] Entity '%s' not found for attach" % entity_id)
		return

	if not BEHAVIOR_MAP.has(behavior_key):
		push_error("[EntityMgr] Unknown behavior: '%s'" % behavior_key)
		return

	var entity: Node2D = _entities[entity_id]

	for child in entity.get_children():
		if child.name == behavior_key:
			push_warning("[EntityMgr] Behavior '%s' already on '%s'" % [behavior_key, entity_id])
			return

	var script_res = load(BEHAVIOR_MAP[behavior_key])
	var behavior_node = Node.new()
	behavior_node.set_script(script_res)
	behavior_node.name = behavior_key

	for key in params:
		if key in behavior_node:
			var value = params[key]
			if value is Dictionary and value.has("x") and value.has("y"):
				value = Vector2(float(value.x), float(value.y))
			behavior_node.set(key, value)

	entity.add_child(behavior_node)
	print("[EntityMgr] Attached '%s' to '%s'" % [behavior_key, entity_id])


func detach_behavior(entity_id: String, behavior_key: String):
	if not _entities.has(entity_id):
		return

	var entity: Node2D = _entities[entity_id]
	for child in entity.get_children():
		if child.name == behavior_key:
			child.queue_free()
			print("[EntityMgr] Detached '%s' from '%s'" % [behavior_key, entity_id])
			return


func get_entity(id: String) -> Node2D:
	return _entities.get(id)


func get_all_entity_ids() -> Array:
	return _entities.keys()


func get_entity_info() -> Array:
	var info := []
	for id in _entities:
		var node: Node2D = _entities[id]
		var behaviors := []
		for child in node.get_children():
			if child.name in BEHAVIOR_MAP:
				behaviors.append(child.name)
		info.append({
			"id": id,
			"position": {"x": node.position.x, "y": node.position.y},
			"behaviors": behaviors,
		})
	return info


func get_ground_y() -> float:
	return GROUND_Y


func _create_placeholder_texture() -> ImageTexture:
	var img := Image.create(32, 48, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.8, 0.3, 0.8))
	return ImageTexture.create_from_image(img)
