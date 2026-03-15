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
        icon_path = output_dir / f"{seed_id}_icon.png"

        if not self.api_key:
            logger.warning("SEEDREAM_API_KEY not set — using placeholder icon")
            return self._write_placeholder(icon_path)

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
                    "size": "512x512",
                },
            )
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]

            img_resp = await client.get(image_url)
            icon_path.write_bytes(img_resp.content)
            logger.info("Saved icon: %s", icon_path)
            return icon_path

    @staticmethod
    def _write_placeholder(path: Path) -> Path:
        """Write a minimal 64x64 dark-purple PNG as placeholder."""
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
