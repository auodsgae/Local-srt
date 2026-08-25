from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from .captions import SimpleAlignmentItem, build_natural_captions, convert_chinese
from .config import MAX_ALIGN_CHUNK_SECONDS, SAMPLE_RATE
from .media import chunk_audio, decode_to_pcm16k
from .qwen_backend import QwenBackend
from .srt import Subtitle, write_srt

ProgressCallback = Callable[[dict], None]


def _emit_progress(
    emit: ProgressCallback,
    input_path: Path,
    stage: str,
    *,
    percent: int | None = None,
    **details: object,
) -> None:
    event: dict[str, object] = {
        "type": "progress",
        "file": str(input_path),
        "mode": "indeterminate" if percent is None else "determinate",
        "stage": stage,
        **details,
    }
    if percent is not None:
        event["percent"] = max(0, min(100, percent))
    emit(event)


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
    _emit_progress(emit, input_path, "decoding media")
    audio, duration = decode_to_pcm16k(input_path)
    _emit_progress(emit, input_path, "preparing audio chunks")
    chunks = chunk_audio(audio, MAX_ALIGN_CHUNK_SECONDS)
    if not chunks:
        raise RuntimeError("No audio samples were decoded from the input file.")

    backend = QwenBackend(model_size=model_size, device=device, progress=emit)
    _emit_progress(emit, input_path, "loading transcription model")
    backend.load()

    subtitles: list[Subtitle] = []
    completed_samples = 0
    total_samples = len(audio)
    for index, (offset, chunk) in enumerate(chunks, 1):
        completed_percent = min(100, int((completed_samples / total_samples) * 100))
        if len(chunks) == 1:
            _emit_progress(emit, input_path, "transcribing audio")
        else:
            _emit_progress(
                emit,
                input_path,
                f"transcribing chunk {index}/{len(chunks)}",
                percent=completed_percent,
            )
        result = backend.transcribe_chunk(chunk, language=language)
        if len(chunks) == 1:
            _emit_progress(emit, input_path, "building captions")
        else:
            _emit_progress(
                emit,
                input_path,
                f"building captions for chunk {index}/{len(chunks)}",
                percent=completed_percent,
            )
        if result.alignment_items and caption_style == "natural":
            subtitles.extend(
                build_natural_captions(
                    result.alignment_items,
                    transcript_text=result.text,
                    offset_seconds=offset,
                    script=script,
                )
            )
        elif result.text.strip():
            subtitles.extend(_fallback_caption(result.text, offset, offset + len(chunk) / SAMPLE_RATE, script))
        completed_samples += len(chunk)
        completed_percent = min(100, int((completed_samples / total_samples) * 100))
        _emit_progress(
            emit,
            input_path,
            f"processed chunk {index}/{len(chunks)}",
            percent=completed_percent,
            completed_audio_seconds=completed_samples / SAMPLE_RATE,
            total_audio_seconds=total_samples / SAMPLE_RATE,
        )

    if not subtitles:
        raise RuntimeError("No speech text was detected.")

    _emit_progress(emit, input_path, "writing SRT", percent=100)
    write_srt(output_path, subtitles)
    _emit_progress(emit, input_path, "done", percent=100)
    return output_path, time.perf_counter() - started


def transcript_to_subtitles_for_tests(items: list[tuple[str, float, float]], offset: float = 0.0) -> list[Subtitle]:
    align = [SimpleAlignmentItem(text=t, start_time=s, end_time=e) for t, s, e in items]
    return build_natural_captions(align, offset_seconds=offset, script="preserve")
