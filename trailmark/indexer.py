"""The --index pass: walk the source, persist the index, then bring the model service up."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from . import client, pages, store

SERVICE_MAIN = Path(__file__).resolve().parent.parent / "app" / "service_main.py"


def service_main_path() -> Path:
    # In the image, app/ is flattened into /app, and trailmark sits next to app.py.
    sibling = Path(__file__).resolve().parent.parent / "service_main.py"
    return sibling if sibling.is_file() else SERVICE_MAIN


def build_index(contract, index_path: str | None) -> dict:
    source = pages.open_source(contract, index_path)
    collected: list[pages.Page] = []
    failures: list[dict] = []
    for item in source.walk():
        if isinstance(item, pages.PageFailure):
            failures.append(item.to_dict())
        else:
            collected.append(item)
    meta = {"mode": contract.section("pages")["mode"], "source": str(index_path), "pages": len(collected), "failures": len(failures), "contract": contract.source}
    target = contract.index_dir
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(dir=target.parent, prefix=".index-"))
    try:
        store.write_index(temp, collected, failures, meta)
        if target.exists():
            shutil.rmtree(target)
        temp.rename(target)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return meta


def start_service(contract, deadline: float) -> dict:
    """Reuse a live service, or start one and wait until it answers. Raises ModelUnavailable."""
    probe = client.ServiceClient(contract.socket_path, deadline, connect_wait=0.0)
    try:
        return probe.ping()
    except client.ModelUnavailable:
        pass
    contract.run_dir.mkdir(parents=True, exist_ok=True)
    process = client.spawn_service(service_main_path(), contract.run_dir / "service.log")
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise client.ModelUnavailable(f"the model service exited with code {code}; see {contract.run_dir / 'service.log'}")
        try:
            return probe.ping()
        except client.ModelUnavailable:
            time.sleep(0.2)
    raise client.ModelUnavailable("the model service was not ready in time")


def run_index(contract, index_path: str | None) -> int:
    started = time.monotonic()
    budget = float(contract.section("time")["startup_s"]) - float(contract.section("time")["margin_s"])
    meta = build_index(contract, index_path)
    print(json.dumps({"indexed_pages": meta["pages"], "failures": meta["failures"], "seconds": round(time.monotonic() - started, 2)}), flush=True)
    wait = min(float(contract.section("service")["ready_wait_s"]), budget - (time.monotonic() - started))
    try:
        info = start_service(contract, time.monotonic() + max(0.0, wait))
    except client.ModelUnavailable as exc:
        print(f"index stored, but no model is available: {exc}", file=sys.stderr, flush=True)
        return 3
    info.pop("ok", None)
    print(json.dumps({"service": info, "seconds": round(time.monotonic() - started, 2)}), flush=True)
    if info.get("is_stub"):
        print("STUB MODEL: backend fake is a scripted test double. Nothing it returns is a result.", flush=True)
    return 0
