extends Node
## Marks the parent entity as equippable (can be picked up and held).

var is_equipped := false
var original_parent: Node = null
var original_transform: Transform3D


func equip(slot: Node3D):
	if is_equipped:
		return

	var parent = get_parent()
	original_parent = parent.get_parent()
	original_transform = parent.global_transform

	if parent.get_parent():
		parent.get_parent().remove_child(parent)

	slot.add_child(parent)
	parent.position = Vector3.ZERO
	parent.rotation = Vector3.ZERO
	is_equipped = true
	print("[Equippable] '%s' equipped" % parent.name)


func unequip():
	if not is_equipped or original_parent == null:
		return

	var parent = get_parent()
	if parent.get_parent():
		parent.get_parent().remove_child(parent)

	original_parent.add_child(parent)
	parent.global_transform = original_transform
	is_equipped = false
	print("[Equippable] '%s' unequipped" % parent.name)
