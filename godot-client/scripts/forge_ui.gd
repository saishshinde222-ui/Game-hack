extends Control
## Forge UI — button, status label, icon preview, combat-style picker.

@onready var forge_btn: Button = %ForgeButton
@onready var status_lbl: Label = %StatusLabel
@onready var preview_rect: TextureRect = %Preview
@onready var style_option: OptionButton = %StyleOption

var _loader: Node


func _ready():
	_loader = load("res://scripts/asset_loader.gd").new()
	add_child(_loader)

	forge_btn.pressed.connect(_on_forge)
	McpClient.status_updated.connect(_on_status)
	McpClient.forge_completed.connect(_on_completed)
	McpClient.forge_failed.connect(_on_failed)
	McpClient.server_connected.connect(func(): status_lbl.text = "Connected — ready to forge")
	McpClient.server_disconnected.connect(func(): status_lbl.text = "Disconnected from server...")

	_populate_styles()


func _populate_styles():
	for s in ["fire-heavy", "ice", "lightning", "shadow", "holy", "balanced"]:
		style_option.add_item(s)
	style_option.select(0)


func _on_forge():
	var style = style_option.get_item_text(style_option.selected)
	GrowthLog.log_combat(style, randf_range(500, 2500))
	GrowthLog.seed_state["angerEvents"] = randi_range(0, 8)

	forge_btn.disabled = true
	status_lbl.text = "Forging..."

	McpClient.send_forge(GrowthLog.get_seed_id(), GrowthLog.get_growth_log())


func _on_status(data: Dictionary):
	status_lbl.text = "%s — %s" % [data.get("status", ""), data.get("message", "")]


func _on_completed(data: Dictionary):
	forge_btn.disabled = false
	status_lbl.text = "Weapon forged!"

	var icon_url = data.get("icon_url", "")
	if icon_url:
		_loader.download_texture(icon_url, func(tex): preview_rect.texture = tex)

	var glb_url = data.get("glb_url", "")
	if glb_url:
		_loader.download_glb(glb_url, func(path):
			var spawner = get_tree().get_first_node_in_group("weapon_spawner")
			if spawner:
				spawner.spawn_from_file(path)
		)

	GrowthLog.reset()


func _on_failed(error: String):
	forge_btn.disabled = false
	status_lbl.text = "FAILED: %s" % error
