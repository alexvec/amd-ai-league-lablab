#!/usr/bin/env python3
"""Serves fixtures/site on 127.0.0.1 with injected faults, for the proxy path. Not part of the image."""

from __future__ import annotations

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FAULT_PAGE = (
    '<html><head><title>Fault index</title></head><body><main><p>Links to faulty pages, then a good one.</p>'
    '<a href="/fault/500">a</a><a href="/fault/redirect-loop">b</a><a href="/fault/slow">c</a><a href="/fault/oversized">d</a>'
    '<a href="/fault/binary">e</a><a href="/index.html">f</a></main></body></html>'
)


def make_server(root: Path, slow_seconds: float = 30.0, port: int = 0) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, status: int, body: bytes, ctype: str = "text/html; charset=utf-8", headers: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/robots.txt":
                return self._send(404, b"none")
            if path == "/fault/index.html":
                return self._send(200, FAULT_PAGE.encode())
            if path == "/fault/500":
                return self._send(500, b"server error")
            if path == "/fault/redirect-loop":
                return self._send(302, b"", headers={"Location": "/fault/redirect-loop"})
            if path == "/fault/slow":
                time.sleep(slow_seconds)
                return self._send(200, b"<p>too late</p>")
            if path == "/fault/oversized":
                return self._send(200, b"<p>" + b"padding " * 1_000_000 + b"</p>")
            if path == "/fault/binary":
                return self._send(200, bytes(range(256)), "application/octet-stream")
            target = (root / path.lstrip("/")).resolve()
            if root.resolve() not in target.parents or not target.is_file():
                return self._send(404, b"not found")
            try:
                data = target.read_bytes()
            except OSError:
                return self._send(403, b"forbidden")
            ctype = "text/plain; charset=utf-8" if target.suffix == ".txt" else "text/html; charset=utf-8"
            if target.suffix in (".pdf", ".dat"):
                ctype = "application/octet-stream"
            return self._send(200, data, ctype)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def start(root: Path, slow_seconds: float = 30.0) -> ThreadingHTTPServer:
    server = make_server(root, slow_seconds)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--port", type=int, default=8901)
    args = parser.parse_args()
    make_server(args.root, port=args.port).serve_forever()
