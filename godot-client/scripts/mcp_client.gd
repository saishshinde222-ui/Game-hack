extends Node
## Autoload singleton — manages the WebSocket connection to the MCP server.

signal status_updated(data: Dictionary)
signal forge_completed(data: Dictionary)
signal forge_failed(error: String)
signal server_connected()
signal server_disconnected()

var _ws := WebSocketPeer.new()
var _was_connected := false

@export var server_url: String = "ws://localhost:8000/ws"


func _ready():
	_connect_ws()


func _process(_delta):
	_ws.poll()

	var state = _ws.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN:
		if not _was_connected:
			_was_connected = true
			server_connected.emit()
			print("[MCP] Connected to server")

		while _ws.get_available_packet_count() > 0:
			var text = _ws.get_packet().get_string_from_utf8()
			_on_message(text)

	elif state == WebSocketPeer.STATE_CLOSED:
		if _was_connected:
			_was_connected = false
			server_disconnected.emit()
			print("[MCP] Disconnected — reconnecting in 2 s")
			await get_tree().create_timer(2.0).timeout
			_connect_ws()


func _connect_ws():
	var err = _ws.connect_to_url(server_url)
	if err != OK:
		push_error("[MCP] connect_to_url failed: %s" % err)


func send_forge(seed_id: String, growth_log: Dictionary):
	if not _was_connected:
		forge_failed.emit("Not connected to MCP server")
		return

	var payload = JSON.stringify({
		"action": "forge",
		"seed_id": seed_id,
		"growth_log": growth_log,
	})
	_ws.send_text(payload)


func _on_message(text: String):
	var json = JSON.new()
	if json.parse(text) != OK:
		push_error("[MCP] Bad JSON: %s" % text)
		return

	var data: Dictionary = json.data
	var status = data.get("status", "")

	status_updated.emit(data)

	match status:
		"Ready":
			forge_completed.emit(data)
		"Failed":
			forge_failed.emit(data.get("message", "Unknown error"))
