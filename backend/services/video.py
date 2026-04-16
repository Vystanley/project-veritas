"""Video / audio / subtitle processing pipeline (download, transcribe, extract frames)."""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from typing import List, Optional

import speech_recognition as sr
from fastapi import HTTPException
from pydub import AudioSegment, effects

from config import FFMPEG_PATH, FFPROBE_PATH, YT_DLP_PATH

logger = logging.getLogger(__name__)


async def _run_subprocess(cmd: list, timeout: int = 120):
    """Run a subprocess off the event loop (works on Windows under uvicorn --reload).

    Returns (returncode, stdout_bytes, stderr_bytes). Raises subprocess.TimeoutExpired
    on timeout so callers can handle it.
    """
    def _run():
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    result = await asyncio.to_thread(_run)
    return result.returncode, result.stdout, result.stderr


def ensure_ffmpeg():
    """Check and install ffmpeg if missing."""
    global FFMPEG_PATH, FFPROBE_PATH  # noqa: PLW0603
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found, attempting install...")
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], capture_output=True, timeout=120)
        FFMPEG_PATH = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        FFPROBE_PATH = shutil.which("ffprobe") or "/usr/bin/ffprobe"


async def download_video(video_url: str, temp_dir: str) -> Optional[str]:
    """Download video as MP4 using yt-dlp with retry. Returns path or None if download fails."""
    ensure_ffmpeg()
    video_path = os.path.join(temp_dir, "video.mp4")

    strategies = [
        ["-f", "best[ext=mp4]/best", "--merge-output-format", "mp4"],
        ["-f", "best"],
        ["--impersonate", "chrome", "-f", "best[ext=mp4]/best", "--merge-output-format", "mp4"],
    ]

    for i, extra_args in enumerate(strategies):
        if i > 0:
            for f in os.listdir(temp_dir):
                fp = os.path.join(temp_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)

        cmd = [YT_DLP_PATH]
        # Only pass --ffmpeg-location if we found a REAL ffmpeg install (not the WinGet shim folder).
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            ffmpeg_dir = os.path.dirname(ffmpeg_bin)
            ffprobe_in_same_dir = os.path.exists(os.path.join(ffmpeg_dir, "ffprobe.exe")) or \
                                  os.path.exists(os.path.join(ffmpeg_dir, "ffprobe"))
            if ffprobe_in_same_dir:
                cmd += ["--ffmpeg-location", ffmpeg_dir]
            # else: rely on PATH — yt-dlp will find ffmpeg/ffprobe on its own
        cmd += [
            "--no-playlist",
            "--max-filesize", "50m",
            "--socket-timeout", "30",
            *extra_args,
            "-o", video_path,
            video_url,
        ]
        logger.info(f"yt-dlp strategy {i+1} running: {' '.join(cmd)}")
        try:
            returncode, stdout, stderr = await _run_subprocess(cmd, timeout=120)
        except subprocess.TimeoutExpired:
            logger.warning(f"Video download timed out (strategy {i+1})")
            continue
        except Exception as e:
            logger.error(f"yt-dlp strategy {i+1} spawn error: {type(e).__name__}: {e}")
            continue

        if returncode != 0:
            error_msg = stderr.decode(errors="replace") if stderr else "Unknown error"
            logger.warning(f"yt-dlp strategy {i+1} failed (rc={returncode}): {error_msg[:800]}")
            continue

        if not os.path.exists(video_path):
            for f in os.listdir(temp_dir):
                if f.startswith("video") and any(f.endswith(ext) for ext in [".mp4", ".webm", ".mkv"]):
                    video_path = os.path.join(temp_dir, f)
                    break
        if not os.path.exists(video_path):
            for f in os.listdir(temp_dir):
                full = os.path.join(temp_dir, f)
                if os.path.isfile(full) and os.path.getsize(full) > 10000:
                    video_path = full
                    break

        if os.path.exists(video_path):
            logger.info(f"Video downloaded (strategy {i+1}): {video_path} ({os.path.getsize(video_path)} bytes)")
            return video_path

    return None


