import asyncio
import json
import logging
import os
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.orchestrator import handle_user_prompt
from app.state import forge_store

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Weapon Forge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

GODOT_WS_URL = os.getenv("GODOT_WS_URL", "ws://localhost:9080")
godot_ws = None


async def connect_to_godot():
    """Connect to Godot's WebSocket server and listen for messages."""
    global godot_ws

    while True:
        try:
            logger.info("Connecting to Godot at %s ...", GODOT_WS_URL)
            async with websockets.connect(GODOT_WS_URL) as ws:
                godot_ws = ws
                logger.info("Connected to Godot")

                async for message in ws:
                    await _handle_godot_message(ws, message)

        except (ConnectionRefusedError, OSError):
            logger.info("Godot not available, retrying in 2s...")
        except websockets.ConnectionClosed:
            logger.info("Godot connection lost, reconnecting...")
        finally:
            godot_ws = None

        await asyncio.sleep(2)


async def _handle_godot_message(ws, raw: str):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Bad JSON from Godot: %s", raw)
        return

    msg_type = data.get("type", "")

    if msg_type == "user_prompt":
        prompt = data.get("prompt", "")
        context = data.get("context", {})
        logger.info("User prompt: %s", prompt)

        await send_to_godot({"type": "status", "message": "Processing: %s" % prompt})

        commands = await handle_user_prompt(prompt, context, ASSETS_DIR)

        for cmd in commands:
            await send_to_godot(cmd)

        await send_to_godot({"type": "status", "message": "Done"})

    elif msg_type == "context":
        logger.info("Received project context from Godot")
        forge_store["last_context"] = data.get("data", {})


async def send_to_godot(payload: dict):
    global godot_ws
    if godot_ws is None:
        logger.warning("Not connected to Godot, cannot send")
        return
    try:
        await godot_ws.send(json.dumps(payload))
    except websockets.ConnectionClosed:
        logger.warning("Godot connection closed during send")
        godot_ws = None


@app.on_event("startup")
async def startup():
    asyncio.create_task(connect_to_godot())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "godot_connected": godot_ws is not None,
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
