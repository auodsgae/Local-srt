from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Protocol

from .srt import Subtitle

SENTENCE_END_PUNCT = set("\u3002\uff01\uff1f.!?\u2026")
CLAUSE_PUNCT = SENTENCE_END_PUNCT | set("\uff0c\u3001\uff1b\uff1a,;:")
CLAUSE_BREAK_PUNCT = CLAUSE_PUNCT - SENTENCE_END_PUNCT
LATIN_RE = re.compile(r"[A-Za-z0-9]")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)*")
WORD_START_MARKERS = ("\u2581", "\u0120")
NO_SPACE_BEFORE = set(".,!?;:%)]}\u3002\uff0c\u3001\uff01\uff1f\uff1b\uff1a\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u2019\u201d")
NO_SPACE_AFTER = set("([{\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u2018\u201c")
TRAILING_CLOSERS = set(")]}\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u2019\u201d\"'")
ASCII_SPACE_AFTER = set(".,!?;:")
DISPLAY_REMOVE_PUNCT = set(".\u3002!\uff01?\uff1f\u2026")
DISPLAY_SPACE_PUNCT = set(",\uff0c\u3001;\uff1b:\uff1a")
INTERNAL_WORD_PUNCT = set("'-\u2019")
MIN_CLAUSE_UNITS = 5
CONTRACTION_PARTS = {
    "'m",
    "'re",
    "'ve",
    "'ll",
    "'d",
    "'s",
    "n't",
    "\u2019m",
    "\u2019re",
    "\u2019ve",
    "\u2019ll",
    "\u2019d",
    "\u2019s",
    "n\u2019t",
}
COMMON_CJK_BOUNDARY_WORDS = {
    "\u4e00\u8d77",
    "\u4e0d\u6703",
    "\u4e0d\u8981",
    "\u4e0d\u904e",
    "\u4e16\u754c",
    "\u4eca\u5929",
    "\u4ed6\u5011",
    "\u4ee5\u5f8c",
    "\u4ee5\u70ba",
    "\u4f46\u662f",
    "\u4f60\u5011",
    "\u5148\u751f",
    "\u53f0\u5317",
    "\u53f0\u7063",
    "\u56e0\u70ba",
    "\u5982\u679c",
    "\u5b78\u751f",
    "\u5c0f\u6642",
    "\u5c31\u662f",
    "\u5de5\u4f5c",
    "\u5df2\u7d93",
    "\u6211\u5011",
    "\u6240\u4ee5",
    "\u660e\u5929",
    "\u6642\u5019",
    "\u670b\u53cb",
    "\u73fe\u5728",
    "\u771f\u7684",
    "\u77e5\u9053",
    "\u800c\u4e14",
    "\u81ea\u5df1",
    "\u9019\u500b",
    "\u9019\u6a23",
    "\u7136\u5f8c",
    "\u7b49\u4e00\u4e0b",
    "\u7d50\u679c",
    "\u88e1\u9762",
    "\u8eca\u7ad9",
    "\u6e38\u620f",
    "\u904a\u6232",
    "\u9019\u88e1",
    "\u90a3\u500b",
    "\u90a3\u88e1",
    "\u975e\u5e38",
}


class AlignmentItem(Protocol):
    text: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class SimpleAlignmentItem:
    text: str
    start_time: float
    end_time: float


def convert_chinese(text: str, script: str) -> str:
    if script == "preserve":
        return text
    config = "s2twp" if script == "traditional" else "t2s"
    try:
        from opencc import OpenCC
    except Exception:
        return text
    return OpenCC(config).convert(text)


def _contains_latin(text: str) -> bool:
    return bool(LATIN_RE.search(text))


def _contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def _is_cjk_char(text: str) -> bool:
    return len(text) == 1 and _contains_cjk(text)


def _is_punctuation_only(text: str) -> bool:
    text, _force_space = _clean_token(text)
    return bool(text) and not any(_is_aligner_character(ch) for ch in text)


def _ends_with_punctuation(text: str, punctuation: set[str]) -> bool:
    text = text.rstrip()
    while text and text[-1] in TRAILING_CLOSERS:
        text = text[:-1].rstrip()
    return bool(text) and text[-1] in punctuation


