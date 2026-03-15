extends Node
## Entity registry — spawns entities, attaches/detaches behaviors, manages lifecycle.

const RuntimeLoader = preload("res://scripts/runtime_loader.gd")

const BEHAVIOR_MAP := {
	"wander": "res://scripts/behaviors/wander.gd",
	"move_to": "res://scripts/behaviors/move_to.gd",
	"choppable": "res://scripts/behaviors/choppable.gd",
	"equippable": "res://scripts/behaviors/equippable.gd",
}

var _entities: Dictionary = {}
var _scene_root: Node3D = null


func set_scene_root(root: Node3D):
	_scene_root = root


func spawn_entity(id: String, model_path: String, pos: Vector3, rot := Vector3.ZERO, scl := Vector3.ONE, scripts: Array = []) -> Node3D:
	if _entities.has(id):
		push_warning("[EntityMgr] Entity '%s' already exists, removing old" % id)
		remove_entity(id)

	var node: Node3D = null

	if model_path != "" and FileAccess.file_exists(model_path):
		node = RuntimeLoader.load_glb(model_path)
	elif model_path != "" and ResourceLoader.exists(model_path):
		node = RuntimeLoader.load_glb_from_res(model_path)

	if node == null:
		node = _create_placeholder()

	node.name = id
	node.position = pos
	node.rotation_degrees = rot
	node.scale = scl

	if _scene_root:
		_scene_root.add_child(node)
	else:
		push_error("[EntityMgr] No scene root set")
		return null

	_entities[id] = node

	for behavior_key in scripts:
		attach_behavior(id, behavior_key, {})

	print("[EntityMgr] Spawned '%s' at %s" % [id, pos])
	return node


func remove_entity(id: String):
	if not _entities.has(id):
		push_warning("[EntityMgr] Entity '%s' not found" % id)
		return

	var node: Node3D = _entities[id]
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

	var entity: Node3D = _entities[entity_id]

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
			behavior_node.set(key, params[key])

	entity.add_child(behavior_node)
	print("[EntityMgr] Attached '%s' to '%s'" % [behavior_key, entity_id])


func detach_behavior(entity_id: String, behavior_key: String):
	if not _entities.has(entity_id):
		return

	var entity: Node3D = _entities[entity_id]
	for child in entity.get_children():
		if child.name == behavior_key:
			child.queue_free()
			print("[EntityMgr] Detached '%s' from '%s'" % [behavior_key, entity_id])
			return


func equip_item(holder_id: String, item_id: String):
	if not _entities.has(holder_id) or not _entities.has(item_id):
		push_error("[EntityMgr] equip_item: missing entity")
		return

	var holder: Node3D = _entities[holder_id]
	var item: Node3D = _entities[item_id]

	var slot = holder.find_child("HoldableSlot", true, false)
	if slot == null:
		push_error("[EntityMgr] No HoldableSlot on '%s'" % holder_id)
		return

	if item.get_parent():
		item.get_parent().remove_child(item)
	slot.add_child(item)
	item.position = Vector3.ZERO
	item.rotation = Vector3.ZERO
	print("[EntityMgr] Equipped '%s' on '%s'" % [item_id, holder_id])


func interact(actor_id: String, target_id: String, action: String):
	if not _entities.has(target_id):
		push_error("[EntityMgr] interact: target '%s' not found" % target_id)
		return

	var target: Node3D = _entities[target_id]

	for child in target.get_children():
		if child.has_method(action):
			child.call(action)
			print("[EntityMgr] '%s' performed '%s' on '%s'" % [actor_id, action, target_id])
			return

	push_warning("[EntityMgr] No method '%s' on '%s'" % [action, target_id])


func get_entity(id: String) -> Node3D:
	return _entities.get(id)


func get_all_entity_ids() -> Array:
	return _entities.keys()


func get_entity_info() -> Array:
	var info = []
	for id in _entities:
		var node: Node3D = _entities[id]
		var behaviors = []
		for child in node.get_children():
			if child.name in BEHAVIOR_MAP:
				behaviors.append(child.name)
		info.append({
			"id": id,
			"position": {"x": node.position.x, "y": node.position.y, "z": node.position.z},
			"behaviors": behaviors,
		})
	return info


func _create_placeholder() -> Node3D:
	var node = Node3D.new()
	var mesh_instance = MeshInstance3D.new()
	var capsule = CapsuleMesh.new()
	capsule.radius = 0.3
	capsule.height = 1.0
	mesh_instance.mesh = capsule
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.8, 0.3, 0.8)
	mesh_instance.material_override = mat
	node.add_child(mesh_instance)
	return node
