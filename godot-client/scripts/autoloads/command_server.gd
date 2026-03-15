extends Node
## WebSocket server on localhost:9080. MCP connects here.
## Receives JSON commands, emits signals for EntityManager / main.gd.

signal command_received(command: Dictionary)
signal client_connected()
signal client_disconnected()
signal context_requested()

var _tcp_server := TCPServer.new()
var _peer: WebSocketPeer = null
var _stream: StreamPeerTCP = null

const PORT := 9080


func _ready():
	var err = _tcp_server.listen(PORT)
	if err != OK:
		push_error("[CmdServer] Failed to listen on port %d: %s" % [PORT, err])
		return
	print("[CmdServer] Listening on ws://localhost:%d" % PORT)


func _process(_delta):
	if _peer == null:
		_try_accept()
	else:
		_poll_peer()


func _try_accept():
	if not _tcp_server.is_connection_available():
		return

	_stream = _tcp_server.take_connection()
	_peer = WebSocketPeer.new()
	var err = _peer.accept_stream(_stream)
	if err != OK:
		push_error("[CmdServer] accept_stream failed: %s" % err)
		_peer = null
		_stream = null
		return

	print("[CmdServer] MCP client connected")
	client_connected.emit()


func _poll_peer():
	_peer.poll()

	match _peer.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			while _peer.get_available_packet_count() > 0:
				var text = _peer.get_packet().get_string_from_utf8()
				_handle_message(text)
		WebSocketPeer.STATE_CLOSED:
			print("[CmdServer] MCP client disconnected")
			client_disconnected.emit()
			_peer = null
			_stream = null


func _handle_message(text: String):
	var json = JSON.new()
	if json.parse(text) != OK:
		push_error("[CmdServer] Invalid JSON: %s" % text)
		return

	var data: Dictionary = json.data
	var cmd_type = data.get("type", "")

	if cmd_type == "request_context":
		context_requested.emit()
	else:
		command_received.emit(data)


func send_to_mcp(payload: Dictionary):
	if _peer == null or _peer.get_ready_state() != WebSocketPeer.STATE_OPEN:
		push_error("[CmdServer] No MCP client connected")
		return
	_peer.send_text(JSON.stringify(payload))


func send_context(context: Dictionary):
	send_to_mcp({"type": "context", "data": context})


func send_user_prompt(prompt: String, context: Dictionary):
	send_to_mcp({
		"type": "user_prompt",
		"prompt": prompt,
		"context": context,
	})


func is_connected_to_mcp() -> bool:
	return _peer != null and _peer.get_ready_state() == WebSocketPeer.STATE_OPEN
