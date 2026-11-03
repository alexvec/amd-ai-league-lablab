"""Model backends for the resident service.

FakeBackend is a stub and not a model. It replays a script of replies written by hand for the
fixture questions, so tests can drive the socket, retrieval, verifier and citation code. It proves
nothing about what a model would do, and a run with it is never a result. It stamps backend "fake"
everywhere and refuses to load unless MC4_ALLOW_FAKE=1. The image never sets that variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class BackendRefused(RuntimeError):
    """This backend must not run here. The service exits non-zero."""

    exit_code = 2


class FakeBackend:
    name = "fake"

    def __init__(self, script_path: str | None = None):
        if os.environ.get("MC4_ALLOW_FAKE") != "1":
            raise BackendRefused("the fake backend is a test stub and needs MC4_ALLOW_FAKE=1. It is never a result.")
        path = script_path or os.environ.get("MC4_FAKE_SCRIPT")
        self.script = json.loads(Path(path).read_text("utf-8")) if path else {}

    def info(self) -> dict:
        return {"backend": self.name, "model": "none (scripted stub, not a model)", "gpu": None, "hip": None, "is_stub": True}

    def warmup(self) -> None:
        return None

    def generate(self, kind: str, messages: list[dict], meta: dict, max_new_tokens: int, max_time_s: float) -> dict:
        entry = self.script.get(meta.get("question", ""), {})
        if kind == "plan":
            reply = {"terms": entry.get("plan", [])}
        else:
            reads = entry.get("reads", [])
            hop = int(meta.get("hop", 0))
            reply = self._translate(reads[hop], meta) if hop < len(reads) else {"action": "none"}
        return {"text": json.dumps(reply) if isinstance(reply, dict) else str(reply), "tokens_in": 0, "tokens_out": 0}

    @staticmethod
    def _label(pages: dict, wanted: str) -> str:
        """The script names pages by path. A page not opened in this run stays unmatched and gets rejected."""
        for label, ref in pages.items():
            if ref == wanted or ref.endswith("/" + wanted):
                return label
        return f"NOT-OPENED:{wanted}"

    def _translate(self, reply, meta: dict):
        if not isinstance(reply, dict):
            return reply
        pages = meta.get("pages", {})
        if "open_ref" in reply:
            wanted = reply["open_ref"]
            for link in meta.get("links", []):
                if link["ref"] == wanted or link["ref"].endswith("/" + wanted):
                    return {"action": "open", "link": link["index"]}
            return {"action": "open", "link": -1}
        if reply.get("action") == "answer":
            candidates = []
            for candidate in reply.get("candidates", []):
                evidence = [{"page": self._label(pages, item["page"]), "span": item["span"]} for item in candidate.get("evidence", [])]
                candidates.append({**candidate, "evidence": evidence})
            return {**reply, "candidates": candidates}
        return reply


def load_backend(name: str, service_section: dict):
    if name == "fake":
        return FakeBackend()
    if name == "rocm":
        from . import model_rocm  # torch is imported only here, and only in the service process

        return model_rocm.RocmBackend(service_section["model_dir"], service_section["model_name"])
    raise BackendRefused(f"unknown backend: {name}")
