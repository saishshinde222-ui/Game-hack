import asyncio
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

TRIPO_BASE = "https://api.tripo3d.ai/v2/openapi"


class TripoClient:
    def __init__(self):
        self.api_key = os.getenv("TRIPO_API_KEY", "")
        if not self.api_key:
            logger.warning("TRIPO_API_KEY not set — mesh generation will fail")

    async def generate(
        self, prompt: str, output_dir: Path, seed_id: str
    ) -> tuple[Path | None, Path | None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{TRIPO_BASE}/task",
                headers=headers,
                json={"type": "text_to_model", "prompt": prompt},
            )
            resp.raise_for_status()
            task_id = resp.json()["data"]["task_id"]
            logger.info("Tripo task started: %s", task_id)

            glb_url = None
            thumbnail_url = None

            for _ in range(90):
                await asyncio.sleep(2)
                poll = await client.get(
                    f"{TRIPO_BASE}/task/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                data = poll.json()["data"]
                status = data.get("status")

                if status == "success":
                    output = data.get("output", {})
                    glb_url = output.get("model")
                    thumbnail_url = output.get("rendered_image")
                    break
                if status in ("failed", "cancelled"):
                    raise RuntimeError(f"Tripo task {status}: {data}")

            if not glb_url:
                raise TimeoutError("Tripo generation timed out after 3 minutes")

            glb_path = output_dir / f"{seed_id}.glb"
            glb_resp = await client.get(glb_url)
            glb_path.write_bytes(glb_resp.content)
            logger.info("Saved mesh: %s", glb_path)

            thumbnail_path = None
            if thumbnail_url:
                thumbnail_path = output_dir / f"{seed_id}_thumb.png"
                thumb_resp = await client.get(thumbnail_url)
                thumbnail_path.write_bytes(thumb_resp.content)

            return glb_path, thumbnail_path
