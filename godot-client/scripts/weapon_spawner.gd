extends Node3D
## Loads a .glb file and spawns it as a child of this node.

var current_weapon: Node3D = null


func spawn_from_file(glb_path: String):
	clear()

	var doc = GLTFDocument.new()
	var state = GLTFState.new()
	var err = doc.append_from_file(glb_path, state)
	if err != OK:
		push_error("Failed to load weapon GLB: %s" % glb_path)
		return

	var scene = doc.generate_scene(state)
	add_child(scene)
	current_weapon = scene
	print("[Spawner] Weapon placed: %s" % glb_path)


func clear():
	if current_weapon:
		current_weapon.queue_free()
		current_weapon = null
