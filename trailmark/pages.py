"""The page source: one interface, mirror by default, proxy or live second. Selected by the contract.

A walk never raises for one page. Each page is either a Page or a PageFailure, and the walk goes on.
"""

from __future__ import annotations

import codecs
import os
import posixpath
import re
import stat
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator
from urllib.parse import quote, unquote, urlsplit

from .config import Limits
from .extract import build_snapshot, extract_parts, sha256_text
from .fetcher import Fetcher, FetchError, RobotsDenied, forward_proxy_transport
from .netguard import BlockedURL, check_url, origin_of

HTML_SUFFIXES = {".html", ".htm", ".xhtml", ".shtml"}
TEXT_SUFFIXES = {".txt", ".text", ".md", ".rst", ".log", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".py", ".sh", ".js", ".css"}
MIRROR_BASE = "http://mirror.invalid/"
DECLARED_CHARSET = re.compile(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9._:-]+)""", re.IGNORECASE)


@dataclass
class Page:
    ref: str  # corpus-relative path (mirror) or final URL (proxy). The citation comes from this.
    url: str
    title: str
    text: str
    sha256: str
    links: list[dict] = field(default_factory=list)  # {"ref": ..., "text": ...}
    chrome: str = ""
    truncated: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageFailure:
    ref: str
    kind: str
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class PageError(RuntimeError):
    pass


def decode_bytes(data: bytes, declared: str | None = None) -> tuple[str, list[str]]:
    """BOM, then the declared charset, then strict UTF-8, then cp1252. Never raises."""
    for bom, name in ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16")):
        if data.startswith(bom):
            return data.decode(name, "replace"), []
    match = DECLARED_CHARSET.search(data[:2048])
    names = [declared, match.group(1).decode("ascii", "ignore") if match else None, "utf-8"]
    for name in names:
        if not name:
            continue
        try:
            return data.decode(name), [] if name == names[0] or name.lower() in ("utf-8", "utf8") else ["charset_differs_from_declared"]
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("cp1252", "replace"), ["encoding_fallback_cp1252"]


def looks_binary(data: bytes) -> bool:
    sample = data[:8192]
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    control = sum(1 for byte in sample if byte < 9 or 13 < byte < 32)
    return control / len(sample) > 0.05


class MirrorSource:
    """A directory of saved pages. The citation is the path relative to the root."""

    mode = "mirror"

    def __init__(self, root: str | os.PathLike, base_url: str = "", max_bytes: int = 2_000_000, max_text_chars: int = 400_000, max_links: int = 300):
        self.root = Path(root)
        self.base_url = base_url.rstrip("/") + "/" if base_url else ""
        self.max_bytes = max_bytes
        self.max_text_chars = max_text_chars
        self.max_links = max_links

    def url_of(self, ref: str) -> str:
        return (self.base_url or MIRROR_BASE) + quote(ref)

    def _to_ref(self, url: str) -> str | None:
        for base in filter(None, (MIRROR_BASE, self.base_url)):
            if url.startswith(base):
                path = posixpath.normpath(unquote(urlsplit(url[len(base):]).path) or ".")
                if path.startswith("../") or path == "..":
                    return None
                return "" if path == "." else path
        return None

    def walk(self) -> Iterator[Page | PageFailure]:
        errors: list[PageFailure] = []

        def on_error(exc: OSError) -> None:
            errors.append(PageFailure(self._rel(exc.filename or str(self.root)), "unreadable_directory", type(exc).__name__))

        for directory, subdirs, files in os.walk(self.root, onerror=on_error, followlinks=False):
            subdirs.sort()
            yield from errors
            errors.clear()
            if not subdirs and not files and Path(directory) != self.root:
                yield PageFailure(self._rel(directory), "empty_directory")
            for name in sorted(files):
                rel = self._rel(os.path.join(directory, name))
                try:
                    yield self.read(rel)
                except PageError as exc:
                    kind, _, detail = str(exc).partition(": ")
                    yield PageFailure(rel, kind, detail)
                except Exception as exc:  # noqa: BLE001 - one bad page must not cost the rest
                    yield PageFailure(rel, "unexpected_error", f"{type(exc).__name__}: {exc}")
        yield from errors

    def _rel(self, path: str) -> str:
        return Path(path).relative_to(self.root).as_posix() if Path(path) != self.root else "."

    def read(self, ref: str) -> Page:
        """Read one page, or raise PageError("kind: detail")."""
        normal = posixpath.normpath(ref)
        if normal.startswith("../") or normal == ".." or normal.startswith("/"):
            raise PageError(f"outside_root: {ref}")
        path = self.root / normal
        try:
            info = path.lstat()
        except OSError as exc:
            raise PageError(f"unreadable: {type(exc).__name__}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise PageError("symlink_refused")
        if not stat.S_ISREG(info.st_mode):
            raise PageError("not_a_regular_file")
        try:
            with open(path, "rb") as handle:
                data = handle.read(self.max_bytes + 1)
        except OSError as exc:
            raise PageError(f"unreadable: {type(exc).__name__}") from exc
        truncated = len(data) > self.max_bytes
        data = data[: self.max_bytes]
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            kind = "encrypted_pdf" if b"/Encrypt" in data else "pdf_not_supported" if data.startswith(b"%PDF") else "corrupt_pdf"
            raise PageError(kind)
        if not data:
            raise PageError("empty_file")
        if looks_binary(data):
            raise PageError("binary_or_unknown_type")
        if suffix not in HTML_SUFFIXES and suffix not in TEXT_SUFFIXES and suffix:
            # An unknown suffix holding text is still read; only bytes decide it is binary.
            pass
        text, notes = decode_bytes(data)
        if truncated:
            notes.append("oversized_truncated")
        return self._page(normal, text, suffix, truncated, notes)

    def _page(self, ref: str, text: str, suffix: str, truncated: bool, notes: list[str]) -> Page:
        is_html = suffix in HTML_SUFFIXES or (not suffix and re.search(r"(?i)<html|<!doctype html", text[:2048]) is not None)
        if is_html:
            title, body, raw_links, chrome = extract_parts(text, MIRROR_BASE + quote(ref), self.max_links)
            links = []
            for link in raw_links:
                target = self._to_ref(link.url)
                if target is not None and target != ref:
                    links.append({"ref": target, "text": link.text})
        else:
            lines = (re.sub(r"[ \t\f\v\r]+", " ", line).strip() for line in text.split("\n"))
            title, body, links, chrome = "", "\n".join(line for line in lines if line), [], ""
        if not body.strip():
            raise PageError("no_readable_text")
        if len(body) > self.max_text_chars:
            body, truncated = body[: self.max_text_chars], True
        return Page(ref, self.url_of(ref), title, body, sha256_text(body), links, chrome, truncated, notes)


class HTTPSource:
    """Pages over HTTP: a configured internal host, a forward proxy, or (no proxy) the live web.

    Fetching is the guarded fetcher: only http(s), no private or link-local address unless the
    target is a configured origin, a check on every redirect, robots.txt, per-host delay, byte caps.
    """

    def __init__(self, seeds: list[str], allowed_hosts: list[str], proxy: str, limits: Limits, max_pages: int, walk_seconds: float, fetcher_factory=None):
        self.seeds = list(seeds)
        self.allowed = frozenset(origin_of(item) for item in allowed_hosts)
        self.limits = limits
        self.max_pages = max_pages
        self.walk_seconds = walk_seconds
        self.mode = "proxy" if proxy or allowed_hosts else "live"
        self.proxy_transport = None
        if proxy:
            parts = urlsplit(proxy)
            if parts.scheme != "http" or not parts.hostname:
                raise ValueError("pages.proxy must look like http://host:port")
            self.proxy_transport = forward_proxy_transport(parts.hostname, parts.port or 3128)
        self._factory = fetcher_factory or self._default_factory

    def _default_factory(self, deadline: float) -> Fetcher:
        return Fetcher(self.limits, deadline=deadline, allowed_origins=self.allowed, proxy_transport=self.proxy_transport)

    def _page(self, fetcher: Fetcher, url: str) -> Page:
        snapshot = build_snapshot(fetcher.fetch(url), self.limits)
        if not snapshot.text.strip():
            raise PageError("no_readable_text")
        links = [{"ref": link.url, "text": link.text} for link in snapshot.links]
        return Page(snapshot.final_url, snapshot.final_url, snapshot.title, snapshot.text, snapshot.sha256, links, snapshot.chrome, snapshot.truncated, [])

    def read(self, url: str, deadline: float | None = None) -> Page:
        fetcher = self._factory(deadline if deadline is not None else time.monotonic() + self.limits.request_seconds)
        try:
            return self._page(fetcher, url)
        except (BlockedURL, FetchError, RobotsDenied, OSError, ValueError) as exc:
            raise PageError(f"{type(exc).__name__}: {exc}") from exc

    def walk(self) -> Iterator[Page | PageFailure]:
        """Breadth first from the seeds, staying on the seeds' origins, within page and time caps."""
        stop = time.monotonic() + self.walk_seconds
        fetcher = self._factory(stop)
        origins = set()
        queue: deque[str] = deque()
        seen: set[str] = set()
        for seed in self.seeds:
            try:
                origins.add(origin_of(seed))
                queue.append(seed)
            except BlockedURL as exc:
                yield PageFailure(seed, "BlockedURL", str(exc))
        count = 0
        while queue and count < self.max_pages and time.monotonic() < stop:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            count += 1
            try:
                page = self._page(fetcher, url)
            except (BlockedURL, FetchError, RobotsDenied, PageError, OSError, ValueError) as exc:
                yield PageFailure(url, type(exc).__name__, str(exc)[:300])
                continue
            except Exception as exc:  # noqa: BLE001 - one bad page must not cost the rest
                yield PageFailure(url, "unexpected_error", f"{type(exc).__name__}: {exc}"[:300])
                continue
            seen.add(page.ref)
            yield page
            for link in page.links:
                try:
                    target = check_url(link["ref"], self.allowed)
                except BlockedURL:
                    continue
                if (target.scheme, target.host, target.port) in origins and target.url not in seen:
                    queue.append(target.url)
        for url in queue:
            if url not in seen:
                yield PageFailure(url, "walk_budget_reached")


