"""Offline fakes. Nothing in the default suite touches the internet."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trailmark.config import Limits  # noqa: E402
from trailmark.fetcher import Fetcher, RawResponse  # noqa: E402

PUBLIC_IP = "93.184.216.34"


class FakeWeb:
    """Stands in for DNS and sockets. Records which address each request connected to."""

    def __init__(self):
        self.pages = {}
        self.dns = {}
        self.calls = []

    def add(self, url, body="", status=200, ctype="text/html; charset=utf-8", headers=None):
        merged = {"content-type": ctype, **(headers or {})}
        self.pages[url] = RawResponse(status, merged, body.encode() if isinstance(body, str) else body)

    def resolver(self, host, port):
        return self.dns.get(host, [PUBLIC_IP])

    def transport(self, target, ip, limits, deadline, max_bytes, accept_types):
        self.calls.append((target.url, ip))
        response = self.pages.get(target.url)
        if response is None:
            return RawResponse(404, {"content-type": "text/html"}, b"not found")
        body = response.body[:max_bytes]
        return RawResponse(response.status, response.headers, body, len(response.body) > max_bytes)

    def fetcher(self, limits=None, **kwargs):
        kwargs.setdefault("sleep", lambda _: None)
        return Fetcher(limits or Limits(), resolver=self.resolver, transport=self.transport, **kwargs)

    def factory(self, limits, on_event=None, deadline=None):
        return Fetcher(limits, resolver=self.resolver, transport=self.transport, on_event=on_event, deadline=deadline, sleep=lambda _: None)


@pytest.fixture
def web():
    fake = FakeWeb()
    fake.add("https://site.example/robots.txt", "User-agent: *\nDisallow: /private/\n", ctype="text/plain")
    return fake


@pytest.fixture
def stub_model():
    """OpenAI-compatible stub. Set .replies to a list of JSON objects or raw strings."""

    class State:
        replies = []
        requests = []
        owned_by = "stub-server"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, payload):
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send({"data": [{"id": "stub-model", "owned_by": State.owned_by}]})

        def do_POST(self):
            size = int(self.headers.get("Content-Length", 0))
            State.requests.append({"body": json.loads(self.rfile.read(size)), "auth": self.headers.get("Authorization")})
            reply = State.replies.pop(0) if State.replies else {"action": "give_up", "reason": "stub is out of replies"}
            content = reply if isinstance(reply, str) else json.dumps(reply)
            self._send(
                {
                    "model": "stub-model",
                    "choices": [{"message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 7},
                }
            )

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    State.replies, State.requests = [], []
    State.base_url = f"http://127.0.0.1:{server.server_port}/v1"
    yield State
    server.shutdown()
