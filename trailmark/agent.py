"""The agent core: one session, a pluggable backend, then the evidence contract.

Backends only draft claims. They cannot mark anything verified. Verified flags are set
here by the verifier, and the final answer is assembled only from claims that passed.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote, urlsplit

from . import gpu as gpu_mod
from . import textscore
from .config import Limits
from .extract import Snapshot, build_snapshot
from .fetcher import Fetcher, FetchError, RobotsDenied
from .netguard import BlockedURL, check_url, resolve_public
from .verifier import verify_claim

SEARCH_ENDPOINT = "https://api.wikimedia.org/core/v1/wikipedia/en/search/page?limit=3&q="
URL_IN_TEXT = re.compile(r"https?://[^\s\"'<>)\]]+")


class StepBudgetExceeded(RuntimeError):
    pass


@dataclass
class Draft:
    claim: str
    quote: str
    source_url: str
    injected_for_demo: bool = False


class Backend(Protocol):
    name: str
    model: str | None

    def investigate(self, session: "Session") -> list[Draft]: ...

    def revise(self, session: "Session", failed: list[dict]) -> list[Draft]: ...


class Session:
    """Holds the budget, the stored snapshots and the trace for one question."""

    def __init__(self, question: str, start_url: str | None, limits: Limits, fetcher_factory=Fetcher):
        self.question = question
        self.start_url = start_url
        self.limits = limits
        self.started = time.monotonic()
        self.deadline = self.started + limits.request_seconds
        self.steps: list[dict] = []
        self.pages: dict[str, Snapshot] = {}
        self.page_count = 0
        self.notes: list[str] = []
        self.tokens = {"prompt": None, "completion": None}
        self.fetcher = fetcher_factory(limits, on_event=self._on_event, deadline=self.deadline)
        self.resolver = self.fetcher.resolver

    def _on_event(self, **fields) -> None:
        self.step(**fields)

    def step(self, **fields) -> None:
        if len(self.steps) >= self.limits.max_steps:
            raise StepBudgetExceeded(f"step limit {self.limits.max_steps} reached")
        fields["n"] = len(self.steps) + 1
        fields["t_ms"] = int((time.monotonic() - self.started) * 1000)
        self.steps.append(fields)

    def time_left(self) -> float:
        return self.deadline - time.monotonic()

    def can_fetch(self) -> bool:
        return self.page_count < self.limits.max_pages and self.time_left() > 1.0

    def fetch_page(self, url: str) -> Snapshot | None:
        """Fetch, store and return a snapshot. Failures become trace steps, not exceptions."""
        if url in self.pages:
            return self.pages[url]
        if not self.can_fetch():
            self.step(type="fetch_skipped", url=url, note="page or time limit reached")
            return None
        self.page_count += 1
        started = time.monotonic()
        try:
            result = self.fetcher.fetch(url)
        except BlockedURL as exc:
            self.step(type="fetch_blocked", url=url, note=str(exc))
            return None
        except RobotsDenied as exc:
            self.step(type="fetch_denied_by_robots", url=url, note=str(exc))
            return None
        except FetchError as exc:
            self.step(type="fetch_failed", url=url, note=str(exc))
            return None
        snapshot = build_snapshot(result, self.limits)
        self.pages[url] = snapshot
        self.pages[snapshot.final_url] = snapshot
        self.step(
            type="fetch",
            url=url,
            final_url=snapshot.final_url,
            status=result.status,
            bytes=len(result.body),
            chars=len(snapshot.text),
            truncated=snapshot.truncated,
            sha256=snapshot.sha256,
            title=snapshot.title,
            ms=int((time.monotonic() - started) * 1000),
        )
        return snapshot

    def seeds(self) -> list[str]:
        """Starting URLs: the given URL, a URL in the question, or a search step."""
        if self.start_url:
            target = check_url(self.start_url)
            resolve_public(target.host, target.port, self.resolver)
            return [target.url]
        found = URL_IN_TEXT.search(self.question)
        if found:
            target = check_url(found.group().rstrip(".,;"))
            resolve_public(target.host, target.port, self.resolver)
            return [target.url]
        return self._search()

    def _search(self) -> list[str]:
        words = [w for w in textscore.WORD.findall(self.question) if w.lower() not in textscore.STOPWORDS]
        query = " ".join(words) or self.question
        url = SEARCH_ENDPOINT + quote(query)
        try:
            result = self.fetcher.fetch(url, accept_types=("application/json",))
            pages = json.loads(result.body.decode("utf-8", "replace")).get("pages", [])
        except (BlockedURL, RobotsDenied, FetchError, ValueError) as exc:
            self.step(type="search_failed", url=url, note=str(exc))
            self.notes.append("No start_url was given and the search step failed.")
            return []
        seeds = [f"https://en.wikipedia.org/wiki/{quote(str(p.get('key', '')))}" for p in pages if p.get("key")]
        self.step(type="search", url=url, provider="Wikimedia search API", query=query, results=seeds)
        return seeds


def same_site(a: str, b: str) -> bool:
    def host(url: str) -> str:
        name = urlsplit(url).hostname or ""
        return name[4:] if name.startswith("www.") else name

    return host(a) == host(b)


def alter_quote(quote_text: str) -> str:
    """Make a quote wrong the way a hallucinating model would: one changed detail."""
    digits = re.search(r"\d", quote_text)
    if digits:
        replacement = str((int(digits.group()) + 1) % 10)
        return quote_text[: digits.start()] + replacement + quote_text[digits.end() :]
    words = list(re.finditer(r"[A-Za-z]{4,}", quote_text))
    if words:
        last = words[-1]
        return quote_text[: last.start()] + "unsupported" + quote_text[last.end() :]
    return quote_text + " (altered)"


def _judge(draft: Draft, pages: dict[str, Snapshot], attempt: int) -> dict:
    verdict = verify_claim(draft.claim, draft.quote, draft.source_url, pages)
    return {
        "claim": draft.claim,
        "quote": draft.quote,
        "source_url": draft.source_url,
        "verified": verdict.verified,
        "match": verdict.match,
        "reason": verdict.reason,
        "start": verdict.start,
        "end": verdict.end,
        "snapshot_sha256": verdict.snapshot_sha256,
        "in_answer": verdict.verified,
        "injected_for_demo": draft.injected_for_demo,
        "attempt": attempt,
    }


def assemble(claims: list[dict]) -> tuple[str | None, list[str]]:
    """The answer contains verified claims only. Nothing else can reach it."""
    verified = [c for c in claims if c["verified"]]
    if not verified:
        return None, []
    return " ".join(c["claim"] for c in verified), list(dict.fromkeys(c["source_url"] for c in verified))


def trace_meta(backend_name: str, model: str | None) -> dict:
    gpu_name, gpu_source = gpu_mod.detect_cached()
    return {
        "backend": backend_name,
        "model": model,
        "gpu": gpu_name,
        "gpu_source": gpu_source,
        "inference_on_amd": backend_name.startswith("rocm-"),
    }


def run(
    question: str,
    start_url: str | None,
    backend: Backend,
    limits: Limits,
    fetcher_factory=Fetcher,
    inject_fabricated: bool = False,
) -> dict:
    """Answer one question. Raises BlockedURL only for a refused start URL."""
    session = Session(question, start_url, limits, fetcher_factory)
    claims: list[dict] = []
    stop_reason = None
    try:
        drafts = backend.investigate(session)
        if inject_fabricated and drafts:
            first = drafts[0]
            altered = alter_quote(first.quote)
            drafts = drafts + [Draft(altered, altered, first.source_url, injected_for_demo=True)]
            session.step(type="demo_injection", note="Demo switch on: one quote was deliberately altered before verification.")
        claims = _verify_round(session, drafts, attempt=0)
        for attempt in range(1, limits.max_revisions + 1):
            failed = [c for c in claims if not c["verified"] and not c["injected_for_demo"]]
            if not failed or session.time_left() < 1.0:
                break
            more = backend.revise(session, failed)
            if not more:
                break
            for claim in failed:
                claim["superseded"] = True
            claims += _verify_round(session, more, attempt=attempt)
    except StepBudgetExceeded as exc:
        stop_reason = str(exc)
    answer, sources = assemble(claims)
    cited = {c["source_url"] for c in claims} & set(session.pages)
    unique: dict[str, Snapshot] = {}
    for url in cited:
        unique[session.pages[url].sha256] = session.pages[url]
    fetched = {snapshot.sha256: snapshot for snapshot in session.pages.values()}
    return {
        "status": "answered" if answer else "no_answer",
        "question": question,
        "start_url": start_url,
        "answer": answer,
        "sources": sources,
        "claims": claims,
        "snapshots": [s.public_dict() for s in unique.values()],
        "notes": session.notes + ([f"Stopped early: {stop_reason}"] if stop_reason else []),
        "trace": {
            "run_id": uuid.uuid4().hex[:12],
            "mode": "live",
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **trace_meta(backend.name, backend.model),
            "tokens": session.tokens,
            "wall_ms": int((time.monotonic() - session.started) * 1000),
            "pages_fetched": len(fetched),
            "limits": limits.to_dict(),
            "steps": session.steps,
        },
    }


def _verify_round(session: Session, drafts: list[Draft], attempt: int) -> list[dict]:
    judged = [_judge(d, session.pages, attempt) for d in drafts]
    for claim in judged:
        session.step(
            type="verify",
            source_url=claim["source_url"],
            verified=claim["verified"],
            match=claim["match"],
            reason=claim["reason"],
            injected_for_demo=claim["injected_for_demo"],
        )
    return judged
