"""One JSON request and one JSON reply per connection, over a unix socket. Standard library only."""

from __future__ import annotations

import json
import socket
import time

MAX_MESSAGE = 8_000_000


class ProtocolError(RuntimeError):
    pass


def read_message(conn: socket.socket, deadline: float | None = None) -> dict:
    """Read until newline. A deadline bounds the whole message, not one recv."""
    chunks: list[bytes] = []
    total = 0
    while True:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("message deadline reached")
            conn.settimeout(remaining)
        chunk = conn.recv(65536)
        if not chunk:
            raise ProtocolError("connection closed before a full message")
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_MESSAGE:
            raise ProtocolError("message too large")
        if chunk.endswith(b"\n") or b"\n" in chunk:
            break
    line = b"".join(chunks).split(b"\n", 1)[0]
    try:
        value = json.loads(line)
    except ValueError as exc:
        raise ProtocolError("message is not JSON") from exc
    if not isinstance(value, dict):
        raise ProtocolError("message is not an object")
    return value


def send_message(conn: socket.socket, message: dict) -> None:
    data = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
    if len(data) > MAX_MESSAGE:
        raise ProtocolError("message too large")
    conn.sendall(data)
