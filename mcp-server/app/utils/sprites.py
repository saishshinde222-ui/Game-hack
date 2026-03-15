import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def convert_video_to_spritesheet(
    video_path: Path,
    output_dir: Path,
    seed_id: str,
    fps: int = 8,
    columns: int = 8,
) -> Path | None:
    sprite_path = output_dir / f"{seed_id}_sprite.png"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"fps={fps},tile={columns}x1",
            str(sprite_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error("ffmpeg failed: %s", stderr.decode())
            return None

        logger.info("Sprite sheet saved: %s", sprite_path)
        return sprite_path

    except FileNotFoundError:
        logger.error("ffmpeg not found — install it to enable sprite sheets")
        return None
