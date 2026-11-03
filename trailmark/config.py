"""Fetch limits and fixed identity. Match-4 facts live in app/contract.toml, not here."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

USER_AGENT = "TrailmarkBot/0.2 (+https://github.com/alexvec/amd-ai-league-lablab)"
ROBOTS_TOKEN = "trailmarkbot"
ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Limits:
    """Caps for one fetcher instance. The contract's page settings override these."""

    max_redirects: int = 4
    max_bytes: int = 2_000_000
    max_robots_bytes: int = 500_000
    max_text_chars: int = 400_000
    max_links: int = 300
    connect_timeout: float = 5.0
    read_timeout: float = 8.0
    per_fetch_seconds: float = 10.0
    request_seconds: float = 25.0
    per_host_delay: float = 0.4

    def to_dict(self) -> dict:
        return asdict(self)