def _clean_token(token: str) -> tuple[str, bool]:
    token = token.strip()
    force_space = token.startswith(WORD_START_MARKERS)
    for marker in WORD_START_MARKERS:
        token = token.replace(marker, " ")
    token = " ".join(token.split())
    return token, force_space


def _clean_caption_text(text: str) -> str:
    """Remove display punctuation while preserving readable word separators."""
    output: list[str] = []
    for index, char in enumerate(text):
        previous_char = text[index - 1] if index else ""
        next_char = text[index + 1] if index + 1 < len(text) else ""
        inside_word = (
            char in INTERNAL_WORD_PUNCT
            and previous_char.isalnum()
            and next_char.isalnum()
        )
        if inside_word:
            output.append(char)
        elif char in DISPLAY_REMOVE_PUNCT:
            continue
        elif char in DISPLAY_SPACE_PUNCT or unicodedata.category(char).startswith("P"):
            output.append(" ")
        else:
            output.append(char)
    return " ".join("".join(output).split())


def _is_aligner_character(ch: str) -> bool:
    """Match the character filtering used by Qwen's forced aligner."""
    return ch == "'" or unicodedata.category(ch).startswith(("L", "N"))


def _aligner_key(text: str) -> list[str]:
    return [ch.lower() for ch in text if _is_aligner_character(ch)]


def _gap_items(text: str, timestamp: float) -> tuple[list[SimpleAlignmentItem], bool]:
    """Turn transcript punctuation into zero-duration aligned items."""
    items: list[SimpleAlignmentItem] = []
    token = ""
    space_before = False

    def flush() -> None:
        nonlocal token, space_before
        if token:
            prefix = WORD_START_MARKERS[0] if space_before else ""
            items.append(SimpleAlignmentItem(prefix + token, timestamp, timestamp))
            token = ""
            space_before = False

    for char in text:
        if char.isspace():
            flush()
            space_before = True
        elif not _is_aligner_character(char):
            token += char
    flush()
    return items, space_before


def restore_transcript_formatting(
    alignment_items: Iterable[AlignmentItem], transcript_text: str
) -> list[SimpleAlignmentItem]:
    """Restore punctuation and explicit spaces removed by the forced aligner."""
    items = list(alignment_items)

    def copy_items() -> list[SimpleAlignmentItem]:
        return [
            SimpleAlignmentItem(str(item.text), float(item.start_time), float(item.end_time))
            for item in items
        ]

    if not items or not transcript_text:
        return copy_items()

    item_keys = [_aligner_key(str(item.text)) for item in items]
    if any(not key for key in item_keys):
        return copy_items()

    source = [
        (index, char.lower())
        for index, char in enumerate(transcript_text)
        if _is_aligner_character(char)
    ]
    if [char for _index, char in source] != [
        char for key in item_keys for char in key
    ]:
        return copy_items()

    matches: list[tuple[int, int]] = []
    source_cursor = 0
    for key in item_keys:
        raw_start = source[source_cursor][0]
        raw_end = source[source_cursor + len(key) - 1][0] + 1
        matches.append((raw_start, raw_end))
        source_cursor += len(key)

    restored: list[SimpleAlignmentItem] = []
    raw_cursor = 0
    previous_end = float(items[0].start_time)
    for item, (raw_start, raw_end) in zip(items, matches):
        punctuation, trailing_space = _gap_items(transcript_text[raw_cursor:raw_start], previous_end)
        restored.extend(punctuation)
        # Use the original ASR spelling so punctuation inside an aligned word
        # (for example, hyphens or curly apostrophes) is not lost.
        item_text = transcript_text[raw_start:raw_end]
        if trailing_space:
            item_text = WORD_START_MARKERS[0] + item_text
        restored.append(SimpleAlignmentItem(item_text, float(item.start_time), float(item.end_time)))
        raw_cursor = raw_end
        previous_end = float(item.end_time)

    punctuation, _trailing_space = _gap_items(transcript_text[raw_cursor:], previous_end)
    restored.extend(punctuation)
    return restored


@lru_cache(maxsize=4096)
def _word_frequency(text: str, language: str) -> float:
    try:
        from wordfreq import zipf_frequency
    except Exception:
        return 0.0
    return float(zipf_frequency(text, language))


