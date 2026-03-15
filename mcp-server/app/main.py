import asyncio
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.orchestrator import forge_pipeline
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Godot client connected")
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "forge":
                seed_id = data.get("seed_id", str(uuid.uuid4()))
                growth_log = data.get("growth_log", {})
                logger.info("Forge request: seed_id=%s", seed_id)
                asyncio.create_task(
                    forge_pipeline(websocket, seed_id, growth_log)
                )

            elif action == "status":
                seed_id = data.get("seed_id")
                status = forge_store.get(seed_id, {"status": "Unknown"})
                await websocket.send_json({"seed_id": seed_id, **status})

    except WebSocketDisconnect:
        logger.info("Godot client disconnected")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
