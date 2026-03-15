extends RefCounted
## Loads a .glb file from an absolute path at runtime using GLTFDocument.


static func load_glb(absolute_path: String) -> Node3D:
	var file = FileAccess.open(absolute_path, FileAccess.READ)
	if file == null:
		push_error("[Loader] Cannot open: %s" % absolute_path)
		return null

	var buffer = file.get_buffer(file.get_length())
	file.close()

	var doc = GLTFDocument.new()
	var state = GLTFState.new()

	var err = doc.append_from_buffer(buffer, "", state)
	if err != OK:
		push_error("[Loader] GLB parse failed: %s" % absolute_path)
		return null

	var scene = doc.generate_scene(state)
	if scene == null:
		push_error("[Loader] generate_scene returned null: %s" % absolute_path)
		return null

	return scene


static func load_glb_from_res(res_path: String) -> Node3D:
	var doc = GLTFDocument.new()
	var state = GLTFState.new()
	var err = doc.append_from_file(res_path, state)
	if err != OK:
		push_error("[Loader] GLB load failed: %s" % res_path)
		return null
	return doc.generate_scene(state)