def _needs_space(output: str, token: str, *, force_space: bool) -> bool:
    if not output or not token:
        return False
    if token[0] in NO_SPACE_BEFORE or token in CONTRACTION_PARTS:
        return False
    if output[-1] in NO_SPACE_AFTER:
        return False
    if force_space:
        return True
    current_latin = _contains_latin(token[0])
    if output[-1] in ASCII_SPACE_AFTER and current_latin:
        return True
    previous_latin = _contains_latin(output[-1])
    if _contains_cjk(output[-1]) and current_latin:
        return True
    if previous_latin and _contains_cjk(token[0]):
        return True
    if previous_latin and current_latin:
        return True
    return False


def _join_tokens(tokens: list[str]) -> str:
    if not tokens:
        return ""
    output = ""
    for token in tokens:
        token, force_space = _clean_token(token)
        if not token:
            continue
        if _needs_space(output, token, force_space=force_space):
            output += " "
        output += token
    return output.strip()


def _content_unit_count(text: str) -> int:
    return len(LATIN_WORD_RE.findall(text)) + len(CJK_RE.findall(text))


def _over_natural_limit(tokens: list[str], max_words: int, max_zh_chars: int) -> bool:
    text = _join_tokens(tokens)
    if _contains_latin(text):
        return _content_unit_count(text) >= max_words
    # Clause punctuation contributes to the soft limit so a nearby comma can
    # rebalance text at the existing time block before the line grows too long.
    return len(text) >= max_zh_chars


def _over_hard_limit(tokens: list[str], max_words: int, max_zh_chars: int) -> bool:
    text = _join_tokens(tokens)
    if _contains_latin(text):
        return _content_unit_count(text) > max_words + 5
    return len(CJK_RE.findall(text)) > max_zh_chars


def _cjk_chars_near_boundary(left_text: str, right_text: str) -> tuple[str, str]:
    left_chars = "".join(ch for ch in left_text if _is_cjk_char(ch))[-8:]
    right_chars = "".join(ch for ch in right_text if _is_cjk_char(ch))[:8]
    return left_chars, right_chars


@lru_cache(maxsize=4096)
def _jieba_boundary_inside_word(left_chars: str, right_chars: str) -> bool:
    if not left_chars or not right_chars:
        return False
    context = left_chars + right_chars
    boundary = len(left_chars)
    try:
        import jieba
    except Exception:
        return False
    cursor = 0
    for segment in jieba.cut(context, HMM=True):
        next_cursor = cursor + len(segment)
        if cursor < boundary < next_cursor and len(segment) > 1:
            return True
        cursor = next_cursor
    return False


def _common_cjk_word_crosses_boundary(left_chars: str, right_chars: str) -> bool:
    if not left_chars or not right_chars:
        return False
    for left_size in range(1, min(4, len(left_chars)) + 1):
        for right_size in range(1, min(4, len(right_chars)) + 1):
            candidate = left_chars[-left_size:] + right_chars[:right_size]
            if candidate in COMMON_CJK_BOUNDARY_WORDS:
                return True
            if len(candidate) >= 2 and _word_frequency(candidate, "zh") >= 4.0:
                return True
    return False


def _unsafe_boundary(tokens: list[str], next_text: str) -> bool:
    left_text = _join_tokens(tokens)
    next_token, _force_space = _clean_token(next_text)
    if not left_text or not next_token:
        return False
    if _contains_latin(left_text[-1]) and _contains_latin(next_token[0]):
        return next_token in CONTRACTION_PARTS
    if _contains_cjk(left_text[-1]) and _contains_cjk(next_token[0]):
        left_chars, right_chars = _cjk_chars_near_boundary(left_text, next_token)
        return _common_cjk_word_crosses_boundary(left_chars, right_chars) or _jieba_boundary_inside_word(
            left_chars, right_chars
        )
    return False


def _would_exceed_limit(tokens: list[str], next_text: str, max_words: int, max_zh_chars: int) -> bool:
    next_token, _force_space = _clean_token(next_text)
    if not next_token:
        return False
    current = _join_tokens(tokens)
    candidate = _join_tokens(tokens + [next_token])
    if _contains_latin(candidate):
        return (
            bool(current)
            and _content_unit_count(candidate) > max_words
            and _content_unit_count(candidate) > _content_unit_count(current)
        )
    return (
        bool(current)
        and len(CJK_RE.findall(candidate)) > max_zh_chars
        and len(CJK_RE.findall(candidate)) > len(CJK_RE.findall(current))
    )


