from __future__ import annotations

import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip, VideoFileClip, concatenate_videoclips

from .utils import ensure_dir


# Runway's Act-Two data-URI limit applies to the encoded URI string. Base64 adds roughly
# 33% overhead, so keep the raw MP4 comfortably below 12 MiB.
MAX_DATA_URI_VIDEO_BYTES = 11 * 1024 * 1024


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe_duration(path: str | Path) -> float:
    """Get duration through MoviePy/ffmpeg."""
    with VideoFileClip(str(path)) as clip:
        return float(clip.duration)


def compress_motion_reference(input_path: str | Path, output_path: str | Path) -> Path:
    """Normalize a motion reference to a compact H.264 MP4 for Runway Act-Two.

    Fitness reference clips are expected to be 3–30s. The command scales to fit 720x1280,
    preserves aspect ratio, pads to portrait, removes audio, normalizes to 30 fps and keeps
    enough headroom for Runway's base64 data-URI limit.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(input_path)
    if duration < 3 or duration > 30:
        raise ValueError(f"Motion-reference moet 3–30 seconden zijn; ontvangen: {duration:.1f}s")
    cmd = [
        _ffmpeg(), "-y", "-i", str(input_path),
        "-an",
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
        "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-b:v", "1400k", "-maxrate", "1700k", "-bufsize", "2800k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if output_path.stat().st_size > MAX_DATA_URI_VIDEO_BYTES:
        cmd[cmd.index("1400k")] = "900k"
        cmd[cmd.index("1700k")] = "1100k"
        cmd[cmd.index("2800k")] = "1800k"
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if output_path.stat().st_size > MAX_DATA_URI_VIDEO_BYTES:
        raise ValueError(
            "Motion-reference blijft te groot voor Runway Act-Two na base64-encoding. "
            "Kort de clip in of verlaag de bronresolutie."
        )
    return output_path


def _font(size: int, bold: bool = False):
    candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _title_overlay(text: str, width: int, height: int) -> np.ndarray:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(max(28, width // 22), bold=True)
    pad = max(18, width // 35)
    bbox = draw.textbbox((0, 0), text, font=font)
    box_w = bbox[2] - bbox[0] + pad * 2
    box_h = bbox[3] - bbox[1] + pad * 2
    x, y = pad, pad
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=18, fill=(0, 0, 0, 155))
    draw.text((x + pad, y + pad - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
    return np.array(canvas)


def _timer_overlay(seconds: int, width: int, height: int) -> np.ndarray:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(max(30, width // 20), bold=True)
    label = f"{max(0, seconds):02d}"
    bbox = draw.textbbox((0, 0), label, font=font)
    pad = max(16, width // 40)
    box_w = bbox[2] - bbox[0] + pad * 2
    box_h = bbox[3] - bbox[1] + pad * 2
    x = width - box_w - pad
    y = pad
    draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=18, fill=(0, 0, 0, 155))
    draw.text((x + pad, y + pad - bbox[1]), label, font=font, fill=(255, 255, 255, 255))
    return np.array(canvas)


def decorate_clip(video_path: str | Path, exercise_name: str, voiceover_path: str | Path | None = None):
    base = VideoFileClip(str(video_path)).without_audio()
    overlays = [base]
    overlays.append(ImageClip(_title_overlay(exercise_name.upper(), base.w, base.h)).with_duration(base.duration))
    total_seconds = max(1, int(math.ceil(base.duration)))
    for sec in range(total_seconds):
        remaining = max(0, total_seconds - sec)
        overlay = ImageClip(_timer_overlay(remaining, base.w, base.h)).with_start(sec).with_duration(min(1, base.duration - sec))
        overlays.append(overlay)
    composite = CompositeVideoClip(overlays, size=(base.w, base.h)).with_duration(base.duration)
    if voiceover_path and Path(voiceover_path).exists():
        audio = AudioFileClip(str(voiceover_path))
        if audio.duration > composite.duration - 0.25:
            audio = audio.subclipped(0, max(0.1, composite.duration - 0.25))
        audio = audio.with_start(0.15)
        composite = composite.with_audio(CompositeAudioClip([audio]).with_duration(composite.duration))
    return composite


def render_final_video(
    items: list[tuple[str | Path, str, str | Path | None]],
    output_path: str | Path,
    progress=None,
) -> Path:
    if not items:
        raise ValueError("Geen clips om te renderen.")
    clips = []
    try:
        for i, (video_path, name, voiceover_path) in enumerate(items, start=1):
            if progress:
                progress(f"Clip {i}/{len(items)} monteren: {name}")
            clips.append(decorate_clip(video_path, name, voiceover_path))
        final = concatenate_videoclips(clips, method="compose")
        output_path = Path(output_path)
        ensure_dir(output_path.parent)
        final.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="5500k",
            preset="medium",
            threads=4,
            logger=None,
        )
        final.close()
        return output_path
    finally:
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
