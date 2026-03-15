extends Node
## Moves the parent Node2D toward a target position, emits arrived when close.

signal arrived()

@export var target_position: Vector2 = Vector2.ZERO
@export var speed: float = 100.0
@export var arrive_distance: float = 5.0

var _moving := false


func _ready():
	if target_position != Vector2.ZERO:
		_moving = true


func set_target(pos: Vector2):
	target_position = pos
	_moving = true


func _process(delta: float):
	if not _moving:
		return

	var parent = get_parent()
	var direction: Vector2 = target_position - parent.position
	var dist: float = direction.length()

	if dist <= arrive_distance:
		parent.position = target_position
		_moving = false
		arrived.emit()
		return

	parent.position += direction.normalized() * speed * delta
