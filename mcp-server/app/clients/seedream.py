import logging
import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ARK_BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
SEEDREAM_MODEL = "seedream-5-0-260128"


@dataclass
class GeneratedImage:
    path: Path
    url: str


class SeedreamClient:
    def __init__(self):
        self.api_key = os.getenv("ARK_API_KEY", "")

    async def generate(self, prompt: str, output_dir: Path, seed_id: str) -> GeneratedImage:
        """Generate a sprite image and return both local path and remote URL."""
        icon_path = output_dir / f"{seed_id}_icon.png"
        return await self._generate_image(prompt, icon_path, "1024x1024")

    async def generate_face(self, prompt: str, output_dir: Path, seed_id: str) -> GeneratedImage:
        """Generate a character face portrait."""
        face_path = output_dir / f"{seed_id}_face.png"
        return await self._generate_image(prompt, face_path, "1024x1024")

    async def _generate_image(self, prompt: str, output_path: Path, size: str) -> GeneratedImage:
        if not self.api_key:
            logger.warning("ARK_API_KEY not set — using placeholder")
            return GeneratedImage(path=self._write_placeholder(output_path), url="")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ARK_BASE_URL}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": SEEDREAM_MODEL,
                    "prompt": prompt,
                    "size": "2048x2048",
                    "response_format": "url",
                    "output_format": "png",
                    "watermark": False,
                },
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("Seedream image generation failed: %s\nResponse: %s", e, resp.text)
                raise
            data = resp.json()
            image_url = data["data"][0]["url"]

            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            output_path.write_bytes(img_resp.content)
            logger.info("Saved image: %s", output_path)
            return GeneratedImage(path=output_path, url=image_url)

    @staticmethod
    def _write_placeholder(path: Path) -> Path:
        """64x64 dark-purple placeholder PNG."""
        w, h = 64, 64
        raw = b""
        for _ in range(h):
            raw += b"\x00" + b"\x40\x20\x60\xff" * w

        def chunk(tag: bytes, data: bytes) -> bytes:
            body = tag + data
            return len(data).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", zlib.compress(raw))
        png += chunk(b"IEND", b"")
        path.write_bytes(png)
        return path
