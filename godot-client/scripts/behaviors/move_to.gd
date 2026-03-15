extends Node
## Moves the parent Node3D toward a target position, emits arrived when close.

signal arrived()

@export var target_position: Vector3 = Vector3.ZERO
@export var speed: float = 3.0
@export var arrive_distance: float = 0.2

var _moving := false


func _ready():
	if target_position != Vector3.ZERO:
		_moving = true


func set_target(pos: Vector3):
	target_position = pos
	_moving = true


func _process(delta):
	if not _moving:
		return

	var parent = get_parent()
	var direction = (target_position - parent.position)
	var dist = direction.length()

	if dist <= arrive_distance:
		parent.position = target_position
		_moving = false
		arrived.emit()
		return

	parent.position += direction.normalized() * speed * delta

	var look_target = target_position
	look_target.y = parent.position.y
	if parent.position.distance_to(look_target) > 0.01:
		parent.look_at(look_target)
