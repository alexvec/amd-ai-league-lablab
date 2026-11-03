"""The resident model service: one process, one loaded model, one unix socket, no port.

--index starts it. Each question is a new client process. The socket is only bound after the model
has loaded and a warm-up generation finished, so a reachable socket means a ready model.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
import time
from pathlib import Path

from . import protocol
from .backends import BackendRefused, load_backend

READ_SECONDS = 5.0


def serve(backend, socket_path: Path, ready_file: Path, stop_after: int | None = None) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(socket_path.parent, 0o700)
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old_umask = os.umask(0o177)
    try:
        listener.bind(str(socket_path))
    finally:
        os.umask(old_umask)
    listener.listen(8)
    ready_file.write_text(json.dumps({**backend.info(), "pid": os.getpid(), "ready_at": time.time()}), "utf-8")
    print(f"service ready: {json.dumps(backend.info())}", flush=True)
    served = 0
    while stop_after is None or served < stop_after:
        conn, _ = listener.accept()
        served += 1
        with conn:
            try:
                request = protocol.read_message(conn, time.monotonic() + READ_SECONDS)
                protocol.send_message(conn, handle(backend, request))
            except (OSError, TimeoutError, protocol.ProtocolError) as exc:
                print(f"request dropped: {type(exc).__name__}: {exc}", flush=True)
            except Exception as exc:  # noqa: BLE001 - one bad request must not take down the resident model
                print(f"request failed: {type(exc).__name__}: {exc}", flush=True)
                try:
                    protocol.send_message(conn, {"ok": False, "error": type(exc).__name__})
                except OSError:
                    pass


def handle(backend, request: dict) -> dict:
    op = request.get("op")
    if op == "ping":
        return {"ok": True, **backend.info()}
    if op == "generate":
        reply = backend.generate(
            str(request.get("kind", "")),
            request.get("messages") or [],
            request.get("meta") or {},
            int(request.get("max_new_tokens", 64)),
            float(request.get("max_time_s", 25.0)),
        )
        return {"ok": True, "backend": backend.name, **reply}
    return {"ok": False, "error": f"unknown op: {op}"}


def main(contract) -> int:
    section = contract.section("service")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"service starting: backend={section['backend']} model_dir={section['model_dir']}", flush=True)
    try:
        backend = load_backend(section["backend"], section)
    except BackendRefused as exc:
        print(f"service refused to start: {exc}", file=sys.stderr, flush=True)
        return exc.exit_code
    backend.warmup()
    serve(backend, contract.socket_path, contract.run_dir / "service.json")
    return 0
