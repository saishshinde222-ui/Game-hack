extends Node
## Downloads assets from the MCP server and loads them into Godot types.

const BASE_URL := "http://localhost:8000"


func download_glb(url_path: String, callback: Callable):
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(
		func(_result, code, _headers, body):
			if code == 200:
				var local = "user://dl_%s" % url_path.get_file()
				var f = FileAccess.open(local, FileAccess.WRITE)
				f.store_buffer(body)
				f.close()
				callback.call(local)
			else:
				push_error("GLB download failed (%d): %s" % [code, url_path])
			http.queue_free()
	)
	http.request(BASE_URL + url_path)


func download_texture(url_path: String, callback: Callable):
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(
		func(_result, code, _headers, body):
			if code == 200:
				var img = Image.new()
				if img.load_png_from_buffer(body) == OK:
					var tex = ImageTexture.create_from_image(img)
					callback.call(tex)
				else:
					push_error("PNG decode failed: %s" % url_path)
			else:
				push_error("Texture download failed (%d): %s" % [code, url_path])
			http.queue_free()
	)
	http.request(BASE_URL + url_path)


static func load_glb_as_scene(file_path: String) -> Node3D:
	var doc = GLTFDocument.new()
	var state = GLTFState.new()
	var err = doc.append_from_file(file_path, state)
	if err != OK:
		push_error("GLB load error: %s" % file_path)
		return null
	return doc.generate_scene(state)