def open_source(contract, index_path: str | None):
    """Build the source named by the contract."""
    pages = contract.section("pages")
    time_section = contract.section("time")
    if pages["mode"] == "mirror":
        root = pages["root"] or index_path
        if not root:
            raise ValueError("mirror mode needs pages.root or the path given to the index flag")
        return MirrorSource(root, pages["mirror_base_url"], int(pages["max_bytes"]), int(pages["max_text_chars"]))
    if pages["mode"] not in ("proxy", "live"):
        raise ValueError(f"unknown pages.mode: {pages['mode']}")
    if pages["mode"] == "live" and (pages["proxy"] or pages["allowed_hosts"]):
        raise ValueError("pages.mode live takes no proxy or allowed_hosts")
    seeds = list(pages["seeds"])
    if index_path and index_path.startswith(("http://", "https://")):
        seeds.append(index_path)
    seconds = float(pages["fetch_timeout_s"])
    limits = Limits(
        max_bytes=int(pages["max_bytes"]),
        max_text_chars=int(pages["max_text_chars"]),
        connect_timeout=min(5.0, seconds),
        read_timeout=seconds,
        per_fetch_seconds=seconds,
        request_seconds=seconds * 2,
        per_host_delay=float(pages["per_host_delay_s"]),
    )
    return HTTPSource(seeds, pages["allowed_hosts"], pages["proxy"], limits, int(pages["max_index_pages"]), float(time_section["startup_s"]) * float(pages["index_walk_share"]))
