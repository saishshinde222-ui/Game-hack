extends Node
## Oscillates the parent Node2D side-to-side using a sine wave.

@export var speed: float = 2.0
@export var range_x: float = 50.0

var _time: float = 0.0
var _origin_x: float = 0.0


func _ready():
	_origin_x = get_parent().position.x


func _process(delta: float):
	_time += delta * speed
	get_parent().position.x = _origin_x + sin(_time) * range_x
