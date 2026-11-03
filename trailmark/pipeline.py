"""One question: plan, retrieve, read, verify, cite. The model proposes. Plain code decides."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import answer as answer_mod
from . import necessity, prompts, supersession, textscore, verifier
from .client import ModelUnavailable
from .necessity import EvidenceSpan
from .pages import Page, PageError

LINKS_SHOWN = 30
REPLY_ERRORS = (ValueError, TypeError, KeyError, AttributeError)


@dataclass
class Result:
    answer: str
    citations: list[str]
    confidence: float
    trace: dict = field(default_factory=dict)


@dataclass
class Settings:
    pages: int = 4
    first_round_pages: int = 3
    hops: int = 2
    plan_step: bool = True
    retries: int = 1
    read_chars: int = 12000
    plan_tokens: int = 64
    read_tokens: int = 400
    refuse_on_unreadable_overlap: int = 2
    strip_units: bool = True
    cite_form: str = "path"

    @classmethod
    def from_contract(cls, contract) -> "Settings":
        budget = contract.section("budget")
        known = {key: budget[key] for key in budget if key in cls.__dataclass_fields__}
        return cls(**known, strip_units=bool(contract.section("output")["strip_units"]), cite_form=contract.cite_form())


class Run:
    """The state of one question."""

    def __init__(self, question: str, store, model, settings: Settings, deadline: float, source=None):
        self.question = question
        self.store = store
        self.model = model
        self.settings = settings
        self.deadline = deadline
        self.source = source
        self.opened: dict[str, Page] = {}  # label -> page; labels are built here, in opening order
        self.started = time.monotonic()
        self.tokens = {"in": 0, "out": 0}
        self.steps: list[dict] = []
        self.backend = None

    def log(self, kind: str, **fields) -> None:
        self.steps.append({"t_ms": int((time.monotonic() - self.started) * 1000), "step": kind, **fields})

    def label_of(self, page: Page) -> str:
        return next(label for label, item in self.opened.items() if item.ref == page.ref)

    def open_page(self, page: Page) -> bool:
        if len(self.opened) >= self.settings.pages or any(item.ref == page.ref for item in self.opened.values()):
            return False
        label = f"P{len(self.opened) + 1}"
        self.opened[label] = page
        self.log("open", label=label, ref=page.ref, sha256=page.sha256)
        return True

    def open_ref(self, ref: str) -> bool:
        resolved = self.store.resolve(ref)
        if resolved is not None:
            return self.open_page(self.store.pages[resolved])
        if self.source is not None and hasattr(self.source, "read") and ref.startswith(("http://", "https://")):
            try:
                return self.open_page(self.source.read(ref, self.deadline))
            except PageError as exc:
                self.log("open_failed", ref=ref, error=str(exc)[:200])
        return False

    def ask(self, kind: str, messages: list[dict], meta: dict, tokens: int) -> str:
        reply = self.model.generate(kind, messages, {"question": self.question, **meta}, tokens)
        self.backend = reply.get("backend", self.backend)
        self.tokens["in"] += int(reply.get("tokens_in", 0) or 0)
        self.tokens["out"] += int(reply.get("tokens_out", 0) or 0)
        return str(reply.get("text", ""))

    def link_list(self) -> list[dict]:
        links: list[dict] = []
        known = {page.ref for page in self.opened.values()}
        wanted = set(textscore.terms(self.question))
        rows = []
        for label, page in self.opened.items():
            for link in page.links:
                if link["ref"] not in known:
                    rows.append((-textscore.link_score(wanted, link["text"], link["ref"]), len(rows), label, link))
        seen: set[str] = set()
        for _, _, label, link in sorted(rows, key=lambda row: row[:2]):
            if link["ref"] in seen:
                continue
            seen.add(link["ref"])
            links.append({"index": len(links), "label": label, "ref": link["ref"], "text": link["text"][:120]})
            if len(links) >= LINKS_SHOWN:
                break
        return links

    def blocks(self, query: str) -> list[dict]:
        share = self.settings.read_chars // max(1, len(self.opened))
        return [
            {"label": label, "ref": page.ref, "title": page.title, "text": textscore.relevant_text(page.text, query, share)}
            for label, page in self.opened.items()
        ]


def _reject(run: Run, candidate_index: int, reason: str, **fields) -> None:
    run.log("candidate_rejected", candidate=candidate_index, reason=reason, **fields)


def _authority(question: str, status: supersession.PageStatus, line: str, holds_value: bool) -> float:
    """Who survives when pages repeat each other. Current beats stale, a labelled row beats prose."""
    score = 0.0
    if not status.stale:
        score += 100
    if status.revision is not None or status.date is not None:
        score += 10
    if "|" in line or ":" in line or "=" in line:
        score += 10
    if holds_value:
        score += 1
    return score + 0.01 * len(set(textscore.terms(question)) & set(textscore.terms(line)))


def check_candidate(run: Run, index: int, candidate: dict) -> tuple[str, list[EvidenceSpan]] | None:
    """Everything a candidate must pass before it can be considered. The model's word counts for nothing."""
    value = answer_mod.clean_value(candidate.get("value"), run.settings.strip_units)
    if value is None:
        _reject(run, index, "not_a_value", value=str(candidate.get("value"))[:80])
        return None
    evidence = candidate.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        _reject(run, index, "no_evidence", value=value)
        return None
    spans: list[EvidenceSpan] = []
    for item in evidence:
        if not isinstance(item, dict):
            _reject(run, index, "bad_evidence_shape", value=value)
            return None
        page = run.opened.get(str(item.get("page")))
        if page is None:
            _reject(run, index, "page_not_opened_in_this_run", value=value, page=str(item.get("page"))[:80])
            return None
        span_text = item.get("span")
        verdict = verifier.verify_span(span_text, page.text)
        if not verdict.ok:
            _reject(run, index, verdict.reason, value=value, ref=page.ref, span=str(span_text)[:160])
            return None
        line = verifier.enclosing_line(page.text, verdict.start, verdict.end)
        if verifier.looks_like_injection(line):
            _reject(run, index, "span_is_text_addressed_to_the_model", value=value, ref=page.ref)
            return None
        status = supersession.page_status(page.ref, page.title, page.text, page.chrome)
        holds = verifier.value_in_text(value, span_text)
        spans.append(EvidenceSpan(page.ref, span_text, _authority(run.question, status, line, holds), line))
    holders = [span for span in spans if verifier.value_in_text(value, span.text)]
    if not holders:
        _reject(run, index, "value_not_in_any_span", value=value)
        return None
    if all(verifier.wrong_row(run.question, span.line) for span in holders):
        _reject(run, index, "span_is_about_a_different_item", value=value, line=holders[0].line[:160])
        return None
    pages_text = [next(page.text for page in run.opened.values() if page.ref == span.ref) for span in spans]
    if verifier.subject_missing(run.question, pages_text, value):
        _reject(run, index, "subject_of_question_not_on_evidence_pages", value=value)
        return None
    return value, spans


