"""The evidence contract, as plain code. No model is involved.

Rules:
- A claim must name a source URL the agent actually fetched in this run.
- Its quote must be a substring of that page's stored text. Either byte-for-byte
  ("exact"), or after whitespace normalisation ("whitespace_normalized"): runs of any
  Unicode whitespace become one space, ends are trimmed, and zero-width characters and
  soft hyphens are removed, on both sides.
- Case is never folded. Punctuation and spelling are never altered. No ellipses, no
  paraphrase, no fuzzy match.
- A quote shorter than MIN_QUOTE_CHARS is rejected, because it proves nothing.
- Each number in the claim must also occur in the quote.

What this does not prove: that the quote logically supports the claim, or that the
page itself is true. It proves the words were on the page that was fetched.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .extract import sha256_text

MIN_QUOTE_CHARS = 12
INVISIBLE = {"​", "‌", "‍", "⁠", "﻿", "­"}
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass
class Verdict:
    verified: bool
    match: str  # exact | whitespace_normalized | none
    reason: str  # ok | empty_quote | quote_too_short | source_not_fetched | quote_not_found | number_not_in_quote | snapshot_hash_mismatch
    start: int | None = None
    end: int | None = None
    snapshot_sha256: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Normalised text, plus for each normalised character its original index."""
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


def _numbers(text: str) -> set[str]:
    return {match.group().replace(",", "").rstrip(".") for match in NUMBER.finditer(text)}


def verify_quote(quote: str, page_text: str) -> Verdict:
    """Check one quote against one stored page text."""
    if not isinstance(quote, str) or not quote.strip():
        return Verdict(False, "none", "empty_quote")
    position = page_text.find(quote)
    normal_quote = normalize(quote)
    if len(normal_quote) < MIN_QUOTE_CHARS:
        return Verdict(False, "none", "quote_too_short")
    if position >= 0:
        return Verdict(True, "exact", "ok", position, position + len(quote))
    normal_page, index = normalize_with_map(page_text)
    found = normal_page.find(normal_quote)
    if found < 0:
        return Verdict(False, "none", "quote_not_found")
    return Verdict(True, "whitespace_normalized", "ok", index[found], index[found + len(normal_quote) - 1] + 1)


def verify_claim(claim_text: str, quote: str, source_url: str, snapshots: dict) -> Verdict:
    """snapshots maps URL (requested and final) to an object with .text and .sha256."""
    snapshot = snapshots.get(source_url)
    if snapshot is None:
        return Verdict(False, "none", "source_not_fetched")
    if sha256_text(snapshot.text) != snapshot.sha256:
        return Verdict(False, "none", "snapshot_hash_mismatch", snapshot_sha256=snapshot.sha256)
    verdict = verify_quote(quote, snapshot.text)
    verdict.snapshot_sha256 = snapshot.sha256
    if verdict.verified and not _numbers(claim_text or "") <= _numbers(quote):
        return Verdict(False, "none", "number_not_in_quote", snapshot_sha256=snapshot.sha256)
    return verdict
