import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket

from app.clients.seedance import SeedanceClient
from app.clients.seedream import SeedreamClient
from app.clients.tripo import TripoClient
from app.reasoning import analyze_seed_state
from app.state import forge_store
from app.utils.sprites import convert_video_to_spritesheet

logger = logging.getLogger(__name__)
ASSETS_DIR = Path(__file__).parent.parent / "assets"


async def _push(ws: WebSocket, seed_id: str, status: str, message: str, **extra):
    payload = {"seed_id": seed_id, "status": status, "message": message, **extra}
    forge_store[seed_id] = payload
    try:
        await ws.send_json(payload)
    except Exception:
        logger.warning("WebSocket send failed for %s", seed_id)


async def forge_pipeline(ws: WebSocket, seed_id: str, growth_log: dict):
    try:
        # --- Step 1: Reasoning (local, instant) ---
        await _push(ws, seed_id, "Reasoning", "Analyzing growth log...")
        prompts = analyze_seed_state(growth_log)
        await asyncio.sleep(0.3)

        # --- Step 2: 3D mesh via Tripo ---
        await _push(ws, seed_id, "MeshGen", "Generating 3D weapon with Tripo...")
        tripo = TripoClient()
        glb_path, thumbnail_path = await tripo.generate(
            prompt=prompts["tripo_prompt"],
            output_dir=ASSETS_DIR,
            seed_id=seed_id,
        )

        # --- Step 3: 2D generation (icon + emotion in parallel) ---
        await _push(ws, seed_id, "EmotionGen", "Creating soul sprite & icon...")

        tasks = []

        seedream = SeedreamClient()
        tasks.append(
            seedream.generate(
                prompt=prompts["icon_prompt"],
                output_dir=ASSETS_DIR,
                seed_id=seed_id,
            )
        )

        if thumbnail_path and prompts.get("needs_2d"):
            seedance = SeedanceClient()
            tasks.append(
                seedance.generate(
                    reference_image=str(thumbnail_path),
                    emotion_tags=prompts["emotion_tags"],
                    output_dir=ASSETS_DIR,
                    seed_id=seed_id,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        sprite_path = None
        icon_path = None
        for r in results:
            if isinstance(r, Exception):
                logger.error("Generation sub-task error: %s", r)
                continue
            if isinstance(r, Path):
                if r.suffix == ".mp4":
                    sprite_path = await convert_video_to_spritesheet(
                        r, ASSETS_DIR, seed_id
                    )
                elif "_icon" in r.stem:
                    icon_path = r

        # --- Step 4: Done ---
        await _push(
            ws,
            seed_id,
            "Ready",
            "Weapon forged!",
            glb_url=f"/assets/{seed_id}.glb" if glb_path else None,
            sprite_url=f"/assets/{seed_id}_sprite.png" if sprite_path else None,
            icon_url=f"/assets/{seed_id}_icon.png" if icon_path else None,
            tripo_prompt=prompts["tripo_prompt"],
            emotion_tags=prompts["emotion_tags"],
        )

    except Exception as e:
        logger.exception("Forge pipeline failed for %s", seed_id)
        await _push(ws, seed_id, "Failed", str(e))