def _group(run: Run, checked: list[tuple[str, list[EvidenceSpan]]]) -> list[tuple[supersession.Group, list[EvidenceSpan]]]:
    merged: dict[str, tuple[str, list[EvidenceSpan]]] = {}
    for value, spans in checked:
        key = answer_mod.comparison_key(value)
        merged.setdefault(key, (value, []))[1].extend(spans)
    groups = []
    for value, spans in merged.values():
        holders = [span for span in spans if verifier.value_in_text(value, span.text)]
        statuses = []
        for ref in {span.ref for span in holders}:
            page = next(item for item in run.opened.values() if item.ref == ref)
            statuses.append(supersession.page_status(page.ref, page.title, page.text, page.chrome))
        comments = all(supersession.is_comment_line(span.line) for span in holders)
        groups.append((supersession.Group(value, holders, statuses, comments), spans))
    return groups


def unreadable_overlap(question: str, failures: list[dict], threshold: int) -> str | None:
    """A page we could not read, whose name matches the question, might hold the answer."""
    wanted = set(textscore.terms(question))
    for failure in failures:
        if failure.get("kind") in ("empty_directory", "walk_budget_reached"):
            continue
        name = failure.get("ref", "").replace("/", " ").replace("_", " ").replace("-", " ").replace(".", " ")
        if len(wanted & set(textscore.terms(name))) >= threshold:
            return failure["ref"]
    return None


