from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from .captions import SimpleAlignmentItem, build_natural_captions, convert_chinese
from .config import MAX_ALIGN_CHUNK_SECONDS
from .media import chunk_audio, decode_to_pcm16k
from .qwen_backend import QwenBackend
from .srt import Subtitle, write_srt

ProgressCallback = Callable[[dict], None]


def _fallback_caption(text: str, start: float, end: float, script: str) -> list[Subtitle]:
    text = convert_chinese(text.strip(), script)
    return [Subtitle(start, end, text)] if text else []


def transcribe_file(
    input_path: Path,
    output_path: Path,
    *,
    language: str = "auto",
    model_size: str = "1.7b",
    device: str = "cuda",
    script: str = "traditional",
    caption_style: str = "natural",
    progress: ProgressCallback | None = None,
) -> tuple[Path, float]:
    emit = progress or (lambda _event: None)
    started = time.perf_counter()
    emit({"type": "status", "message": "Decoding media with ffmpeg"})
    emit({"type": "progress", "file": str(input_path), "percent": 1, "stage": "decoding media"})
    audio, duration = decode_to_pcm16k(input_path)
    emit({"type": "progress", "file": str(input_path), "percent": 4, "stage": "preparing audio chunks"})
    chunks = chunk_audio(audio, MAX_ALIGN_CHUNK_SECONDS)
    if not chunks:
        raise RuntimeError("No audio samples were decoded from the input file.")

    backend = QwenBackend(model_size=model_size, device=device, progress=emit)
    emit({"type": "progress", "file": str(input_path), "percent": 8, "stage": "loading transcription model"})
    backend.load()
    emit({"type": "progress", "file": str(input_path), "percent": 15, "stage": "model ready"})

    subtitles: list[Subtitle] = []
    for index, (offset, chunk) in enumerate(chunks, 1):
        chunk_start = 15 + int(((index - 1) / len(chunks)) * 80)
        chunk_mid = 15 + int(((index - 0.45) / len(chunks)) * 80)
        chunk_done = 15 + int((index / len(chunks)) * 80)
        emit(
            {
                "type": "progress",
                "file": str(input_path),
                "percent": chunk_start,
                "stage": f"transcribing chunk {index}/{len(chunks)}",
            }
        )
        result = backend.transcribe_chunk(chunk, language=language)
        emit(
            {
                "type": "progress",
                "file": str(input_path),
                "percent": min(94, chunk_mid),
                "stage": f"building captions for chunk {index}/{len(chunks)}",
            }
        )
        if result.alignment_items and caption_style == "natural":
            subtitles.extend(build_natural_captions(result.alignment_items, offset_seconds=offset, script=script))
        elif result.text.strip():
            subtitles.extend(_fallback_caption(result.text, offset, offset + len(chunk) / 16_000, script))
        emit(
            {
                "type": "progress",
                "file": str(input_path),
                "percent": min(95, chunk_done),
                "stage": f"finished chunk {index}/{len(chunks)}",
            }
        )

    if not subtitles:
        raise RuntimeError("No speech text was detected.")

    emit({"type": "progress", "file": str(input_path), "percent": 98, "stage": "writing SRT"})
    write_srt(output_path, subtitles)
    emit({"type": "progress", "file": str(input_path), "percent": 100, "stage": "done"})
    return output_path, time.perf_counter() - started


def transcript_to_subtitles_for_tests(items: list[tuple[str, float, float]], offset: float = 0.0) -> list[Subtitle]:
    align = [SimpleAlignmentItem(text=t, start_time=s, end_time=e) for t, s, e in items]
    return build_natural_captions(align, offset_seconds=offset, script="preserve")
