extends RefCounted
## Loads PNG textures and spritesheets from absolute paths at runtime.


static func load_texture(path: String) -> ImageTexture:
	if path == "":
		return null

	var file = FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("[Loader] Cannot open: %s" % path)
		return null

	var buffer = file.get_buffer(file.get_length())
	file.close()

	var img = Image.new()
	var err: int

	if path.ends_with(".png"):
		err = img.load_png_from_buffer(buffer)
	elif path.ends_with(".jpg") or path.ends_with(".jpeg"):
		err = img.load_jpg_from_buffer(buffer)
	elif path.ends_with(".webp"):
		err = img.load_webp_from_buffer(buffer)
	else:
		err = img.load_png_from_buffer(buffer)

	if err != OK:
		push_error("[Loader] Image decode failed: %s" % path)
		return null

	return ImageTexture.create_from_image(img)


static func load_spritesheet(path: String, columns: int, rows: int, frame_count: int, fps: float = 8.0) -> SpriteFrames:
	var img_tex = load_texture(path)
	if img_tex == null:
		return null

	var sheet_w: int = img_tex.get_width()
	var sheet_h: int = img_tex.get_height()
	var frame_w: int = sheet_w / columns
	var frame_h: int = sheet_h / rows

	var frames = SpriteFrames.new()
	frames.set_animation_speed("default", fps)
	frames.set_animation_loop("default", true)

	var count := 0
	for row in range(rows):
		for col in range(columns):
			if count >= frame_count:
				break
			var atlas = AtlasTexture.new()
			atlas.atlas = img_tex
			atlas.region = Rect2(col * frame_w, row * frame_h, frame_w, frame_h)
			frames.add_frame("default", atlas)
			count += 1
		if count >= frame_count:
			break

	return frames