def decide(run: Run, candidates: list[dict]) -> Result:
    """Pure code from here on: verify, resolve conflicts, compute the necessity set."""
    checked = []
    for index, candidate in enumerate(candidates):
        result = check_candidate(run, index, candidate) if isinstance(candidate, dict) else None
        if result is not None:
            checked.append(result)
    grouped = _group(run, checked)
    winner, reason = supersession.pick([group for group, _ in grouped])
    run.log("supersession", reason=reason, values=[group.value for group, _ in grouped])
    if winner is None:
        return finish(run, None, [], reason)
    blocked = unreadable_overlap(run.question, run.store.failures, run.settings.refuse_on_unreadable_overlap)
    if blocked is not None:
        return finish(run, None, [], "unreadable_page_might_hold_the_answer", blocked=blocked)
    spans = next(spans for group, spans in grouped if group is winner)
    refs = necessity.necessary_pages(spans, winner.value, run.question)
    run.log("necessity", kept=refs, considered=sorted({span.ref for span in spans}))
    if not refs:
        return finish(run, None, [], "evidence_does_not_entail_the_value")
    return finish(run, winner.value, refs, "answered")


def _citation(run: Run, ref: str) -> str:
    if run.settings.cite_form == "url":
        page = next(item for item in run.opened.values() if item.ref == ref)
        return page.url
    if ref.startswith(("http://", "https://")):
        return ref.split("://", 1)[1].split("/", 1)[-1]
    return ref


def finish(run: Run, value: str | None, refs: list[str], reason: str, **fields) -> Result:
    trace = {
        "question": run.question,
        "backend": run.backend,
        "outcome": "answered" if value else "refused",
        "reason": reason,
        "tokens": run.tokens,
        "wall_ms": int((time.monotonic() - run.started) * 1000),
        "opened": {label: page.ref for label, page in run.opened.items()},
        "steps": run.steps,
        **fields,
    }
    if value is None:
        return Result("", [], 0.0, trace)
    return Result(value, sorted(_citation(run, ref) for ref in refs), 0.9, trace)


def answer_question(question: str, store, model, settings: Settings, deadline: float, start_ref: str | None = None, source=None) -> Result:
    run = Run(question, store, model, settings, deadline, source)
    try:
        return _run(run, start_ref)
    except ModelUnavailable as exc:
        return finish(run, None, [], f"model_unavailable: {exc}")


def _run(run: Run, start_ref: str | None) -> Result:
    settings = run.settings
    query = run.question
    if settings.plan_step:
        reply = prompts.parse_json_reply(run.ask("plan", prompts.plan_messages(run.question), {}, settings.plan_tokens)) or {}
        extra = reply.get("terms")
        if isinstance(extra, list):
            planned = [str(term)[:80] for term in extra[:8] if isinstance(term, (str, int, float))]
            query = " ".join([run.question, *planned])
            run.log("plan", terms=planned)
    if start_ref:
        if not run.open_ref(start_ref):
            run.log("start_page_not_available", ref=start_ref)
    ranked = run.store.search(query)
    run.log("search", query=query[:200], hits=ranked[:8])
    for ref in ranked:
        if len(run.opened) >= settings.first_round_pages:
            break
        run.open_page(run.store.pages[ref])
    if not run.opened:
        return finish(run, None, [], "no_page_matched")

    for hop in range(settings.hops + 1):
        links = run.link_list()
        pages_meta = {label: page.ref for label, page in run.opened.items()}
        messages = prompts.read_messages(run.question, run.blocks(query), links)
        reply = None
        for _ in range(settings.retries + 1):
            reply = prompts.parse_json_reply(run.ask("read", messages, {"hop": hop, "pages": pages_meta, "links": links}, settings.read_tokens))
            if reply is not None:
                break
        action = reply.get("action") if reply else None
        run.log("read", hop=hop, action=action, pages=list(pages_meta))
        if action == "answer":
            candidates = reply.get("candidates")
            if not isinstance(candidates, list):
                return finish(run, None, [], "malformed_candidates")
            return decide(run, candidates)
        if action == "search":
            # A search or link that adds no page is not the end: the hop budget bounds the rounds,
            # and the model may be able to answer from what is already open.
            terms = reply.get("terms")
            if isinstance(terms, list) and terms:
                text = " ".join(str(term)[:80] for term in terms[:8])
                query = f"{query} {text}"
                hits = [ref for ref in run.store.search(text) if ref not in pages_meta.values()]
                run.log("search", query=text[:200], hits=hits[:8])
                if hits:
                    run.open_page(run.store.pages[hits[0]])
        elif action == "open":
            target = reply.get("link")
            chosen = next((item for item in links if item["index"] == target), None) if isinstance(target, int) and not isinstance(target, bool) else None
            if chosen is not None:
                run.open_ref(chosen["ref"])
        else:
            break
    return finish(run, None, [], "model_found_nothing")
