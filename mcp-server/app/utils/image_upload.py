import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://0x0.st"


async def upload_image(image_path: Path) -> str | None:
    """Upload a local image to 0x0.st and return the public URL.

    Returns None on failure so callers can fall back gracefully.
    """
    if not image_path.exists():
        logger.error("upload_image: file not found: %s", image_path)
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(image_path, "rb") as f:
                resp = await client.post(
                    UPLOAD_URL,
                    files={"file": (image_path.name, f, "image/png")},
                )
            if resp.status_code == 200:
                url = resp.text.strip()
                logger.info("Uploaded %s → %s", image_path.name, url)
                return url
            else:
                logger.error(
                    "Upload failed (HTTP %d): %s", resp.status_code, resp.text[:200]
                )
                return None
    except Exception as e:
        logger.error("Upload exception: %s", e)
        return None
