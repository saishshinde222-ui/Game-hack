extends Marker3D
## Placed on a character at the hand position. Equippable items attach here.


func get_held_item() -> Node3D:
	for child in get_children():
		if child is Node3D:
			return child
	return null


func has_item() -> bool:
	return get_held_item() != null


func clear():
	for child in get_children():
		child.queue_free()
