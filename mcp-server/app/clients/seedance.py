import asyncio
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ARK_BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
SEEDANCE_MODEL = "seedance-1-5-pro-251215"
POLL_INTERVAL = 10
MAX_POLL_TIME = 300


class SeedanceClient:
    """Seedance 1.5 Pro client via BytePlus Ark API for video generation.

    Uses the async task pattern:
      1. POST /contents/generations/tasks → returns task ID
      2. GET  /contents/generations/tasks/{id} → poll until succeeded
      3. Download video from content.video_url
    """

    def __init__(self):
        self.api_key = os.getenv("ARK_API_KEY", "")
        if not self.api_key:
            logger.warning("ARK_API_KEY not set — Seedance calls will fail")

    async def text_to_video(
        self,
        prompt: str,
        output_dir: Path,
        seed_id: str,
        duration: int = 5,
        ratio: str = "1:1",
    ) -> Path | None:
        mp4_path = output_dir / f"{seed_id}_anim.mp4"

        if not self.api_key:
            logger.warning("ARK_API_KEY not set — skipping video generation")
            return None

        content = [{"type": "text", "text": prompt}]
        return await self._create_and_poll(content, duration, ratio, mp4_path)

    async def image_to_video(
        self,
        image_url: str,
        prompt: str,
        output_dir: Path,
        seed_id: str,
        duration: int = 5,
        ratio: str = "1:1",
    ) -> Path | None:
        mp4_path = output_dir / f"{seed_id}_anim.mp4"

        if not self.api_key:
            logger.warning("ARK_API_KEY not set — skipping video generation")
            return None

        if not image_url:
            logger.error("No image URL provided for image-to-video")
            return None

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        return await self._create_and_poll(content, duration, ratio, mp4_path)

    async def _create_and_poll(
        self,
        content: list[dict],
        duration: int,
        ratio: str,
        output_path: Path,
    ) -> Path | None:
        task_id = await self._create_task(content, duration, ratio)
        if not task_id:
            return None

        video_url = await self._poll_task(task_id)
        if not video_url:
            return None

        return await self._download(video_url, output_path)

    async def _create_task(
        self, content: list[dict], duration: int, ratio: str
    ) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{ARK_BASE_URL}/contents/generations/tasks",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": SEEDANCE_MODEL,
                        "content": content,
                        "ratio": ratio,
                        "duration": duration,
                        "watermark": False,
                    },
                )
                resp.raise_for_status()
                task_id = resp.json().get("id")
                logger.info("Seedance task created: %s", task_id)
                return task_id
        except Exception as e:
            logger.error("Seedance task creation failed: %s", e)
            return None

    async def _poll_task(self, task_id: str) -> str | None:
        elapsed = 0
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while elapsed < MAX_POLL_TIME:
                    resp = await client.get(
                        f"{ARK_BASE_URL}/contents/generations/tasks/{task_id}",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    status = data.get("status", "")

                    if status == "succeeded":
                        video_url = data.get("content", {}).get("video_url")
                        logger.info("Seedance task %s succeeded", task_id)
                        return video_url
                    elif status == "failed":
                        error = data.get("error", {})
                        logger.error("Seedance task %s failed: %s", task_id, error)
                        return None
                    else:
                        logger.info(
                            "Seedance task %s status: %s, polling...", task_id, status
                        )
                        await asyncio.sleep(POLL_INTERVAL)
                        elapsed += POLL_INTERVAL

            logger.error("Seedance task %s timed out after %ds", task_id, MAX_POLL_TIME)
            return None
        except Exception as e:
            logger.error("Seedance polling failed: %s", e)
            return None

    async def _download(self, url: str, dest: Path) -> Path | None:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                logger.info("Saved video: %s", dest)
                return dest
        except Exception as e:
            logger.error("Video download failed: %s", e)
            return None
