"""When two pages disagree, decide which one counts, from what the pages say about themselves."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

HEAD_LINES = 12
# A line saying this page replaces another is about the other page.
POINTS_ELSEWHERE = re.compile(r"(?i)\b(supersedes|replaces|obsoletes|updates|withdraws)\b")
STATUS = re.compile(
    r"(?i)(\bstatus\s*[:|-]\s*(withdrawn|superseded|obsolete|retired|deprecated|archived)\b"
    r"|\b(this|the)\s+(\w+\s+){0,3}(has been|is|was)\s+(now\s+)?(withdrawn|superseded|obsolete|retired|deprecated)\b"
    r"|\bsuperseded\s+by\b|\breplaced\s+by\b|^\W*(withdrawn|superseded|obsolete)\W*$)"
)
NAME_STATUS = re.compile(r"(?i)(^|[\W_])(withdrawn|superseded|obsolete|deprecated)([\W_]|$)")
# In a title the word must stand apart from the name: "Datasheet (withdrawn)", not "Deprecated APIs guide".
TITLE_STATUS = re.compile(r"(?i)(^|[(\[:–—-])\s*(withdrawn|superseded|obsolete|deprecated)\s*($|[)\]:–—-])")
REVISION = re.compile(r"(?i)(?:^|[\W_])(?:(?:revision|rev\.?)[\s_-]*(\d{1,3}|[a-z])|r[_-]?(\d{1,3}))(?![a-z0-9])")
CLAUSE = re.compile(r"(?<!\bRev\.)(?<!\brev\.)(?<=[.;])\s+")
ISO_DATE = re.compile(r"\b(20\d{2}|19\d{2})-(\d{2})-(\d{2})\b")
DATE_LABEL = re.compile(r"(?i)\b(updated|revised|published|issued|effective|dated?|released)\b")
COMMENT_LINE = re.compile(r"^\s*(#|//|--|/\*|\*|;|<!--)")


@dataclass(frozen=True)
class PageStatus:
    stale: bool
    reason: str
    revision: int | None
    date: date | None


def _revision_value(raw: str) -> int:
    return int(raw) if raw.isdigit() else ord(raw.upper()) - ord("A") + 1


def _own_clauses(lines: list[str]) -> list[str]:
    """Clauses about this page. "Revision 2. Supersedes revision 1." keeps only the first."""
    return [part for line in lines if line.strip() for part in CLAUSE.split(line) if part.strip() and not POINTS_ELSEWHERE.search(part)]


def page_status(ref: str, title: str, text: str, chrome: str = "") -> PageStatus:
    """Only the page's own name, title and top lines count. A mention deep in a page is not a status."""
    head = _own_clauses([line for line in text.split("\n")[:HEAD_LINES]])
    lines = _own_clauses([title, *chrome.split("\n")]) + head
    reason = ""
    if NAME_STATUS.search(ref.rsplit("/", 1)[-1]):
        reason = "file name"
    elif title and not POINTS_ELSEWHERE.search(title) and TITLE_STATUS.search(title):
        reason = "title"
    else:
        reason = next((f"line: {line[:80]}" for line in lines if STATUS.search(line)), "")
    revision = None
    for line in [*_own_clauses([title]), *head, ref.rsplit("/", 1)[-1]]:
        match = REVISION.search(line)
        if match:
            revision = _revision_value(match.group(1) or match.group(2))
            break
    found_date = None
    for line in head:
        match = ISO_DATE.search(line)
        if match and DATE_LABEL.search(line):
            try:
                found_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                break
            except ValueError:
                continue
    return PageStatus(bool(reason), reason, revision, found_date)


def is_comment_line(line: str) -> bool:
    return COMMENT_LINE.match(line) is not None


@dataclass
class Group:
    """Every verified candidate carrying the same value."""

    value: str
    spans: list  # verifier-approved evidence spans with .ref, .line
    statuses: list[PageStatus]  # the statuses of the pages holding the value
    all_comments: bool


def pick(groups: list[Group]) -> tuple[Group | None, str]:
    """(winner, reason). None means refuse. Never guesses between undated, unlabelled conflicts."""
    if not groups:
        return None, "no_verified_candidate"
    alive = groups
    if len(alive) > 1:
        plain = [group for group in alive if not group.all_comments]
        alive = plain or alive
    fresh = [group for group in alive if not all(status.stale for status in group.statuses)]
    if not fresh:
        return None, "only_withdrawn_or_superseded_pages_hold_the_value"
    if len(fresh) == 1:
        return fresh[0], "single_value" if len(groups) == 1 else "conflict_resolved_by_status"
    for attribute, reason in (("revision", "revision_label"), ("date", "date_label")):
        ranks = [max((getattr(status, attribute) for status in group.statuses if getattr(status, attribute) is not None), default=None) for group in fresh]
        if all(rank is not None for rank in ranks):
            top = max(ranks)
            winners = [group for group, rank in zip(fresh, ranks) if rank == top]
            if len(winners) == 1:
                return winners[0], f"conflict_resolved_by_{reason}"
    return None, "conflict_not_determinable"
