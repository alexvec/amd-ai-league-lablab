"""The real socket transport, against a real local server. No DNS is involved."""

import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from trailmark.config import Limits
from trailmark.fetcher import FetchError, socket_transport
from trailmark.netguard import CheckedURL


class Handler(BaseHTTPRequestHandler):
    hosts = []

    def log_message(self, *_):
        pass

    def do_GET(self):
        Handler.hosts.append(self.headers.get("Host"))
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/elsewhere")
            self.end_headers()
            return
        if self.path == "/binary":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(b"\x00" * 10)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"a" * 300_000)


@pytest.fixture(scope="module")
def port():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_port
    server.shutdown()


def call(port, path, max_bytes=1_000_000, deadline=None, types=("text/html",)):
    target = CheckedURL("http", "pinned.example", port, path, f"http://pinned.example{path}")
    return socket_transport(target, "127.0.0.1", Limits(), deadline or time.monotonic() + 5, max_bytes, types)


def test_connects_to_pinned_address_and_sends_the_checked_host_name(port):
    response = call(port, "/page")
    assert response.status == 200 and Handler.hosts[-1].startswith("pinned.example")


def test_stops_reading_at_the_size_cap(port):
    response = call(port, "/page", max_bytes=70_000)
    assert response.truncated and len(response.body) < 300_000


def test_redirect_body_is_not_read(port):
    response = call(port, "/redirect")
    assert response.status == 302 and response.body == b""


def test_unwanted_content_type_body_is_not_read(port):
    assert call(port, "/binary").body == b""


def test_expired_deadline_raises(port):
    with pytest.raises(FetchError):
        call(port, "/page", deadline=time.monotonic() - 1)


class Dripper(socketserver.BaseRequestHandler):
    """Sends one byte at a time, each inside the read timeout, for as long as it is allowed to."""

    def handle(self):
        self.request.recv(4096)
        head = b"" if self.server.drip_headers else b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 100000\r\n\r\n"
        try:
            self.request.sendall(head or b"HTTP/1.1 200 OK\r\n")
            for _ in range(200):
                self.request.sendall(b"X-A: 1\r\n" if self.server.drip_headers else b"a")
                time.sleep(0.05)
        except OSError:
            pass


@pytest.mark.parametrize("drip_headers", [False, True], ids=["body", "headers"])
def test_slow_sender_cannot_outlast_the_deadline(drip_headers):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Dripper)
    server.daemon_threads = True
    server.drip_headers = drip_headers
    threading.Thread(target=server.serve_forever, daemon=True).start()
    started = time.monotonic()
    try:
        with pytest.raises(FetchError, match="time limit"):
            call(server.server_address[1], "/drip", deadline=time.monotonic() + 0.5)
    finally:
        server.shutdown()
    assert time.monotonic() - started < 3
