"""Offline fakes. Nothing in the default suite touches the internet, and none of it needs a GPU or a model."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for entry in (ROOT, ROOT / "app", ROOT / "tools"):
    sys.path.insert(0, str(entry))

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


@pytest.fixture
def web():
    fake = FakeWeb()
    fake.add("https://site.example/robots.txt", "User-agent: *\nDisallow: /private/\n", ctype="text/plain")
    return fake
