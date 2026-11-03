"""The citation set: necessity, not relevance. Section 3.1 of the PRD, at string level.

Start with the pages carrying the used spans and try removing one page at a time, least
authoritative first. A removal stands if the remaining spans still entail the value:

- some remaining span holds the value, and
- every linking identifier that span depends on is still introduced by a remaining span on another
  page, recursively, so a chain of any length survives or breaks as a whole.

A linking identifier is one shared between a value-holding span and a span that does not hold the
value, and not named in the question. If the question itself names the ticket, the page naming it
is not needed, because the reader already has it.

Known limits: chains linked by anything other than an identifier (a shared plain word, say) are not
seen, so such a first hop would be dropped. And a span that shares an identifier with the value's span
only by coincidence looks like a chain, so that page would be kept.
"""

from __future__ import annotations

from dataclasses import dataclass

from .verifier import identifiers, value_in_text


@dataclass(frozen=True)
class EvidenceSpan:
    ref: str
    text: str
    authority: float = 0.0  # higher is kept longer; see authority() in pipeline
    line: str = ""


def _links(span: EvidenceSpan, others: list[EvidenceSpan], excluded: set[str]) -> set[str]:
    found = identifiers(span.text) - excluded
    shared: set[str] = set()
    for other in others:
        if other.ref != span.ref:
            shared |= found & identifiers(other.text)
    return shared


def _chain_holds(span: EvidenceSpan, kept: list[EvidenceSpan], non_holders: list[EvidenceSpan], excluded: set[str], seen: frozenset[str]) -> bool:
    """Every link this span depends on (judged on all evidence) is introduced by a kept span."""
    for link in _links(span, non_holders, excluded):
        providers = [other for other in kept if other.ref != span.ref and other.ref not in seen and other in non_holders and link in identifiers(other.text)]
        if not any(_chain_holds(other, kept, non_holders, excluded | {link}, seen | {span.ref}) for other in providers):
            return False
    return True


def entails(kept: list[EvidenceSpan], all_spans: list[EvidenceSpan], value: str, question: str) -> bool:
    holders = [span for span in kept if value_in_text(value, span.text)]
    if not holders:
        return False
    non_holders = [span for span in all_spans if not value_in_text(value, span.text)]
    excluded = identifiers(question) | identifiers(value)
    return any(_chain_holds(holder, kept, non_holders, excluded, frozenset()) for holder in holders)


def necessary_pages(spans: list[EvidenceSpan], value: str, question: str) -> list[str]:
    """The pages whose removal breaks the chain. Returns [] if the evidence never entailed the value."""
    if not entails(spans, spans, value, question):
        return []
    kept = list(spans)
    refs = sorted({span.ref for span in spans}, key=lambda ref: (max(span.authority for span in spans if span.ref == ref), ref))
    for ref in refs:
        trial = [span for span in kept if span.ref != ref]
        if trial and entails(trial, spans, value, question):
            kept = trial
    return sorted({span.ref for span in kept})
