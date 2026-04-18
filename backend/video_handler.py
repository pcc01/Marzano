"""
Video artifact handler.
Extracts frames from uploaded video files using ffmpeg,
returns them as base64 images for the AI vision model.
Optionally transcribes audio using faster-whisper (if installed).
"""

import asyncio
import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


FFPROBE_CMD = os.getenv("FFPROBE_CMD", "ffprobe")
FFMPEG_CMD = os.getenv("FFMPEG_CMD", "ffmpeg")
MAX_FRAMES = int(os.getenv("VIDEO_MAX_FRAMES", "8"))
MAX_VIDEO_SECONDS = int(os.getenv("VIDEO_MAX_SECONDS", "300"))  # 5 min cap


# ─────────────────────────────────────────
# Public API
# ─────────────────────────────────────────

async def process_video(video_bytes: bytes, filename: str) -> dict:
    """
    Main entry point. Returns:
    {
        "frames_b64": [<base64 jpg>, ...],
        "duration_s": float,
        "frame_count": int,
        "transcript": str | None,
        "summary_for_prompt": str,
    }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, filename)
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        # Get duration
        duration = await _get_duration(video_path)
        if duration is None:
            return _error_result("Could not read video duration — is ffmpeg installed?")

        # Cap at MAX_VIDEO_SECONDS
        duration = min(duration, MAX_VIDEO_SECONDS)

        # Extract evenly-spaced frames
        frames = await _extract_frames(video_path, duration, tmpdir)

        # Attempt transcription (optional)
        transcript = await _transcribe(video_path)

        summary = _build_summary(filename, duration, len(frames), transcript)

        return {
            "frames_b64": frames,
            "duration_s": round(duration, 1),
            "frame_count": len(frames),
            "transcript": transcript,
            "summary_for_prompt": summary,
            "error": None,
        }


def is_video_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in {
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv"
    }


# ─────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────

async def _get_duration(video_path: str) -> Optional[float]:
    try:
        result = await asyncio.create_subprocess_exec(
            FFPROBE_CMD,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(result.communicate(), timeout=15)
        return float(stdout.decode().strip())
    except Exception:
        return None


async def _extract_frames(
    video_path: str, duration: float, tmpdir: str
) -> list[str]:
    """Extract MAX_FRAMES evenly-spaced frames, return as base64 JPEG strings."""
    frame_interval = max(1.0, duration / MAX_FRAMES)
    output_pattern = os.path.join(tmpdir, "frame_%04d.jpg")

    try:
        proc = await asyncio.create_subprocess_exec(
            FFMPEG_CMD,
            "-i", video_path,
            "-vf", f"fps=1/{frame_interval:.2f}",
            "-vframes", str(MAX_FRAMES),
            "-q:v", "5",           # JPEG quality 1-31, lower = better
            "-vf", "scale=1280:-1", # cap width at 1280px
            output_pattern,
            "-y",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=120)
    except Exception as e:
        print(f"[VIDEO] Frame extraction error: {e}")
        return []

    frames = []
    for img_path in sorted(Path(tmpdir).glob("frame_*.jpg")):
        try:
            with open(img_path, "rb") as f:
                frames.append(base64.standard_b64encode(f.read()).decode())
        except Exception:
            pass
    return frames


async def _transcribe(video_path: str) -> Optional[str]:
    """
    Attempt transcription with faster-whisper.
    Returns None if not installed (graceful degradation).
    """
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(video_path, beam_size=3)
        text = " ".join(seg.text.strip() for seg in segments)
        return text[:3000] if text else None
    except ImportError:
        return None
    except Exception as e:
        print(f"[VIDEO] Transcription failed: {e}")
        return None


def _build_summary(
    filename: str, duration: float, frame_count: int, transcript: Optional[str]
) -> str:
    mins = int(duration // 60)
    secs = int(duration % 60)
    parts = [
        f"[Video artifact: {filename}]",
        f"Duration: {mins}m {secs}s",
        f"Frames analysed: {frame_count}",
    ]
    if transcript:
        parts.append(f"Audio transcript: {transcript[:500]}{'...' if len(transcript) > 500 else ''}")
    else:
        parts.append("Audio transcript: not available (faster-whisper not installed)")
    return "\n".join(parts)


def _error_result(message: str) -> dict:
    return {
        "frames_b64": [],
        "duration_s": 0,
        "frame_count": 0,
        "transcript": None,
        "summary_for_prompt": f"[Video processing error: {message}]",
        "error": message,
    }
