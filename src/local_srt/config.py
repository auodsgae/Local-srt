from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LocalSRT"
SAMPLE_RATE = 16_000
MAX_ALIGN_CHUNK_SECONDS = 270.0

ASR_MODELS = {
    "1.7b": "Qwen/Qwen3-ASR-1.7B",
    "0.6b": "Qwen/Qwen3-ASR-0.6B",
}
DEFAULT_ASR_MODEL = "1.7b"
DEFAULT_ALIGNER_MODEL = "Qwen/Qwen3-ForcedAligner-0.6B"

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".ts",
    ".m2ts",
    ".mpg",
    ".mpeg",
    ".m4v",
    ".vob",
    ".3gp",
    ".f4v",
    ".mxf",
}

AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".wma",
}

SUPPORTED_INPUT_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def app_data_dir() -> Path:
    portable_root = os.environ.get("LOCAL_SRT_APP_DATA")
    if portable_root:
        return Path(portable_root).expanduser()
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if root:
            return Path(root) / APP_NAME
    return Path.home() / ".local-srt"


def model_cache_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]
