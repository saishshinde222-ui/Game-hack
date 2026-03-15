extends Node
## Autoload singleton that tracks player behaviour as a SeedState.

var seed_state: Dictionary = {}


func _ready():
	reset()


func reset():
	seed_state = {
		"SeedID": _uuid(),
		"combatStyle": "balanced",
		"timeInSun": 0,
		"angerEvents": 0,
		"damageDealt": 0,
	}


func log_combat(style: String, damage: float):
	seed_state["combatStyle"] = style
	seed_state["damageDealt"] += damage


func log_anger():
	seed_state["angerEvents"] += 1


func log_sun_time(seconds: float):
	seed_state["timeInSun"] += seconds


func get_growth_log() -> Dictionary:
	return {
		"combatStyle": seed_state["combatStyle"],
		"timeInSun": seed_state["timeInSun"],
		"angerEvents": seed_state["angerEvents"],
		"damageDealt": seed_state["damageDealt"],
	}


func get_seed_id() -> String:
	return seed_state["SeedID"]


func _uuid() -> String:
	var hex = "0123456789abcdef"
	var parts: PackedStringArray = []
	var lengths = [8, 4, 4, 4, 12]
	for seg_len in lengths:
		var seg = ""
		for _i in range(seg_len):
			seg += hex[randi() % hex.length()]
		parts.append(seg)
	return "-".join(parts)
