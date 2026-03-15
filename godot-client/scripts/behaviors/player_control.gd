extends Node
## Keyboard-driven movement with gravity, jumping, and animation state switching.
## Supports both WASD and arrow keys. Attaches to any entity as a child node.

@export var move_speed: float = 200.0
@export var jump_velocity: float = -400.0
@export var gravity: float = 900.0

var _velocity: Vector2 = Vector2.ZERO
var _on_ground: bool = true
var _facing_right: bool = true
var _jump_held_last: bool = false


func _process(delta: float):
	var parent: Node2D = get_parent()
	if parent == null:
		return

	var direction: float = 0.0
	if Input.is_action_pressed("ui_right") or Input.is_key_pressed(KEY_D):
		direction = 1.0
	elif Input.is_action_pressed("ui_left") or Input.is_key_pressed(KEY_A):
		direction = -1.0

	_velocity.x = direction * move_speed

	_velocity.y += gravity * delta

	var jump_pressed: bool = (
		Input.is_action_pressed("ui_accept")
		or Input.is_key_pressed(KEY_W)
		or Input.is_key_pressed(KEY_SPACE)
	)
	var jump_just_pressed: bool = jump_pressed and not _jump_held_last
	_jump_held_last = jump_pressed

	if jump_just_pressed and _on_ground:
		_velocity.y = jump_velocity
		_on_ground = false

	parent.position += _velocity * delta

	var floor_y: float = EntityManager.GROUND_Y - _get_displayed_half_height(parent)
	if parent.position.y >= floor_y:
		parent.position.y = floor_y
		_velocity.y = 0.0
		_on_ground = true

	if direction > 0.0:
		_facing_right = true
		parent.scale.x = absf(parent.scale.x)
	elif direction < 0.0:
		_facing_right = false
		parent.scale.x = -absf(parent.scale.x)

	_update_animation(parent, direction)


func _update_animation(parent: Node2D, direction: float):
	if not parent is AnimatedSprite2D:
		return
	var anim: AnimatedSprite2D = parent
	var sf: SpriteFrames = anim.sprite_frames
	if sf == null:
		return

	if not _on_ground:
		_try_play(anim, sf, "jump")
	elif absf(direction) > 0.0:
		_try_play(anim, sf, "run")
	else:
		_try_play(anim, sf, "idle")


func _try_play(anim: AnimatedSprite2D, sf: SpriteFrames, desired: String):
	if sf.has_animation(desired):
		if anim.animation != desired:
			anim.play(desired)
		return
	if sf.has_animation("default"):
		if anim.animation != "default":
			anim.play("default")


func _get_displayed_half_height(node: Node2D) -> float:
	var h: float = 48.0
	if node is AnimatedSprite2D:
		var sf: SpriteFrames = node.sprite_frames
		if sf:
			for anim_name in ["idle", "default", "run"]:
				if sf.has_animation(anim_name) and sf.get_frame_count(anim_name) > 0:
					var tex = sf.get_frame_texture(anim_name, 0)
					if tex:
						h = tex.get_height()
						break
	elif node is Sprite2D and node.texture:
		h = node.texture.get_height()
	return h * absf(node.scale.y) * 0.5
