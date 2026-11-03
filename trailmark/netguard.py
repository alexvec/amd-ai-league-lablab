"""URL and address policy for fetching user-supplied URLs (SSRF defence).

Every hop goes through check_url() and resolve_public(). The fetcher then connects
to the address returned here and never resolves the name again, so DNS rebinding
cannot move a checked name onto a private address between check and connect.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

ALLOWED_SCHEMES = {"http": 80, "https": 443}
ALLOWED_PORTS = {80, 443}
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".intranet", ".lan", ".home", ".corp", ".arpa")
# Metadata and platform addresses that are not covered by the ranges below.
EXPLICIT_BLOCKS = {ipaddress.ip_address("168.63.129.16")}
NAT64 = ipaddress.ip_network("64:ff9b::/96")
NAT64_LOCAL = ipaddress.ip_network("64:ff9b:1::/48")
TEREDO = ipaddress.ip_network("2001::/32")
SIX_TO_FOUR = ipaddress.ip_network("2002::/16")


class BlockedURL(ValueError):
    """The URL or its address is outside the fetch policy."""


@dataclass(frozen=True)
class CheckedURL:
    scheme: str
    host: str  # lower-case; punycode for IDN; no brackets on IPv6
    port: int
    path_query: str
    url: str


def is_public_ip(value: str) -> bool:
    """True only for globally routable unicast addresses."""
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if ip in EXPLICIT_BLOCKS:
        return False
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))
        if ip in NAT64 or ip in NAT64_LOCAL or ip in TEREDO or ip in SIX_TO_FOUR:
            return False
    if ip.is_multicast or ip.is_loopback or ip.is_link_local or ip.is_private:
        return False
    if ip.is_reserved or ip.is_unspecified:
        return False
    return ip.is_global


def _looks_numeric(host: str) -> bool:
    """Decimal, hex and octal host spellings that resolvers may turn into addresses."""
    last = host.rsplit(".", 1)[-1]
    return bool(re.fullmatch(r"(0x[0-9a-f]*|[0-9]+)", last))


def origin_of(url: str) -> tuple[str, str, int]:
    """(scheme, lower-case host, port) of a configured URL, for the allowed_origins set."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise BlockedURL(f"not an http(s) origin: {url}")
    return scheme, parts.hostname.rstrip(".").lower(), parts.port or ALLOWED_SCHEMES[scheme]


def check_url(url: str, allowed_origins=frozenset()) -> CheckedURL:
    """Validate scheme, host form and port. Raises BlockedURL. Does no network I/O.

    allowed_origins holds (scheme, host, port) values taken only from the operator's contract
    config, never from a page or a question. An exact match may use a private address or a
    non-standard port, as a configured mirror host or internal proxy has to. Nothing else changes:
    the scheme, credential and control-character checks still apply, and any other host gets the
    full policy, including a redirect from an allowed origin to somewhere else.
    """
    if not isinstance(url, str) or not url.strip():
        raise BlockedURL("empty URL")
    url = url.strip()
    if len(url) > 2048:
        raise BlockedURL("URL too long")
    if "\\" in url or re.search(r"[\x00-\x20\x7f]", url):
        raise BlockedURL("URL contains control characters, spaces or backslashes")
    try:
        parts = urlsplit(url)
        raw_port = parts.port
    except ValueError as exc:
        raise BlockedURL(f"unparseable URL: {exc}") from exc
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise BlockedURL(f"scheme not allowed: {scheme or '(none)'}")
    if parts.username is not None or parts.password is not None:
        raise BlockedURL("credentials in URL are not allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise BlockedURL("URL has no host")
    port = raw_port or ALLOWED_SCHEMES[scheme]
    trusted = (scheme, host, port) in allowed_origins
    if port not in ALLOWED_PORTS and not trusted:
        raise BlockedURL(f"port not allowed: {port}")

    literal = None
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        pass
    if literal is not None:
        if not trusted and not is_public_ip(host):
            raise BlockedURL(f"address not allowed: {host}")
    else:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise BlockedURL("invalid host name") from exc
        if not trusted:
            if host == "localhost" or host.endswith(BLOCKED_SUFFIXES):
                raise BlockedURL(f"host not allowed: {host}")
            if "." not in host:
                raise BlockedURL(f"single-label host not allowed: {host}")
            if _looks_numeric(host):
                raise BlockedURL(f"numeric host form not allowed: {host}")

    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=~-._")
    query = quote(parts.query, safe="/%:@!$&'()*+,;=~-._?")
    path_query = path + (f"?{query}" if query else "")
    netloc = f"[{host}]" if literal is not None and literal.version == 6 else host
    if raw_port and raw_port != ALLOWED_SCHEMES[scheme]:
        netloc += f":{raw_port}"
    return CheckedURL(scheme, host, port, path_query, urlunsplit((scheme, netloc, path, query, "")))


def system_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(info[4][0] for info in infos))


def resolve_public(host: str, port: int, resolver=system_resolver, trusted: bool = False) -> list[str]:
    """Resolve host. Refuses if any answer is non-public, since a mixed answer is suspect.

    trusted is only true for an origin the operator configured (see check_url).
    """
    try:
        addresses = resolver(host, port)
    except OSError as exc:
        raise BlockedURL(f"could not resolve {host}: {exc}") from exc
    if not addresses:
        raise BlockedURL(f"no addresses for {host}")
    for address in addresses:
        if not trusted and not is_public_ip(address):
            raise BlockedURL(f"{host} resolves to a disallowed address: {address}")
    return addresses