async def download_subtitles(video_url: str, temp_dir: str) -> Optional[str]:
    """Try to download subtitles/captions from the video (YouTube fallback)."""
    sub_path = os.path.join(temp_dir, "subs")
    cmd = [
        YT_DLP_PATH,
        "--write-auto-sub",
        "--sub-lang", "en",
        "--skip-download",
        "--no-playlist",
        "-o", sub_path,
        video_url,
    ]
    try:
        await _run_subprocess(cmd, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        logger.warning(f"Subtitle subprocess error: {e}")
        return None

    for f in os.listdir(temp_dir):
        if f.endswith(".vtt") or f.endswith(".srt"):
            vtt_path = os.path.join(temp_dir, f)
            with open(vtt_path, "r") as fh:
                content = fh.read()
            lines = []
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                    continue
                if "-->" in line:
                    continue
                clean = re.sub(r"<[^>]+>", "", line)
                clean = clean.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
                if clean.strip():
                    lines.append(clean.strip())
            deduped = []
            for l in lines:
                if not deduped or l != deduped[-1]:
                    deduped.append(l)
            transcript = " ".join(deduped)
            if len(transcript) > 10:
                logger.info(f"Subtitles extracted: {len(transcript)} chars")
                return transcript
    return None


async def get_remote_video_duration(video_url: str) -> Optional[float]:
    """Fetch duration in seconds from the URL's metadata without downloading the video.

    Uses `yt-dlp --dump-json --skip-download` which is quick (~1-3s) and lets us
    reject videos that are too long BEFORE paying the download + analysis cost.
    Returns None if yt-dlp can't determine the duration — callers should treat
    that as "unknown, let it through" rather than blocking.
    """
    cmd = [
        YT_DLP_PATH,
        "--dump-json",
        "--skip-download",
        "--no-playlist",
        "--socket-timeout", "20",
        video_url,
    ]
    try:
        returncode, stdout, stderr = await _run_subprocess(cmd, timeout=30)
    except subprocess.TimeoutExpired:
        logger.warning("Duration probe timed out; allowing request through.")
        return None
    except Exception as e:
        logger.warning(f"Duration probe spawn error: {e}")
        return None

    if returncode != 0:
        logger.info(f"Duration probe returned rc={returncode}; proceeding without limit check.")
        return None

    try:
        info = json.loads(stdout.decode(errors="replace"))
    except Exception as e:
        logger.warning(f"Duration probe JSON parse failed: {e}")
        return None

    duration = info.get("duration")
    if isinstance(duration, (int, float)) and duration > 0:
        return float(duration)
    return None


async def _probe_duration(video_path: str) -> Optional[float]:
    """Return video duration in seconds, or None if ffprobe fails."""
    cmd = [
        FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    try:
        rc, stdout, _ = await _run_subprocess(cmd, timeout=15)
        if rc == 0 and stdout:
            return float(stdout.decode().strip())
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
    return None


async def extract_frames(video_path: str, temp_dir: str, num_frames: int = 8) -> List[str]:
    """Extract evenly-spaced frames across the entire video (not just the first seconds).

    Uses ffprobe to get duration, then samples num_frames points uniformly.
    Falls back to the old fps=1 method if probing fails.
    """
    frames_dir = os.path.join(temp_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    duration = await _probe_duration(video_path)

    if duration and duration > 1.0:
        # Sample `num_frames` timestamps evenly across the video, skipping the very first/last
        # tenth (titles/end cards often distort).
        start = duration * 0.05
        end = duration * 0.95
        step = (end - start) / max(num_frames - 1, 1)
        timestamps = [start + i * step for i in range(num_frames)]

        for idx, ts in enumerate(timestamps):
            out = os.path.join(frames_dir, f"frame_{idx:03d}.jpg")
            cmd = [
                FFMPEG_PATH, "-ss", f"{ts:.3f}", "-i", video_path,
                "-frames:v", "1", "-vf", "scale=768:-1",
                "-q:v", "4", out, "-y",
            ]
            try:
                await _run_subprocess(cmd, timeout=15)
            except Exception as e:
                logger.warning(f"Frame extraction at {ts:.1f}s failed: {e}")
    else:
        # Fallback: first N seconds
        cmd = [
            FFMPEG_PATH, "-i", video_path,
            "-vf", "fps=1,scale=768:-1",
            "-frames:v", str(num_frames),
            "-q:v", "4",
            os.path.join(frames_dir, "frame_%03d.jpg"),
            "-y",
        ]
        await _run_subprocess(cmd, timeout=30)

    return sorted(
        [os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".jpg")]
    )


async def extract_audio(video_path: str, temp_dir: str) -> str:
    """Extract audio from video using ffmpeg."""
    audio_path = os.path.join(temp_dir, "audio.mp3")
    cmd = [FFMPEG_PATH, "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", audio_path, "-y"]
    await _run_subprocess(cmd, timeout=60)
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        raise HTTPException(status_code=400, detail="Could not extract audio from video")
    return audio_path


async def transcribe_audio(audio_path: str, temp_dir: str) -> str:
    """Transcribe audio using Google Speech Recognition (free, no API key required)."""
    try:
        wav_path = os.path.join(temp_dir, "audio_sr.wav")

        cmd = [FFMPEG_PATH, "-i", audio_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path, "-y"]
        await _run_subprocess(cmd, timeout=60)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 1000:
            raise Exception("WAV conversion failed")

        audio = AudioSegment.from_wav(wav_path)
        duration_ms = len(audio)
        logger.info(f"Audio duration: {duration_ms/1000:.1f}s")

        # --- Preprocessing to help Google STT with noisy / music-heavy audio ---
        # TikTok/Reels audio often buries speech under background music. We
        # normalize peak loudness, apply dynamic range compression (pulls up
        # quieter speech), then re-normalize. This measurably improves
        # transcription on mixed-audio clips without needing a paid STT.
        try:
            audio = effects.normalize(audio)
            audio = effects.compress_dynamic_range(audio, threshold=-20.0, ratio=4.0)
            audio = effects.normalize(audio)
            # Re-export the processed audio so the recognizer reads the cleaned version.
            audio.export(wav_path, format="wav")
            logger.info("Audio preprocessed: normalized + compressed")
        except Exception as e:
            logger.warning(f"Audio preprocessing failed (continuing with raw audio): {e}")

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 200  # slightly more sensitive than default

        chunk_duration_ms = 55000  # ~55 seconds per chunk (Google's limit is ~60s)

        if duration_ms <= 60000:
            chunks = [audio]
        else:
            chunks = [audio[i:i + chunk_duration_ms] for i in range(0, duration_ms, chunk_duration_ms)]

        full_transcript = []
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")

            with sr.AudioFile(chunk_path) as source:
                audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data)
                if text:
                    full_transcript.append(text)
                    logger.info(f"Chunk {i+1}/{len(chunks)} transcribed: {len(text)} chars")
            except sr.UnknownValueError:
                logger.warning(f"Chunk {i+1}: Could not understand audio")
            except sr.RequestError as e:
                logger.warning(f"Chunk {i+1}: Google STT request error: {e}")

        transcript = " ".join(full_transcript)
        if transcript and len(transcript) > 10:
            logger.info(f"Full transcript: {len(transcript)} chars")
            return transcript

        raise Exception("No speech detected in audio")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")
