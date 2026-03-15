extends Node
## Responds to "chop" action — plays a fall animation, emits chopped signal.

signal chopped()

@export var fall_duration: float = 1.0
var _is_chopped := false


func chop():
	if _is_chopped:
		return

	_is_chopped = true
	var parent = get_parent()

	var tween = parent.create_tween()
	tween.tween_property(parent, "rotation_degrees:z", 90.0, fall_duration)\
		.set_ease(Tween.EASE_IN)\
		.set_trans(Tween.TRANS_QUAD)
	tween.tween_callback(func():
		chopped.emit()
		print("[Choppable] '%s' has been chopped" % parent.name)
	)
