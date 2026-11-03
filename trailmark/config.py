"""Hard limits and environment configuration. Everything here is plain data."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

USER_AGENT = "TrailmarkBot/0.1 (+https://github.com/alexvec/amd-ai-league-lablab)"
ROBOTS_TOKEN = "trailmarkbot"
ROOT = Path(__file__).resolve().parent.parent
TRACES_DIR = ROOT / "traces"

BACKEND_EXTRACTIVE = "extractive-no-llm"


@dataclass(frozen=True)
class Limits:
    """Per-request caps for the public endpoint."""

    max_pages: int = 5
    max_steps: int = 40
    max_redirects: int = 4
    max_bytes: int = 2_000_000
    max_robots_bytes: int = 500_000
    max_text_chars: int = 120_000
    max_links: int = 300
    connect_timeout: float = 5.0
    read_timeout: float = 8.0
    per_fetch_seconds: float = 10.0
    request_seconds: float = 25.0
    per_host_delay: float = 0.4
    max_llm_calls: int = 8
    max_revisions: int = 2

    def to_dict(self) -> dict:
        return asdict(self)


def public_limits() -> Limits:
    """Limits for the HTTP endpoint. A model server on a notebook needs more time."""
    seconds = float(os.environ.get("TRAILMARK_REQUEST_SECONDS", "25"))
    return Limits(request_seconds=min(seconds, 600.0))


def backend_choice() -> str:
    return os.environ.get("TRAILMARK_BACKEND", "extractive").strip().lower()


def llm_settings() -> dict:
    return {
        "base_url": os.environ.get("TRAILMARK_LLM_BASE_URL", "").strip(),
        "api_key": os.environ.get("TRAILMARK_LLM_API_KEY", "").strip(),
        "model": os.environ.get("TRAILMARK_LLM_MODEL", "").strip(),
    }
