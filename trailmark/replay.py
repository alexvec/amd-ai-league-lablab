"""Replay of traces this code generated. Always labelled, and always re-verified.

Stored flags are not trusted: each claim is checked again against the stored snapshot.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

from .agent import assemble
from .config import TRACES_DIR
from .extract import sha256_text  # noqa: F401  re-exported for callers checking snapshots
from .verifier import verify_claim

SAFE_ID = re.compile(r"^[a-zA-Z0-9_.-]{1,120}$")


class TraceNotFound(LookupError):
    pass


def list_traces(directory: Path = TRACES_DIR) -> list[dict]:
    rows = []
    if not directory.is_dir():
        return rows
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text("utf-8"))
            trace = data["trace"]
        except (ValueError, KeyError, OSError):
            continue
        rows.append(
            {
                "id": path.stem,
                "question": data.get("question"),
                "backend": trace.get("backend"),
                "model": trace.get("model"),
                "gpu": trace.get("gpu"),
                "inference_on_amd": bool(trace.get("inference_on_amd")),
                "recorded_at": trace.get("recorded_at"),
            }
        )
    return rows


def amd_runs(directory: Path = TRACES_DIR) -> list[dict]:
    """Recorded runs that measured an AMD GPU and used a rocm-* backend."""
    return [row for row in list_traces(directory) if row["inference_on_amd"] and row["gpu"]]


def replay(trace_id: str | None, directory: Path = TRACES_DIR) -> dict:
    rows = list_traces(directory)
    if trace_id is None and rows:
        trace_id = rows[-1]["id"]
    if not trace_id or not SAFE_ID.match(trace_id) or not (directory / f"{trace_id}.json").is_file():
        raise TraceNotFound(trace_id or "(no traces recorded)")
    data = json.loads((directory / f"{trace_id}.json").read_text("utf-8"))
    response = copy.deepcopy(data)
    pages = {}
    for snapshot in response.get("snapshots", []):
        stored = SimpleNamespace(text=snapshot.get("text", ""), sha256=snapshot.get("sha256", ""))
        pages[snapshot.get("url")] = stored
        pages[snapshot.get("final_url")] = stored
    for claim in response.get("claims", []):
        verdict = verify_claim(claim.get("claim", ""), claim.get("quote", ""), claim.get("source_url", ""), pages)
        claim.update(verified=verdict.verified, match=verdict.match, reason=verdict.reason, start=verdict.start, end=verdict.end, in_answer=verdict.verified)
    answer, sources = assemble(response.get("claims", []))
    response.update(answer=answer, sources=sources, status="answered" if answer else "no_answer")
    trace = response["trace"]
    trace["mode"] = "replay"
    trace["trace_id"] = trace_id
    response["replay_notice"] = (
        f"Replay of a run recorded {trace.get('recorded_at')} by backend {trace.get('backend')}. "
        "No page was fetched and no inference ran for this response. The verifier re-checked the stored snapshot just now."
    )
    return response
