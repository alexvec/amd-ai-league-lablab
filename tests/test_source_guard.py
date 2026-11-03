"""PRD acceptance test 8, the part new to this rebuild: configured origins pass, nothing else does."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from trailmark.config import Limits
from trailmark.fetcher import FetchError, Fetcher, forward_proxy_transport
from trailmark.netguard import BlockedURL, check_url, origin_of, resolve_public
from trailmark.pages import HTTPSource, PageError

ALLOWED = frozenset({origin_of("http://10.0.0.5:8080")})
FAST = Limits(per_host_delay=0.0, connect_timeout=1, read_timeout=1, per_fetch_seconds=1, request_seconds=3)


def test_configured_origin_may_be_private_on_any_port():
    assert check_url("http://10.0.0.5:8080/page", ALLOWED).port == 8080


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.5/page", "http://10.0.0.5:8081/page", "https://10.0.0.5:8080/page", "http://10.0.0.6:8080/", "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8080/", "http://localhost:8080/", "file:///etc/passwd", "ftp://10.0.0.5:8080/", "http://user:pw@10.0.0.5:8080/",
    ],
)
def test_anything_else_is_refused_even_with_an_origin_configured(url):
    with pytest.raises(BlockedURL):
        check_url(url, ALLOWED)


def test_no_origin_means_the_full_policy_applies():
    with pytest.raises(BlockedURL):
        check_url("http://10.0.0.5:8080/page")


def test_private_answer_passes_only_for_a_trusted_origin():
    with pytest.raises(BlockedURL):
        resolve_public("pages.internal", 80, lambda *_: ["10.0.0.5"])
    assert resolve_public("pages.internal", 80, lambda *_: ["10.0.0.5"], trusted=True) == ["10.0.0.5"]


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *_):
        pass

    def do_GET(self):  # noqa: N802
        Handler.seen.append((self.path, self.headers.get("Host")))
        if self.path.endswith("/robots.txt"):
            self.send_response(404)
            self.end_headers()
            return
        if self.path.endswith("/to-metadata"):
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<title>t</title><p>Served through the configured route.</p>")


@pytest.fixture
def server():
    Handler.seen = []
    instance = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=instance.serve_forever, daemon=True).start()
    yield instance
    instance.shutdown()


def test_configured_host_is_fetched_and_a_redirect_off_it_is_refused(server):
    origin = f"http://127.0.0.1:{server.server_port}"
    source = HTTPSource([], [origin], "", FAST, 10, 5.0)
    assert "configured route" in source.read(f"{origin}/page").text
    with pytest.raises(PageError, match="BlockedURL"):
        source.read(f"{origin}/to-metadata")
    assert not any("meta-data" in path for path, _ in Handler.seen)


def test_loopback_is_refused_when_not_configured(server):
    source = HTTPSource([], [], "", FAST, 10, 5.0)
    with pytest.raises(PageError, match="BlockedURL"):
        source.read(f"http://127.0.0.1:{server.server_port}/page")
    assert Handler.seen == []


def test_forward_proxy_gets_an_absolute_form_request_for_a_public_name(server):
    transport = forward_proxy_transport("127.0.0.1", server.server_port)
    def no_dns(*_):
        raise AssertionError("the proxy resolves names, not us")
    fetcher = Fetcher(FAST, resolver=no_dns, proxy_transport=transport, sleep=lambda _: None)
    result = fetcher.fetch("http://pages.example/page")
    assert result.status == 200
    assert ("http://pages.example/page", "pages.example") in Handler.seen


def test_forward_proxy_does_not_widen_the_url_policy(server):
    fetcher = Fetcher(FAST, proxy_transport=forward_proxy_transport("127.0.0.1", server.server_port), sleep=lambda _: None)
    for url in ("http://169.254.169.254/latest/meta-data/", "http://localhost/", "file:///etc/passwd"):
        with pytest.raises(BlockedURL):
            fetcher.fetch(url)
    assert Handler.seen == []


def test_robots_is_read_from_the_configured_port(server):
    origin = f"http://127.0.0.1:{server.server_port}"
    HTTPSource([], [origin], "", FAST, 10, 5.0).read(f"{origin}/page")
    assert Handler.seen[0][0] == "/robots.txt" and Handler.seen[0][1].endswith(str(server.server_port))


def test_fetch_body_never_exceeds_the_cap(server, monkeypatch):
    class Big(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"a" * 500_000)

    big = HTTPServer(("127.0.0.1", 0), Big)
    threading.Thread(target=big.serve_forever, daemon=True).start()
    try:
        from trailmark.fetcher import socket_transport
        from trailmark.netguard import CheckedURL

        target = CheckedURL("http", "pinned.example", big.server_port, "/x", "http://pinned.example/x")
        import time

        response = socket_transport(target, "127.0.0.1", FAST, time.monotonic() + 3, 100_000, ("text/html",))
        assert response.truncated and len(response.body) == 100_000
    finally:
        big.shutdown()


def test_dead_host_is_a_fetch_error_not_a_hang():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    origin = f"http://127.0.0.1:{port}"
    fetcher = Fetcher(FAST, allowed_origins=frozenset({origin_of(origin)}), sleep=lambda _: None)
    with pytest.raises((FetchError, Exception)):
        fetcher.fetch(f"{origin}/page")
