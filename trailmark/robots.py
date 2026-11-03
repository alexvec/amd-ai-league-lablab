"""robots.txt matching per RFC 9309: group selection, longest match, * and $ wildcards.

Written here because urllib.robotparser uses first-match order and ignores wildcards,
which would treat some disallowed paths as allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Robots:
    rules: list[tuple[bool, str]] = field(default_factory=list)
    allow_all: bool = False
    deny_all: bool = False

    def allowed(self, path_query: str) -> bool:
        if self.deny_all:
            return False
        if self.allow_all:
            return True
        best_length, verdict = -1, True
        for allow, pattern in self.rules:
            if _matches(pattern, path_query):
                length = len(pattern)
                if length > best_length or (length == best_length and allow):
                    best_length, verdict = length, allow
        return verdict


def _matches(pattern: str, path: str) -> bool:
    """Prefix match with * and $. Greedy and linear: a hostile robots.txt cannot cause backtracking."""
    anchored = pattern.endswith("$")
    pieces = (pattern[:-1] if anchored else pattern).split("*")
    if not path.startswith(pieces[0]):
        return False
    position = len(pieces[0])
    if len(pieces) == 1:
        return not anchored or position == len(path)
    tail = pieces[-1] if anchored else None
    for piece in pieces[1:-1] if anchored else pieces[1:]:
        found = path.find(piece, position)
        if found < 0:
            return False
        position = found + len(piece)
    if tail is None:
        return True
    return len(path) - len(tail) >= position and path.endswith(tail)


def parse(text: str, token: str) -> Robots:
    groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[bool, str]] = []
    in_rules = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((agents, rules))
                agents, rules, in_rules = [], [], False
            agents.append(value.lower())
        elif key in ("allow", "disallow"):
            in_rules = True
            if value:
                rules.append((key == "allow", value))
    if agents:
        groups.append((agents, rules))

    token = token.lower()
    specific = [r for names, r in groups if any(n and n != "*" and n in token for n in names)]
    chosen = specific or [r for names, r in groups if "*" in names]
    return Robots(rules=[rule for group in chosen for rule in group])


def from_status(status: int, body: str, token: str) -> Robots:
    """RFC 9309 section 2.3.1: 4xx means no restrictions, 5xx or failure means assume denied.

    401 and 403 are also treated as denied: a site refusing the policy file should not
    be read as permission.
    """
    if status in (401, 403):
        return Robots(deny_all=True)
    if 200 <= status < 300:
        return parse(body, token)
    if 400 <= status < 500:
        return Robots(allow_all=True)
    return Robots(deny_all=True)
