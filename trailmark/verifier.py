"""Span and value checks, as plain code. No model is involved.

A candidate answer names evidence spans. Here a span must occur in the stored text of the page
it names (exact first, then with whitespace and case normalised), and the value must occur in a
span on token boundaries, so 94 is not found inside 194.

What this does not prove: that the page is true, or that the span means what the model thinks it
means. It proves the words were on a page stored at index time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MIN_SPAN_CHARS = 8
INVISIBLE = {"​", "‌", "‍", "⁠", "﻿", "­"}
IDENTIFIER = re.compile(r"(?<![\w.-])(?=[\w-]*[A-Za-z])(?=[\w-]*\d)[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*(?![\w-])")
# Text aimed at the model rather than at a reader. A page saying this is not evidence of anything.
INJECTION = re.compile(
    r"(?i)(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all)\b.{0,30}\b(instruction|prompt|rule|message)"
    r"|\b(system prompt|you are now|new instructions)\b"
    r"|\b(answer|respond|reply|output|say)\s+(with|only with)\b"
)


@dataclass(frozen=True)
class SpanVerdict:
    ok: bool
    match: str  # exact | normalized | none
    reason: str  # ok | empty_span | span_too_short | span_not_found
    start: int | None = None
    end: int | None = None


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-normalised text, plus each normalised character's original index."""
    out: list[str] = []
    index: list[int] = []
    pending_space = -1
    for position, char in enumerate(text):
        if char in INVISIBLE:
            continue
        if char.isspace():
            if pending_space < 0:
                pending_space = position
            continue
        if pending_space >= 0 and out:
            out.append(" ")
            index.append(pending_space)
        pending_space = -1
        out.append(char)
        index.append(position)
    return "".join(out), index


def normalize(text: str) -> str:
    return normalize_with_map(text)[0]


def _lower_with_map(text: str, index: list[int]) -> tuple[str, list[int]]:
    """casefold can change length (ß to ss), so the position map is rebuilt alongside it."""
    out: list[str] = []
    mapped: list[int] = []
    for char, position in zip(text, index):
        folded = char.casefold()
        out.append(folded)
        mapped.extend([position] * len(folded))
    return "".join(out), mapped


def verify_span(span: str, page_text: str) -> SpanVerdict:
    """Check one span against one page's stored text."""
    if not isinstance(span, str) or not span.strip():
        return SpanVerdict(False, "none", "empty_span")
    plain = normalize(span)
    if len(plain) < MIN_SPAN_CHARS:
        return SpanVerdict(False, "none", "span_too_short")
    position = page_text.find(span)
    if position >= 0:
        return SpanVerdict(True, "exact", "ok", position, position + len(span))
    page, index = normalize_with_map(page_text)
    page, index = _lower_with_map(page, index)
    found = page.find(plain.casefold())
    if found < 0:
        return SpanVerdict(False, "none", "span_not_found")
    return SpanVerdict(True, "normalized", "ok", index[found], index[found + len(plain.casefold()) - 1] + 1)


def value_in_text(value: str, text: str) -> bool:
    """The value occurs on token boundaries, ignoring case and whitespace differences."""
    needle, haystack = normalize(value).casefold(), normalize(text).casefold()
    if not needle:
        return False
    pattern = rf"(?<![\w.]){re.escape(needle)}(?![\w]|\.\d)"
    # 1200 and 1,200 are the same value.
    return re.search(pattern, haystack) is not None or re.search(pattern, re.sub(r"(?<=\d),(?=\d{3})", "", haystack)) is not None


def identifiers(text: str) -> set[str]:
    """Tokens mixing letters and digits (K7, HV-3310, AX-220), case folded."""
    return {match.group().casefold() for match in IDENTIFIER.finditer(text or "")}


def enclosing_line(page_text: str, start: int, end: int) -> str:
    """The stored line or lines a verified span sits on."""
    left = page_text.rfind("\n", 0, start) + 1
    right = page_text.find("\n", end)
    return page_text[left : right if right >= 0 else len(page_text)]


def looks_like_injection(text: str) -> bool:
    return INJECTION.search(text or "") is not None


def _family(identifier: str) -> str:
    return re.match(r"[a-z]*", identifier).group()


def wrong_row(question: str, line: str) -> bool:
    """A span on a table row or labelled line about a sibling of the thing asked about.

    The question names K7 and the line names K5 but not K7: same family, different item. This is
    the near-miss row. Lines naming no identifier of that family are left alone.
    """
    asked = identifiers(question)
    if not asked:
        return False
    found = identifiers(line)
    if asked & found:
        return False
    families = {_family(item) for item in asked if _family(item)}
    return any(_family(item) in families for item in found)


def subject_missing(question: str, page_texts: list[str], value: str = "") -> bool:
    """An identifier in the question appears on none of the evidence pages.

    The K11 question answered from the K7 page is rejected here. It catches a model filling a gap
    from a page about something else, and does nothing for questions that name no identifier.
    """
    combined = " ".join(page_texts)
    found = identifiers(combined)
    folded = normalize(combined).casefold()
    for item in identifiers(question) - identifiers(value):
        if item not in found and item not in folded:
            return True
    return False
