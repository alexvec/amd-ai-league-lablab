"""Joins the contract to the pipeline for one query process."""

from __future__ import annotations

import json
import time

from . import client, indexer, pages, pipeline, store


def refusal(trace: dict, reason: str) -> pipeline.Result:
    return pipeline.Result("", [], 0.0, {**trace, "outcome": "refused", "reason": reason})


def _start_ref(contract, start_url: str | None) -> str | None:
    if not start_url:
        return None
    section = contract.section("pages")
    if section["mode"] != "mirror":
        return start_url
    base = section["mirror_base_url"].rstrip("/")
    if base and start_url.startswith(base + "/"):
        return start_url[len(base) + 1 :]
    return start_url if not start_url.startswith(("http://", "https://")) else None


def answer(contract, question: str, start_url: str | None, budget: float) -> pipeline.Result:
    deadline = time.monotonic() + budget
    trace = {"question": question}
    try:
        index = store.PageStore(contract.index_dir)
    except store.IndexMissing as exc:
        return refusal(trace, str(exc))
    section = contract.section("service")
    model = client.ServiceClient(contract.socket_path, deadline, float(section["connect_wait_s"]))
    if section["respawn_on_missing"]:
        _respawn_if_missing(contract, model, deadline)
    source = pages.open_source(contract, None) if contract.section("pages")["mode"] != "mirror" else None
    return pipeline.answer_question(question, index, model, pipeline.Settings.from_contract(contract), deadline, _start_ref(contract, start_url), source)


def _respawn_if_missing(contract, model: client.ServiceClient, deadline: float) -> None:
    """Off by default. Loading a model inside a question only fits the budget if a measurement says so."""
    try:
        model.ping()
    except client.ModelUnavailable:
        indexer.start_service(contract, deadline)


def record_trace(contract, query_id: str, trace: dict) -> None:
    """For audit only. A failure here must not touch the answer that was already written."""
    try:
        directory = contract.run_dir / "traces"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{query_id}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=1), "utf-8")
    except (OSError, TypeError, ValueError):
        pass
