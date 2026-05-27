from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Subtitle:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def normalize_subtitles(items: list[Subtitle]) -> list[Subtitle]:
    normalized: list[Subtitle] = []
    previous_end = 0.0
    for item in items:
        text = item.text.strip()
        if not text:
            continue
        start = max(0.0, item.start)
        end = max(start + 0.05, item.end)
        if normalized and start < previous_end:
            start = previous_end
            end = max(start + 0.05, end)
        normalized.append(Subtitle(start=start, end=end, text=text))
        previous_end = end
    return normalized


def render_srt(items: list[Subtitle]) -> str:
    blocks = []
    for index, item in enumerate(normalize_subtitles(items), 1):
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(item.start)} --> {format_timestamp(item.end)}\n"
            f"{item.text}\n"
        )
    return "\n".join(blocks) + ("\n" if blocks else "")


def write_srt(path: Path, items: list[Subtitle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_srt(items), encoding="utf-8")

