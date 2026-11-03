"""Real, deterministic, non-LLM backend.

Fetches pages, follows links scored by keyword overlap with the question, and quotes the
best-matching sentences verbatim. It reads no meaning into text: it can return a sentence
that shares the question's words and does not answer it. It has no failure of its own
for the verifier to catch, since quotes are cut directly from stored text.
"""

from __future__ import annotations

import heapq
from urllib.parse import urlsplit

from . import textscore
from .agent import Draft, Session, same_site
from .config import BACKEND_EXTRACTIVE

SKIP_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".gz", ".mp4", ".mp3", ".webp", ".css", ".js", ".ico")
GOOD_ENOUGH = 0.8
MIN_SCORE = 0.3
MAX_CLAIMS = 3
MIN_CHARS, MAX_CHARS = 20, 600


class ExtractiveBackend:
    name = BACKEND_EXTRACTIVE
    model = None

    def investigate(self, session: Session) -> list[Draft]:
        question_terms = set(textscore.terms(session.question))
        seeds = session.seeds()
        frontier: list[tuple[float, int, str, str]] = []
        order = 0
        for seed in seeds:
            order += 1
            heapq.heappush(frontier, (-1000.0, order, seed, "start"))
        visited: set[str] = set()
        visited_snapshots = []
        best = 0.0
        while frontier and session.can_fetch() and best < GOOD_ENOUGH:
            priority, _, url, via = heapq.heappop(frontier)
            if url in visited:
                continue
            visited.add(url)
            if via != "start":
                session.step(type="follow_link", url=url, anchor=via, keyword_overlap=-priority)
            snapshot = session.fetch_page(url)
            if snapshot is None:
                continue
            visited_snapshots.append(snapshot)
            visited.add(snapshot.final_url)
            best = max((item[0] for item in _rank(session.question, visited_snapshots)), default=0.0)
            for link in snapshot.links:
                path = urlsplit(link.url).path.lower()
                if link.url in visited or path.endswith(SKIP_EXTENSIONS) or not same_site(link.url, snapshot.final_url):
                    continue
                score = textscore.link_score(question_terms, link.text, urlsplit(link.url).path)
                if score > 0:
                    order += 1
                    heapq.heappush(frontier, (-score, order, link.url, link.text or link.url))
        ranked = _rank(session.question, visited_snapshots)
        chosen = _select(ranked)
        session.step(
            type="select_sentences",
            method="keyword overlap weighted by rarity",
            candidates=len(ranked),
            chosen=[{"score": round(score, 3), "url": url} for score, url, _ in chosen],
        )
        if not chosen and visited_snapshots:
            session.notes.append("No sentence on the fetched pages matched enough of the question's keywords.")
        if not visited_snapshots and not session.notes:
            session.notes.append("No page could be fetched. See the trace for the reason.")
        return [Draft(sentence, sentence, url) for _, url, sentence in chosen]

    def revise(self, session: Session, failed: list[dict]) -> list[Draft]:
        return []


def _rank(question: str, snapshots: list) -> list[tuple[float, str, str]]:
    wanted = list(dict.fromkeys(textscore.terms(question)))
    if not wanted:
        return []
    rows = []
    for snapshot in snapshots:
        title_terms = set(textscore.terms(snapshot.title))
        for sentence in textscore.split_sentences(snapshot.text):
            if MIN_CHARS <= len(sentence) <= MAX_CHARS:
                rows.append((sentence, snapshot.final_url, set(textscore.terms(sentence)), title_terms))
    if not rows:
        return []
    idf = textscore.idf_table([row[2] for row in rows])
    default = max(idf.values(), default=1.0)
    total = sum(idf.get(term, default) for term in wanted)
    lowered = question.lower().split()
    wants_number = bool(lowered) and (lowered[0] in ("when",) or " ".join(lowered[:2]) in ("how many", "how much", "what year", "how long", "how fast", "how far", "how old"))
    ranked = []
    for sentence, url, sentence_terms, title_terms in rows:
        direct = sum(idf.get(term, default) for term in wanted if term in sentence_terms)
        if direct == 0:
            continue
        # A term in the page title counts for half: the page is about it, the sentence may not repeat it.
        context = sum(0.5 * idf.get(term, default) for term in wanted if term not in sentence_terms and term in title_terms)
        score = (direct + context) / total
        if wants_number and any(ch.isdigit() for ch in sentence):
            score += 0.1
        if sentence[-1] not in ".!?\"'”)":
            score *= 0.7  # headings and table rows
        score *= 1 - min(len(sentence), 600) / 3000  # prefer the tighter of two similar matches
        ranked.append((score, url, sentence))
    ranked.sort(key=lambda item: -item[0])
    return ranked


def _select(ranked: list[tuple[float, str, str]]) -> list[tuple[float, str, str]]:
    chosen: list[tuple[float, str, str]] = []
    for score, url, sentence in ranked:
        if score < MIN_SCORE or (chosen and score < 0.75 * chosen[0][0]):
            break
        words = set(textscore.terms(sentence))
        duplicate = any(len(words & set(textscore.terms(other))) / max(1, len(words | set(textscore.terms(other)))) > 0.7 for _, _, other in chosen)
        if not duplicate:
            chosen.append((score, url, sentence))
        if len(chosen) == MAX_CLAIMS:
            break
    return chosen
