from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

from .config import SAMPLE_RATE, bundled_base_dir


class MediaError(RuntimeError):
    pass


def find_ffmpeg() -> Path | None:
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    local = bundled_base_dir() / "ffmpeg" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if local.exists():
        return local
    return None


def decode_to_pcm16k(input_path: Path, ffmpeg_path: Path | None = None) -> tuple[np.ndarray, float]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        raise MediaError("ffmpeg was not found. Install ffmpeg or place ffmpeg.exe in the app ffmpeg folder.")
    if not input_path.exists():
        raise MediaError(f"Input file does not exist: {input_path}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "1",
        "-f",
        "wav",
        str(wav_path),
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode(errors="replace")
            last_line = next((line.strip() for line in reversed(stderr.splitlines()) if line.strip()), "unknown ffmpeg error")
            raise MediaError(f"ffmpeg failed: {last_line}")
        return read_wav_float32(wav_path)
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            pass


def read_wav_float32(path: Path) -> tuple[np.ndarray, float]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getframerate() != SAMPLE_RATE:
            raise MediaError("Decoded WAV is not 16 kHz mono.")
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if sample_width != 2:
        raise MediaError("Decoded WAV is not 16-bit PCM.")
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return audio, len(audio) / SAMPLE_RATE


def chunk_audio(audio: np.ndarray, max_seconds: float) -> list[tuple[float, np.ndarray]]:
    max_samples = max(1, int(max_seconds * SAMPLE_RATE))
    chunks: list[tuple[float, np.ndarray]] = []
    for start_sample in range(0, len(audio), max_samples):
        chunk = audio[start_sample : start_sample + max_samples]
        if len(chunk) == 0:
            continue
        chunks.append((start_sample / SAMPLE_RATE, chunk))
    return chunks

