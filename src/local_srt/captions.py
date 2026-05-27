from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Protocol

from .srt import Subtitle

SENTENCE_END_PUNCT = set("\u3002\uff01\uff1f.!?")
CLAUSE_PUNCT = SENTENCE_END_PUNCT | set("\uff0c\u3001\uff1b\uff1a,;:")
LATIN_RE = re.compile(r"[A-Za-z0-9]")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WORD_START_MARKERS = ("\u2581", "\u0120")
NO_SPACE_BEFORE = set(".,!?;:%)]}\u3002\uff0c\u3001\uff01\uff1f\uff1b\uff1a")
NO_SPACE_AFTER = set("([{")
ASCII_SPACE_AFTER = set(".,!?;:")
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
COMMON_ENGLISH_JOIN_FIXES = {
    "anybody",
    "anyone",
    "anything",
    "because",
    "cannot",
    "everybody",
    "everyone",
    "everything",
    "forever",
    "maybe",
    "nobody",
    "nothing",
    "outside",
    "someone",
    "something",
    "sometimes",
    "today",
    "together",
    "tomorrow",
    "tonight",
    "whatever",
    "whenever",
    "wherever",
    "without",
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
    return bool(text) and all(ch in CLAUSE_PUNCT for ch in text)


def _clean_token(token: str) -> tuple[str, bool]:
    token = token.strip()
    force_space = token.startswith(WORD_START_MARKERS)
    for marker in WORD_START_MARKERS:
        token = token.replace(marker, " ")
    token = " ".join(token.split())
    return token, force_space


@lru_cache(maxsize=4096)
def _word_frequency(text: str, language: str) -> float:
    try:
        from wordfreq import zipf_frequency
    except Exception:
        return 0.0
    return float(zipf_frequency(text, language))


def _last_latin_word(text: str) -> str:
    match = re.search(r"[A-Za-z0-9]+$", text)
    return match.group(0) if match else ""


def _should_join_english_fragments(left_word: str, token: str) -> bool:
    right_match = re.match(r"[A-Za-z0-9]+$", token)
    if not left_word or not right_match:
        return False
    right_word = right_match.group(0)
    joined = f"{left_word}{right_word}".lower()
    if joined in COMMON_ENGLISH_JOIN_FIXES:
        return True
    if len(left_word) <= 1 or len(right_word) <= 1:
        return False
    joined_freq = _word_frequency(joined, "en")
    split_freq = _word_frequency(f"{left_word} {right_word}".lower(), "en")
    return joined_freq >= 3.4 and joined_freq >= split_freq + 0.8


def _needs_space(output: str, token: str, *, force_space: bool) -> bool:
    if not output or not token:
        return False
    if force_space:
        return True
    if token[0] in NO_SPACE_BEFORE or token in CONTRACTION_PARTS:
        return False
    if output[-1] in NO_SPACE_AFTER:
        return False
    current_latin = _contains_latin(token[0])
    if output[-1] in ASCII_SPACE_AFTER and current_latin:
        return True
    previous_latin = _contains_latin(output[-1])
    if previous_latin and current_latin:
        return not _should_join_english_fragments(_last_latin_word(output), token)
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


def _over_natural_limit(tokens: list[str], max_words: int, max_zh_chars: int) -> bool:
    text = _join_tokens(tokens)
    if _contains_latin(text):
        return len(tokens) >= max_words
    return len(text) >= max_zh_chars


def _over_hard_limit(tokens: list[str], max_words: int, max_zh_chars: int) -> bool:
    text = _join_tokens(tokens)
    if _contains_latin(text):
        return len(tokens) >= max_words + 5
    return len(text) > max_zh_chars


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
        return _should_join_english_fragments(_last_latin_word(left_text), next_token)
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
        return bool(current) and len(tokens) >= max_words
    return bool(current) and len(candidate) > max_zh_chars


def build_natural_captions(
    alignment_items: Iterable[AlignmentItem],
    *,
    offset_seconds: float = 0.0,
    script: str = "traditional",
    max_words: int = 9,
    max_zh_chars: int = 15,
    max_pause_seconds: float = 0.45,
    hard_pause_seconds: float = 1.0,
) -> list[Subtitle]:
    items = list(alignment_items)
    subtitles: list[Subtitle] = []
    tokens: list[str] = []
    start: float | None = None
    end: float | None = None

    def flush() -> None:
        nonlocal tokens, start, end
        text = convert_chinese(_join_tokens(tokens), script)
        if start is not None and end is not None and text:
            subtitles.append(Subtitle(start + offset_seconds, end + offset_seconds, text))
        tokens = []
        start = None
        end = None

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
            flush()

        if tokens and _would_exceed_limit(tokens, text, max_words, max_zh_chars) and not _unsafe_boundary(tokens, text):
            flush()

        if start is None:
            start = float(item.start_time)
        end = float(item.end_time)
        tokens.append(text)

        text_has_sentence_end = any(ch in SENTENCE_END_PUNCT for ch in text)
        text_has_clause_punct = any(ch in CLAUSE_PUNCT for ch in text)
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
        should_flush = (
            text_has_sentence_end
            or (text_has_clause_punct and over_soft_limit)
            or has_hard_pause
            or (has_pause and (over_soft_limit or _contains_cjk(caption_text)))
            or over_hard_limit
        )

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
