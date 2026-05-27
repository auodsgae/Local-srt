from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .config import ASR_MODELS, DEFAULT_ALIGNER_MODEL, model_cache_dir

ProgressCallback = Callable[[dict], None]


class BackendError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionChunk:
    language: str
    text: str
    alignment_items: list


def _select_torch_dtype(torch, device: str):
    if device == "cpu":
        return torch.float32
    major, _minor = torch.cuda.get_device_capability(0)
    return torch.bfloat16 if major >= 8 else torch.float16


def assert_runtime_ready(device: str) -> str:
    try:
        import torch
    except Exception as exc:
        raise BackendError("PyTorch is not installed. Install dependencies with pip install -e .") from exc
    if device == "cpu":
        return "CPU"
    if device != "cuda":
        raise BackendError(f"Unsupported device: {device}")
    if not torch.cuda.is_available():
        raise BackendError("CUDA is unavailable. This v1 build requires an NVIDIA GPU with a working CUDA PyTorch install.")
    return torch.cuda.get_device_name(0)


class QwenBackend:
    def __init__(
        self,
        *,
        model_size: str = "1.7b",
        device: str = "cuda",
        cache_dir: Path | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.cache_dir = cache_dir or model_cache_dir()
        self.progress = progress or (lambda _event: None)
        self._model = None

    def _emit(self, event: dict) -> None:
        self.progress(event)

    def load(self) -> None:
        if self._model is not None:
            return
        if self.model_size not in ASR_MODELS:
            raise BackendError(f"Unsupported model size: {self.model_size}")

        runtime_name = assert_runtime_ready(self.device)
        if self.device == "cuda":
            self._emit({"type": "status", "message": f"Using NVIDIA GPU: {runtime_name}"})
        else:
            self._emit({"type": "status", "message": "Using CPU. This can be much slower than GPU mode."})
        os.environ.setdefault("HF_HOME", str(self.cache_dir / "huggingface"))
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        try:
            import torch
            from qwen_asr import Qwen3ASRModel
        except Exception as exc:
            raise BackendError("qwen-asr could not be imported. Install dependencies with pip install -e .") from exc

        dtype = _select_torch_dtype(torch, self.device)
        device_map = "cuda:0" if self.device == "cuda" else "cpu"
        self._emit({"type": "status", "message": "Loading Qwen3-ASR and ForcedAligner"})
        self._model = Qwen3ASRModel.from_pretrained(
            ASR_MODELS[self.model_size],
            dtype=dtype,
            device_map=device_map,
            cache_dir=str(self.cache_dir),
            forced_aligner=DEFAULT_ALIGNER_MODEL,
            forced_aligner_kwargs={
                "dtype": dtype,
                "device_map": device_map,
                "cache_dir": str(self.cache_dir),
            },
            max_inference_batch_size=1,
            max_new_tokens=1024,
        )

    def transcribe_chunk(self, audio: np.ndarray, *, language: str | None = None) -> TranscriptionChunk:
        self.load()
        assert self._model is not None
        result = self._model.transcribe(
            audio=(audio, 16_000),
            language=None if language in (None, "auto") else language,
            return_time_stamps=True,
        )[0]
        alignment = []
        timestamps = getattr(result, "time_stamps", None)
        if timestamps is not None:
            alignment = list(getattr(timestamps, "items", timestamps) or [])
        return TranscriptionChunk(
            language=str(getattr(result, "language", "") or ""),
            text=str(getattr(result, "text", "") or ""),
            alignment_items=alignment,
        )
