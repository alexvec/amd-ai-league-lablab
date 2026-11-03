"""Keyword scoring shared by the extractive backend and the LLM link and text selection."""

from __future__ import annotations

import math
import re

STOPWORDS = set(
    """a about above after again all also am an and any are as at be because been before being below between both but by
    can could did do does doing done down during each few find for from further get give had has have having he her here
    hers him his how i if in into is it its itself just me more most my no nor not of off on once only or other our out
    over own please same she should show so some such tell than that the their them then there these they this those
    through to too under until up us very was we were what when where which while who whom whose why will with would you
    your""".split()
)
WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
SPLIT = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[^\W_a-z])", re.UNICODE)
ABBREVIATION = re.compile(r"(?:\b(?:e\.g|i\.e|etc|vs|cf|al|Dr|Mr|Mrs|Ms|Prof|St|No|Fig|Inc|Ltd|Jr|Sr)\.|\b[A-Z]\.)$")


def stem(word: str) -> str:
    word = word.lower().replace("’", "'")
    if word.endswith("'s"):
        word = word[:-2]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith(("ing", "ed")):
        return word[:-3] if word.endswith("ing") else word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def terms(text: str) -> list[str]:
    """Stemmed content words, stopwords removed."""
    return [stem(w) for w in WORD.findall(text) if w.lower() not in STOPWORDS]


def split_sentences(text: str) -> list[str]:
    """Sentences as exact slices of the input lines, so a quote is verbatim by construction."""
    sentences: list[str] = []
    for line in text.split("\n"):
        start = 0
        pieces = []
        for match in SPLIT.finditer(line):
            candidate = line[start : match.start()]
            if ABBREVIATION.search(candidate.rstrip("\"'”’)]")) or not candidate.strip():
                continue
            pieces.append(line[start:match.start()])
            start = match.end()
        pieces.append(line[start:])
        sentences.extend(piece.strip() for piece in pieces if piece.strip())
    return sentences


def idf_table(documents: list[set[str]]) -> dict[str, float]:
    total = len(documents)
    counts: dict[str, int] = {}
    for document in documents:
        for term in document:
            counts[term] = counts.get(term, 0) + 1
    return {term: math.log(1 + total / count) for term, count in counts.items()}


def link_score(question_terms: set[str], anchor: str, url_path: str) -> float:
    anchor_terms = set(terms(anchor))
    path_terms = set(terms(re.sub(r"[/_\-.+%]", " ", url_path)))
    return len(question_terms & anchor_terms) + 0.5 * len(question_terms & path_terms)


def relevant_text(text: str, question: str, budget: int) -> str:
    """Most relevant lines of a long page, in page order, up to budget characters."""
    if len(text) <= budget:
        return text
    wanted = set(terms(question))
    lines = text.split("\n")
    ranked = sorted(range(len(lines)), key=lambda i: (-len(wanted & set(terms(lines[i]))), i))
    chosen: set[int] = set()
    used = 0
    for index in ranked:
        if used + len(lines[index]) + 1 > budget:
            continue
        chosen.add(index)
        used += len(lines[index]) + 1
    return "\n".join(lines[i] for i in sorted(chosen))
