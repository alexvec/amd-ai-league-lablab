"""Readable-text and link extraction, and the stored page snapshot.

Page content is data. Text hidden from readers is dropped because it is a common
place to hide instructions aimed at a model.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

SKIP_TEXT = {"nav", "footer", "aside", "form", "button", "select", "header"}
SKIP_ALL = {"script", "style", "noscript", "template", "svg", "canvas", "iframe", "object", "embed", "textarea", "math"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {
    "address", "article", "blockquote", "br", "caption", "dd", "details", "div", "dl", "dt", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "main", "ol", "p", "pre", "section", "summary", "table", "tbody",
    "thead", "tfoot", "tr", "ul",
}
NOISE_CLASSES = ("reference", "mw-editsection", "visually-hidden", "sr-only")


@dataclass
class Link:
    url: str
    text: str


@dataclass
class Snapshot:
    url: str
    final_url: str
    title: str
    text: str
    sha256: str
    fetched_at: str
    truncated: bool = False
    links: list[Link] = field(default_factory=list)
    chrome: str = ""

    def public_dict(self, include_text: bool = True) -> dict:
        data = {
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "sha256": self.sha256,
            "fetched_at": self.fetched_at,
            "truncated": self.truncated,
            "chars": len(self.text),
        }
        if include_text:
            data["text"] = self.text
        return data


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_hidden(attrs: dict) -> bool:
    if "hidden" in attrs or attrs.get("aria-hidden") == "true":
        return True
    style = (attrs.get("style") or "").replace(" ", "").lower()
    return "display:none" in style or "visibility:hidden" in style


class _Reader(HTMLParser):
    def __init__(self, base_url: str, max_links: int):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.max_links = max_links
        self.lines: list[str] = []
        self.buffer: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.stack: list[tuple[str, bool]] = []  # (tag, blocks links as well as text)
        self.anchor: tuple[str, list[str]] | None = None
        self.links: list[Link] = []
        self.seen: set[str] = set()
        self.chrome: list[str] = []  # nav, header and similar. Used only to spot a "withdrawn" banner.

    def _flush(self) -> None:
        line = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
        self.buffer = []
        if line:
            self.lines.append(line)

    def _noisy(self, attrs: dict) -> bool:
        classes = (attrs.get("class") or "").split()
        return any(name in classes for name in NOISE_CLASSES)

    def handle_starttag(self, tag, attrs):
        attr = {k: (v or "") for k, v in attrs}
        if tag == "base" and attr.get("href"):
            try:
                self.base = urljoin(self.base, attr["href"])
            except ValueError:
                pass  # A malformed base from the page is ignored.
        if tag == "title" and not self.stack:
            self.in_title = True
        if tag in VOID:
            if tag in BLOCK:
                self._flush()
            return
        if tag in SKIP_ALL or _is_hidden(attr):
            self.stack.append((tag, True))
            return
        # Inside a skipped region every tag is tracked, so a nested closing tag of the
        # same name cannot end the region early and expose hidden text.
        if self.stack or tag in SKIP_TEXT or self._noisy(attr):
            self.stack.append((tag, False))
        if tag == "a" and attr.get("href") and not any(full for _, full in self.stack):
            self.anchor = (attr["href"], [])
        if not self.stack:
            if tag in BLOCK:
                self._flush()
            elif tag in ("td", "th") and self.buffer:
                self.buffer.append(" | ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.anchor:
            self._finish_anchor()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return
        if not self.stack and tag in BLOCK:
            self._flush()

    def _finish_anchor(self):
        href, parts = self.anchor
        self.anchor = None
        if len(self.links) >= self.max_links:
            return
        try:
            url = urldefrag(urljoin(self.base, unescape(href).strip())).url
            scheme = urlsplit(url).scheme.lower()
        except ValueError:
            return
        if scheme not in ("http", "https") or url in self.seen:
            return
        self.seen.add(url)
        self.links.append(Link(url, re.sub(r"\s+", " ", "".join(parts)).strip()[:200]))

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
            return
        if any(full for _, full in self.stack):
            return
        if self.anchor:
            self.anchor[1].append(data)
        if not self.stack:
            self.buffer.append(data)
        elif data.strip():
            self.chrome.append(data.strip())

    def close(self):
        super().close()
        self._flush()


def extract_parts(html: str, base_url: str, max_links: int = 300) -> tuple[str, str, list[Link], str]:
    """(title, readable text, links, chrome text). Hidden text appears in none of them."""
    reader = _Reader(base_url, max_links)
    reader.feed(html)
    reader.close()
    title = re.sub(r"\s+", " ", "".join(reader.title_parts)).strip()[:300]
    return title, "\n".join(reader.lines), reader.links, "\n".join(reader.chrome)[:2000]


def extract_html(html: str, base_url: str, max_links: int = 300) -> tuple[str, str, list[Link]]:
    return extract_parts(html, base_url, max_links)[:3]


def build_snapshot(result, limits) -> Snapshot:
    try:
        decoded = result.body.decode(result.charset, "replace")
    except LookupError:
        decoded = result.body.decode("utf-8", "replace")
    if result.content_type == "text/plain":
        lines = (re.sub(r"[ \t\f\v\r]+", " ", line).strip() for line in decoded.split("\n"))
        title, text, links, chrome = "", "\n".join(line for line in lines if line), [], ""
    else:
        title, text, links, chrome = extract_parts(decoded, result.final_url, limits.max_links)
    truncated = result.truncated or len(text) > limits.max_text_chars
    text = text[: limits.max_text_chars]
    return Snapshot(
        url=result.url,
        final_url=result.final_url,
        title=title,
        text=text,
        sha256=sha256_text(text),
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        truncated=truncated,
        links=links,
        chrome=chrome,
    )
