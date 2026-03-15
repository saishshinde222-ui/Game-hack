import logging
import os
import struct
import zlib
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class SeedreamClient:
    def __init__(self):
        self.api_key = os.getenv("SEEDREAM_API_KEY", "")
        self.base_url = os.getenv(
            "SEEDREAM_BASE_URL",
            "https://api.volcengine.com/v1/images/generations",
        )

    async def generate(self, prompt: str, output_dir: Path, seed_id: str) -> Path:
        """Generate a generic image (icon, asset, etc.)."""
        icon_path = output_dir / f"{seed_id}_icon.png"
        return await self._generate_image(prompt, icon_path, "512x512")

    async def generate_face(self, prompt: str, output_dir: Path, seed_id: str) -> Path:
        """Generate a character face portrait with emotion."""
        face_path = output_dir / f"{seed_id}_face.png"
        return await self._generate_image(prompt, face_path, "512x512")

    async def _generate_image(self, prompt: str, output_path: Path, size: str) -> Path:
        if not self.api_key:
            logger.warning("SEEDREAM_API_KEY not set — using placeholder")
            return self._write_placeholder(output_path)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "seedream-5.0-lite",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                },
            )
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]

            img_resp = await client.get(image_url)
            output_path.write_bytes(img_resp.content)
            logger.info("Saved image: %s", output_path)
            return output_path

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
