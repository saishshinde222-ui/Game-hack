import base64
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class SeedanceClient:
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY", "")
        self.base_url = os.getenv(
            "SEEDANCE_BASE_URL",
            "https://api.volcengine.com/v1/video/generations",
        )

    async def generate(
        self,
        reference_image: str,
        emotion_tags: list[str],
        output_dir: Path,
        seed_id: str,
    ) -> Path:
        mp4_path = output_dir / f"{seed_id}_emotion.mp4"

        if not self.api_key:
            logger.warning("SEEDANCE_API_KEY not set — skipping emotion video")
            placeholder = output_dir / f"{seed_id}_emotion_skip.txt"
            placeholder.write_text("SeeDance skipped: no API key")
            return placeholder

        emotion_str = ", ".join(emotion_tags)
        prompt = (
            f"A weapon sprite showing {emotion_str} energy, "
            f"pulsing glow effect, seamless loop, dark background"
        )

        with open(reference_image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "seedance-2.0",
                    "prompt": prompt,
                    "image": image_b64,
                    "duration": 5,
                },
            )
            resp.raise_for_status()
            video_url = resp.json()["data"][0]["url"]

            vid_resp = await client.get(video_url)
            mp4_path.write_bytes(vid_resp.content)
            logger.info("Saved emotion video: %s", mp4_path)
            return mp4_path
