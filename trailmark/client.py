"""The query process's side of the socket. It must never import torch or load a model."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from . import protocol


class ModelUnavailable(RuntimeError):
    """The service is absent, stuck or broken. The caller refuses."""


class ServiceClient:
    def __init__(self, socket_path: str | Path, deadline: float, connect_wait: float = 2.0):
        self.socket_path = str(socket_path)
        self.deadline = deadline
        self.connect_wait = connect_wait
        self.info: dict = {}

    def _connect(self, wait: float) -> socket.socket:
        stop = min(time.monotonic() + wait, self.deadline)
        last: Exception | None = None
        while True:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                conn.settimeout(max(0.05, min(1.0, self.deadline - time.monotonic())))
                conn.connect(self.socket_path)
                return conn
            except OSError as exc:
                conn.close()
                last = exc
            if time.monotonic() >= stop:
                raise ModelUnavailable(f"cannot reach the model service: {type(last).__name__}")
            time.sleep(0.05)

    def call(self, request: dict) -> dict:
        conn = self._connect(self.connect_wait)
        try:
            protocol.send_message(conn, request)
            reply = protocol.read_message(conn, self.deadline)
        except (OSError, TimeoutError, protocol.ProtocolError) as exc:
            raise ModelUnavailable(f"model service failed: {type(exc).__name__}") from exc
        finally:
            conn.close()
        if not reply.get("ok"):
            raise ModelUnavailable(f"model service error: {reply.get('error', 'unknown')}")
        return reply

    def ping(self) -> dict:
        self.info = self.call({"op": "ping"})
        return self.info

    def generate(self, kind: str, messages: list[dict], meta: dict, max_new_tokens: int) -> dict:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ModelUnavailable("query deadline reached")
        return self.call({"op": "generate", "kind": kind, "messages": messages, "meta": meta, "max_new_tokens": max_new_tokens, "max_time_s": max(0.1, remaining - 0.5)})


def spawn_service(service_main: Path, log_path: Path) -> subprocess.Popen:
    """Detached from this process and its session, so it outlives the exec that started it."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    try:
        return subprocess.Popen([sys.executable, str(service_main)], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    finally:
        log.close()
