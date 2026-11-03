"""PRD acceptance test 6, plus redirect, DNS rebinding and limit behaviour."""

import gzip

import pytest

from trailmark.config import Limits
from trailmark.fetcher import FetchError, RobotsDenied
from trailmark.netguard import BlockedURL, check_url, is_public_ip, resolve_public

from .conftest import PUBLIC_IP


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd", "ftp://example.com/", "gopher://example.com/", "javascript:alert(1)", "data:text/html,x",
        "http://localhost/", "http://foo.localhost/", "http://db.internal/", "http://printer.local/", "http://intranet/",
        "http://127.0.0.1/", "http://10.0.0.1/", "http://172.16.0.1/", "http://192.168.1.1/", "http://169.254.169.254/latest/meta-data/",
        "http://100.100.100.200/", "http://168.63.129.16/", "http://0.0.0.0/", "http://[::1]/", "http://[fe80::1]/", "http://[fd00:ec2::254]/",
        "http://[::ffff:127.0.0.1]/", "http://[::ffff:169.254.169.254]/", "http://[64:ff9b::7f00:1]/", "http://[2002:7f00:1::]/",
        "http://2130706433/", "http://0x7f000001/", "http://0x7f.0.0.1/", "http://0177.0.0.1/", "http://127.1/",
        "http://user:pass@example.com/", "http://example.com:22/", "https://example.com:8443/", "http://exa mple.com/", "http://example.com\\@10.0.0.1/", "",
    ],
)
def test_refused_urls(url):
    with pytest.raises(BlockedURL):
        check_url(url)


@pytest.mark.parametrize("url", ["https://example.com/", "http://example.com/a?b=c", "https://93.184.216.34/", "https://example.com:443/x"])
def test_allowed_urls(url):
    assert check_url(url).host


def test_fragment_is_dropped_and_path_encoded():
    assert check_url("https://example.com/a b#frag".replace(" ", "%20")).url == "https://example.com/a%20b"


@pytest.mark.parametrize(
    "ip,public",
    [
        ("8.8.8.8", True), ("2606:4700:4700::1111", True), ("127.0.0.1", False), ("10.1.1.1", False), ("100.64.0.1", False),
        ("169.254.169.254", False), ("192.0.2.1", False), ("224.0.0.1", False), ("240.0.0.1", False), ("255.255.255.255", False),
        ("::", False), ("::1", False), ("fc00::1", False), ("ff02::1", False), ("::ffff:10.0.0.1", False), ("2001:db8::1", False), ("not-an-ip", False),
    ],
)
def test_is_public_ip(ip, public):
    assert is_public_ip(ip) is public


def test_name_resolving_to_private_address_is_refused():
    with pytest.raises(BlockedURL):
        resolve_public("evil.example", 80, lambda *_: ["10.0.0.5"])


def test_mixed_public_and_private_answer_is_refused():
    with pytest.raises(BlockedURL):
        resolve_public("evil.example", 80, lambda *_: ["8.8.8.8", "127.0.0.1"])


def test_redirect_to_private_ip_is_refused_and_never_connected(web):
    web.add("https://site.example/go", status=302, headers={"location": "http://169.254.169.254/latest/meta-data/"})
    with pytest.raises(BlockedURL):
        web.fetcher().fetch("https://site.example/go")
    assert not [ip for _, ip in web.calls if ip != PUBLIC_IP]
    assert not [url for url, _ in web.calls if "169.254" in url]


def test_redirect_to_name_resolving_private_is_refused(web):
    web.dns["rebind.example"] = ["192.168.0.10"]
    web.add("https://site.example/go", status=301, headers={"location": "https://rebind.example/admin"})
    with pytest.raises(BlockedURL):
        web.fetcher().fetch("https://site.example/go")
    assert all(ip == PUBLIC_IP for _, ip in web.calls)


def test_redirect_to_disallowed_scheme_is_refused(web):
    web.add("https://site.example/go", status=302, headers={"location": "file:///etc/passwd"})
    with pytest.raises(BlockedURL):
        web.fetcher().fetch("https://site.example/go")


def test_dns_rebinding_between_hops_is_caught(web):
    answers = iter([[PUBLIC_IP]] * 6 + [["127.0.0.1"]] * 6)
    web.resolver = lambda *_: next(answers)
    web.add("https://site.example/go", status=302, headers={"location": "https://site.example/next"})
    with pytest.raises((BlockedURL, FetchError, RobotsDenied)):
        web.fetcher().fetch("https://site.example/go")
    assert all(ip == PUBLIC_IP for _, ip in web.calls)


def test_connection_uses_the_checked_address(web):
    web.dns["site.example"] = ["203.0.114.9"]
    web.add("https://site.example/a", "<p>hello</p>")
    web.fetcher().fetch("https://site.example/a")
    assert ("https://site.example/a", "203.0.114.9") in web.calls


def test_redirect_loop_is_bounded(web):
    web.add("https://site.example/a", status=302, headers={"location": "/b"})
    web.add("https://site.example/b", status=302, headers={"location": "/a"})
    with pytest.raises(FetchError):
        web.fetcher().fetch("https://site.example/a")


def test_robots_disallow_is_respected(web):
    web.add("https://site.example/private/x", "<p>secret</p>")
    with pytest.raises(RobotsDenied):
        web.fetcher().fetch("https://site.example/private/x")
    assert "https://site.example/private/x" not in [url for url, _ in web.calls]


def test_robots_checked_on_redirect_hop(web):
    web.add("https://site.example/go", status=302, headers={"location": "/private/x"})
    web.add("https://site.example/private/x", "<p>secret</p>")
    with pytest.raises(RobotsDenied):
        web.fetcher().fetch("https://site.example/go")


def test_response_size_is_capped(web):
    web.add("https://site.example/big", "<p>" + "a" * 5000 + "</p>")
    result = web.fetcher(Limits(max_bytes=1000)).fetch("https://site.example/big")
    assert result.truncated and len(result.body) <= 1000


def test_gzip_expansion_is_capped(web):
    web.add("https://site.example/bomb", gzip.compress(b"a" * 5_000_000), headers={"content-encoding": "gzip"})
    result = web.fetcher(Limits(max_bytes=10_000)).fetch("https://site.example/bomb")
    assert result.truncated and len(result.body) <= 10_000


def test_non_text_content_is_refused(web):
    web.add("https://site.example/a.bin", b"\x00\x01", ctype="application/octet-stream")
    with pytest.raises(FetchError):
        web.fetcher().fetch("https://site.example/a.bin")


def test_deadline_stops_fetching(web):
    import time

    web.add("https://site.example/a", "<p>hello</p>")
    with pytest.raises(FetchError):
        web.fetcher(deadline=time.monotonic() - 1).fetch("https://site.example/a")


def test_malformed_redirect_target_is_refused_not_a_crash(web):
    web.add("https://site.example/go", status=302, headers={"location": "http://[bad"})
    with pytest.raises(BlockedURL):
        web.fetcher().fetch("https://site.example/go")
