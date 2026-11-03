"""BM25 over page chunks, own implementation, standard library only. Persisted as plain JSON."""

from __future__ import annotations

import math
from collections import Counter

from .textscore import terms

K1 = 1.5
B = 0.75
CHUNK_CHARS = 1200


def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Line-aligned chunks. A line longer than size is cut, since minified pages have those."""
    chunks: list[str] = []
    current: list[str] = []
    used = 0
    for line in text.split("\n"):
        while len(line) > size:
            if current:
                chunks.append("\n".join(current))
                current, used = [], 0
            chunks.append(line[:size])
            line = line[size:]
        if used + len(line) + 1 > size and current:
            chunks.append("\n".join(current))
            current, used = [], 0
        current.append(line)
        used += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return [chunk for chunk in chunks if chunk.strip()]


def build(pages: list[dict]) -> dict:
    """pages: dicts with ref, title and text. The title and path also count as chunk terms."""
    postings: dict[str, list[list[int]]] = {}
    chunk_refs: list[int] = []
    lengths: list[int] = []
    refs = [page["ref"] for page in pages]
    for page_number, page in enumerate(pages):
        heading = f"{page.get('title', '')} {page['ref'].replace('/', ' ').replace('-', ' ').replace('_', ' ')}"
        for chunk in chunk_text(page["text"]):
            counts = Counter(terms(f"{heading}\n{chunk}"))
            chunk_id = len(chunk_refs)
            chunk_refs.append(page_number)
            lengths.append(sum(counts.values()))
            for term, count in counts.items():
                postings.setdefault(term, []).append([chunk_id, count])
    return {"refs": refs, "chunk_pages": chunk_refs, "lengths": lengths, "postings": postings}


def search(index: dict, query: str, limit: int = 20) -> list[tuple[str, float]]:
    """Pages by their best chunk's score, highest first. Ties break on ref, so order is stable."""
    lengths = index["lengths"]
    total = len(lengths)
    if not total:
        return []
    average = sum(lengths) / total
    scores: dict[int, float] = {}
    for term in set(terms(query)):
        posting = index["postings"].get(term)
        if not posting:
            continue
        weight = math.log(1 + (total - len(posting) + 0.5) / (len(posting) + 0.5))
        for chunk_id, count in posting:
            scale = K1 * (1 - B + B * lengths[chunk_id] / (average or 1))
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight * count * (K1 + 1) / (count + scale)
    best: dict[str, float] = {}
    for chunk_id, score in scores.items():
        ref = index["refs"][index["chunk_pages"][chunk_id]]
        best[ref] = max(best.get(ref, 0.0), score)
    return sorted(best.items(), key=lambda item: (-item[1], item[0]))[:limit]
