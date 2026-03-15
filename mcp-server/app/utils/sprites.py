import asyncio
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops

logger = logging.getLogger(__name__)


async def remove_background_and_trim(image_path: Path, threshold: int = 20) -> Path:
    """Remove white/near-white background from a sprite and autocrop to content bounds."""

    def _process():
        img = Image.open(image_path).convert("RGBA")

        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, white)
        diff_gray = diff.convert("L")

        alpha = diff_gray.point(lambda x: 255 if x > threshold else 0)
        img.putalpha(alpha)

        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        img.save(image_path)

    await asyncio.to_thread(_process)
    logger.info("Background removed and trimmed: %s", image_path.name)
    return image_path


@dataclass
class SpriteSheetMeta:
    path: Path
    frame_count: int
    columns: int
    rows: int
    frame_width: int
    frame_height: int

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "frame_count": self.frame_count,
            "columns": self.columns,
            "rows": self.rows,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
        }


async def extract_frames(
    video_path: Path,
    output_dir: Path,
    seed_id: str,
    fps: int = 8,
) -> list[Path] | None:
    """Extract individual frames from a video as PNGs."""
    frame_dir = output_dir / f"{seed_id}_frames"
    frame_dir.mkdir(exist_ok=True)
    pattern = str(frame_dir / "frame_%04d.png")

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"fps={fps}",
            pattern,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error("ffmpeg frame extraction failed: %s", stderr.decode())
            return None

        frames = sorted(frame_dir.glob("frame_*.png"))
        logger.info("Extracted %d frames to %s", len(frames), frame_dir)
        return frames

    except FileNotFoundError:
        logger.error("ffmpeg not found — install it to enable sprite sheets")
        return None


async def _probe_frame_size(video_path: Path, fps: int) -> tuple[int, int, int] | None:
    """Use ffprobe to get video frame dimensions and count expected frames."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(video_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None

        info = json.loads(stdout.decode())
        stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        if stream is None:
            return None

        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(info.get("format", {}).get("duration", 0))
        frame_count = max(1, int(duration * fps))
        return width, height, frame_count

    except Exception as e:
        logger.warning("ffprobe failed: %s", e)
        return None


async def convert_video_to_spritesheet(
    video_path: Path,
    output_dir: Path,
    seed_id: str,
    fps: int = 8,
    columns: int = 8,
) -> SpriteSheetMeta | None:
    """Convert a video into a tiled sprite sheet PNG with metadata."""
    sprite_path = output_dir / f"{seed_id}_sprite.png"

    probe = await _probe_frame_size(video_path, fps)
    if probe:
        frame_w, frame_h, frame_count = probe
    else:
        frame_w, frame_h, frame_count = 480, 480, fps * 5

    rows = math.ceil(frame_count / columns)

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"fps={fps},tile={columns}x{rows}",
            str(sprite_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error("ffmpeg spritesheet failed: %s", stderr.decode())
            return None

        logger.info("Sprite sheet saved: %s (%dx%d, %d frames)",
                     sprite_path, columns, rows, frame_count)

        return SpriteSheetMeta(
            path=sprite_path,
            frame_count=frame_count,
            columns=columns,
            rows=rows,
            frame_width=frame_w,
            frame_height=frame_h,
        )

    except FileNotFoundError:
        logger.error("ffmpeg not found — install it to enable sprite sheets")
        return None