def build_natural_captions(
    alignment_items: Iterable[AlignmentItem],
    *,
    transcript_text: str | None = None,
    offset_seconds: float = 0.0,
    script: str = "traditional",
    max_words: int = 9,
    max_zh_chars: int = 15,
    max_pause_seconds: float = 0.45,
    hard_pause_seconds: float = 1.0,
) -> list[Subtitle]:
    raw_items = list(alignment_items)
    items: list[AlignmentItem] = (
        restore_transcript_formatting(raw_items, transcript_text)
        if transcript_text
        else raw_items
    )
    subtitles: list[Subtitle] = []
    tokens: list[str] = []
    start: float | None = None
    end: float | None = None

    def flush() -> None:
        nonlocal tokens, start, end
        text = _clean_caption_text(convert_chinese(_join_tokens(tokens), script))
        if start is not None and end is not None and text:
            subtitles.append(Subtitle(start + offset_seconds, end + offset_seconds, text))
        tokens = []
        start = None
        end = None

    def last_clause_break_index() -> int | None:
        for token_index in range(len(tokens) - 2, -1, -1):
            token, _force_space = _clean_token(tokens[token_index])
            if not _ends_with_punctuation(token, CLAUSE_BREAK_PUNCT):
                continue
            prefix_text = _join_tokens(tokens[: token_index + 1])
            if _content_unit_count(prefix_text) >= MIN_CLAUSE_UNITS:
                return token_index
        return None

    def rebalance_at_clause(boundary_end: float) -> bool:
        nonlocal tokens, start, end
        break_index = last_clause_break_index()
        if break_index is None or start is None:
            return False
        prefix = tokens[: break_index + 1]
        remainder = tokens[break_index + 1 :]
        text = _clean_caption_text(convert_chinese(_join_tokens(prefix), script))
        if not text or not remainder:
            return False
        subtitles.append(
            Subtitle(start + offset_seconds, boundary_end + offset_seconds, text)
        )
        tokens = remainder
        start = boundary_end
        end = boundary_end
        return True

    for index, item in enumerate(items):
        text = str(item.text).strip()
        if not text:
            continue

        next_item = items[index + 1] if index + 1 < len(items) else None
        candidate_tokens = tokens + [text]
        candidate_text = _join_tokens(candidate_tokens)
        if (
            tokens
            and next_item is not None
            and not _contains_latin(candidate_text)
            and len(candidate_text) >= max_zh_chars
            and _unsafe_boundary(candidate_tokens, str(next_item.text))
            and not _unsafe_boundary(tokens, text)
        ):
            if not rebalance_at_clause(float(item.start_time)):
                flush()

        if tokens and _would_exceed_limit(tokens, text, max_words, max_zh_chars) and not _unsafe_boundary(tokens, text):
            flush()

        if start is None:
            start = float(item.start_time)
        end = float(item.end_time)
        tokens.append(text)

        next_gap = (
            max(0.0, float(next_item.start_time) - float(item.end_time))
            if next_item is not None
            else 0.0
        )
        over_soft_limit = _over_natural_limit(tokens, max_words, max_zh_chars)
        over_hard_limit = _over_hard_limit(tokens, max_words, max_zh_chars)
        has_pause = next_item is not None and next_gap >= max_pause_seconds
        has_hard_pause = next_item is not None and next_gap >= hard_pause_seconds
        caption_text = _join_tokens(tokens)
        text_has_sentence_end = _ends_with_punctuation(
            caption_text, SENTENCE_END_PUNCT
        )
        text_has_clause_punct = _ends_with_punctuation(caption_text, CLAUSE_PUNCT)

        if over_soft_limit and not text_has_sentence_end and rebalance_at_clause(float(item.end_time)):
            continue

        should_flush = (
            text_has_sentence_end
            or (text_has_clause_punct and over_soft_limit)
            or has_hard_pause
            or (has_pause and (over_soft_limit or _contains_cjk(caption_text)))
            or over_hard_limit
        )

        if should_flush and next_item is not None and _is_punctuation_only(str(next_item.text)):
            continue
        if (
            should_flush
            and not has_hard_pause
            and next_item is not None
            and not over_hard_limit
            and _unsafe_boundary(tokens, str(next_item.text))
        ):
            continue
        if should_flush:
            flush()

    flush()
    return subtitles
