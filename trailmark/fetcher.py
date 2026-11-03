"""Guarded HTTP fetcher. Standard library only, so it runs anywhere the agent runs."""

from __future__ import annotations

import http.client
import socket
import ssl
import threading
import time
import zlib
from dataclasses import dataclass, field
from urllib.parse import urljoin

from . import robots as robots_mod
from .config import ROBOTS_TOKEN, USER_AGENT, Limits
from .netguard import BlockedURL, CheckedURL, check_url, resolve_public, system_resolver

TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
REDIRECTS = {301, 302, 303, 307, 308}
DEADLINE_MESSAGE = "time limit reached while reading the response"


class FetchError(RuntimeError):
    """Network, size, type or deadline failure."""


class RobotsDenied(RuntimeError):
    """robots.txt disallows this URL for our agent token."""


@dataclass
class RawResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    truncated: bool = False


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    charset: str
    body: bytes
    truncated: bool
    hops: list[str] = field(default_factory=list)


class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, ip, connect_timeout, read_timeout):
        super().__init__(host, port, timeout=read_timeout)
        self._ip, self._connect_timeout = ip, connect_timeout

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self._connect_timeout)
        self.sock.settimeout(self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, ip, connect_timeout, read_timeout):
        super().__init__(host, port, timeout=read_timeout, context=ssl.create_default_context())
        self._ip, self._connect_timeout = ip, connect_timeout

    def connect(self):
        raw = socket.create_connection((self._ip, self.port), self._connect_timeout)
        raw.settimeout(self.timeout)
        # Published before the handshake, so the deadline watchdog can also stop a slow handshake.
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host, do_handshake_on_connect=False)
        self.sock.do_handshake()


def socket_transport(target: CheckedURL, ip: str, limits: Limits, deadline: float, max_bytes: int, accept_types) -> RawResponse:
    """Connect to the checked address, never to a freshly resolved name."""
    cls = _PinnedHTTPS if target.scheme == "https" else _PinnedHTTP
    conn = cls(target.host, target.port, ip, limits.connect_timeout, limits.read_timeout)
    return _exchange(conn, target.path_query, {}, limits, deadline, max_bytes, accept_types)


def forward_proxy_transport(proxy_host: str, proxy_port: int):
    """A transport that sends every request through a configured forward proxy.

    http targets use an absolute-form GET. https targets use CONNECT, then verify the target's
    certificate. Name resolution happens at the proxy, so the fetcher's own DNS check cannot run
    on this path; check_url's host policy still does, and the proxy is the rest of the boundary.
    The CONNECT branch has not been exercised, because no TLS test server exists in this repo.
    """

    def transport(target: CheckedURL, _ip: str, limits: Limits, deadline: float, max_bytes: int, accept_types) -> RawResponse:
        if target.scheme == "https":
            conn = http.client.HTTPSConnection(proxy_host, proxy_port, timeout=limits.read_timeout, context=ssl.create_default_context())
            conn.set_tunnel(target.host, target.port)
            return _exchange(conn, target.path_query, {}, limits, deadline, max_bytes, accept_types)
        conn = http.client.HTTPConnection(proxy_host, proxy_port, timeout=limits.read_timeout)
        netloc = target.host if target.port == 80 else f"{target.host}:{target.port}"
        return _exchange(conn, target.url, {"Host": netloc}, limits, deadline, max_bytes, accept_types)

    return transport


def _exchange(conn, request_target: str, extra_headers: dict, limits: Limits, deadline: float, max_bytes: int, accept_types) -> RawResponse:
    """The read timeout only bounds one recv, so a server sending one byte at a time could
    outlast it forever. The watchdog shuts the socket at the deadline to stop that.
    """
    expired = threading.Event()

    def expire() -> None:
        expired.set()
        sock = conn.sock
        if sock is not None:
            try:
                socket.socket.shutdown(sock, socket.SHUT_RDWR)
            except OSError:
                pass

    watchdog = threading.Timer(max(0.0, deadline - time.monotonic()), expire)
    watchdog.daemon = True
    watchdog.start()
    try:
        conn.request(
            "GET",
            request_target,
            headers={
                **extra_headers,
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,application/json;q=0.5",
                "Accept-Encoding": "gzip",
                "Connection": "close",
            },
        )
        resp = conn.getresponse()
        headers = {k.lower(): v for k, v in resp.getheaders()}
        if resp.status in REDIRECTS:
            return RawResponse(resp.status, headers, b"")
        ctype = headers.get("content-type", "").split(";")[0].strip().lower()
        if accept_types and 200 <= resp.status < 300 and ctype and ctype not in accept_types:
            return RawResponse(resp.status, headers, b"")
        chunks, total, truncated = [], 0, False
        while True:
            chunk = resp.read(65536)
            if expired.is_set():
                raise FetchError(DEADLINE_MESSAGE)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total >= max_bytes:
                truncated = True
                break
        return RawResponse(resp.status, headers, b"".join(chunks)[:max_bytes], truncated)
    except (OSError, http.client.HTTPException):
        if expired.is_set():
            raise FetchError(DEADLINE_MESSAGE) from None
        raise
    finally:
        watchdog.cancel()
        conn.close()


def _decode_body(raw: RawResponse, max_bytes: int) -> tuple[bytes, bool]:
    if raw.headers.get("content-encoding", "").strip().lower() != "gzip":
        return raw.body, raw.truncated
    # max_length caps expansion, so a compression bomb cannot exhaust memory.
    engine = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        data = engine.decompress(raw.body, max_bytes)
    except zlib.error as exc:
        raise FetchError(f"bad gzip body: {exc}") from exc
    return data, raw.truncated or bool(engine.unconsumed_tail)


def _redirect_target(base: str, location: str, allowed_origins=frozenset()) -> CheckedURL:
    try:
        joined = urljoin(base, location)
    except ValueError as exc:
        raise BlockedURL(f"unparseable redirect target: {exc}") from exc
    return check_url(joined, allowed_origins)


class Fetcher:
    """One instance per request: it holds that request's robots cache and politeness clock."""

    def __init__(self, limits: Limits, resolver=system_resolver, transport=socket_transport, on_event=None, sleep=time.sleep, deadline: float | None = None, allowed_origins=frozenset(), proxy_transport=None):
        self.limits = limits
        self.allowed_origins = frozenset(allowed_origins)
        self.proxy_transport = proxy_transport
        self.resolver = resolver
        self.transport = transport
        self.on_event = on_event or (lambda **_: None)
        self.sleep = sleep
        self.deadline = deadline if deadline is not None else time.monotonic() + limits.request_seconds
        self._robots: dict[str, robots_mod.Robots] = {}
        self._last_hit: dict[str, float] = {}

    def _remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise FetchError("request time limit reached")
        return remaining

    def _polite_wait(self, host: str) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.limits.per_host_delay - (time.monotonic() - last)
            if wait > 0:
                self.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def _route(self, target: CheckedURL) -> tuple[list[str], object]:
        """Addresses to try and the transport to use. Configured origins go direct, never via the proxy."""
        trusted = (target.scheme, target.host, target.port) in self.allowed_origins
        if self.proxy_transport is not None and not trusted:
            return ["forward-proxy"], self.proxy_transport
        return resolve_public(target.host, target.port, self.resolver, trusted=trusted), self.transport

    def _one_hop(self, target: CheckedURL, max_bytes: int, accept_types) -> RawResponse:
        addresses, transport = self._route(target)
        self._polite_wait(target.host)
        last_error: Exception | None = None
        for ip in addresses:
            budget = min(self._remaining(), self.limits.per_fetch_seconds)
            try:
                return transport(target, ip, self.limits, time.monotonic() + budget, max_bytes, accept_types)
            except FetchError:
                raise
            except (OSError, http.client.HTTPException) as exc:
                last_error = exc
        raise FetchError(f"could not fetch {target.url}: {last_error}")

    def _robots_for(self, target: CheckedURL) -> robots_mod.Robots:
        origin = f"{target.scheme}://{target.host}:{target.port}"
        if origin in self._robots:
            return self._robots[origin]
        netloc = f"[{target.host}]" if ":" in target.host else target.host
        if target.port not in (80, 443):
            netloc += f":{target.port}"
        url = f"{target.scheme}://{netloc}/robots.txt"
        try:
            current = check_url(url, self.allowed_origins)
            status, body = 0, b""
            for _ in range(self.limits.max_redirects + 1):
                raw = self._one_hop(current, self.limits.max_robots_bytes, None)
                status, body = raw.status, _decode_body(raw, self.limits.max_robots_bytes)[0]
                if raw.status in REDIRECTS and raw.headers.get("location"):
                    current = _redirect_target(current.url, raw.headers["location"], self.allowed_origins)
                    continue
                break
            policy = robots_mod.from_status(status, body.decode("utf-8", "replace"), ROBOTS_TOKEN)
            self.on_event(type="robots", url=url, status=status, note="deny_all" if policy.deny_all else "parsed")
        except (BlockedURL, FetchError) as exc:
            # RFC 9309: unreachable robots.txt means assume disallowed.
            policy = robots_mod.Robots(deny_all=True)
            self.on_event(type="robots", url=url, status=None, note=f"unreachable, assuming denied: {exc}")
        self._robots[origin] = policy
        return policy

    def fetch(self, url: str, accept_types=TEXT_TYPES) -> FetchResult:
        """GET with the URL policy, DNS check and robots check applied on every hop."""
        current = check_url(url, self.allowed_origins)
        hops: list[str] = []
        for _ in range(self.limits.max_redirects + 1):
            self._remaining()
            self._route(current)
            if not self._robots_for(current).allowed(current.path_query):
                raise RobotsDenied(f"robots.txt disallows {current.url}")
            raw = self._one_hop(current, self.limits.max_bytes, accept_types)
            hops.append(current.url)
            if raw.status in REDIRECTS:
                location = raw.headers.get("location")
                if not location:
                    raise FetchError(f"redirect without a location from {current.url}")
                current = _redirect_target(current.url, location, self.allowed_origins)
                continue
            header = raw.headers.get("content-type", "")
            ctype = header.split(";")[0].strip().lower()
            charset = "utf-8"
            if "charset=" in header.lower():
                charset = header.lower().split("charset=", 1)[1].split(";")[0].strip().strip('"\'') or "utf-8"
            if not 200 <= raw.status < 300:
                raise FetchError(f"HTTP {raw.status} from {current.url}")
            if accept_types and ctype not in accept_types:
                raise FetchError(f"content type not supported: {ctype or '(none)'}")
            body, truncated = _decode_body(raw, self.limits.max_bytes)
            return FetchResult(url, current.url, raw.status, ctype, charset, body, truncated, hops)
        raise FetchError(f"too many redirects from {url}")
