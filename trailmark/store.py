"""The persisted index, read by each short-lived query process."""

from __future__ import annotations

import json
import posixpath
from pathlib import Path

from . import bm25
from .pages import Page


class IndexMissing(RuntimeError):
    pass


class PageStore:
    def __init__(self, directory: str | Path):
        directory = Path(directory)
        try:
            self.meta = json.loads((directory / "meta.json").read_text("utf-8"))
            self.failures = json.loads((directory / "failures.json").read_text("utf-8"))
            self.bm25 = json.loads((directory / "bm25.json").read_text("utf-8"))
            lines = (directory / "pages.jsonl").read_text("utf-8").splitlines()
        except (OSError, ValueError) as exc:
            raise IndexMissing(f"no usable index at {directory}: {type(exc).__name__}") from exc
        self.pages: dict[str, Page] = {}
        for line in lines:
            page = Page(**json.loads(line))
            self.pages[page.ref] = page

    def search(self, query: str, limit: int = 20) -> list[str]:
        return [ref for ref, _ in bm25.search(self.bm25, query, limit)]

    def resolve(self, ref: str) -> str | None:
        """Map a link target to a stored page. Saved sites link to directories and bare names."""
        candidates = [ref]
        if self.meta.get("mode") == "mirror":
            clean = posixpath.normpath(ref) if ref else ""
            candidates = [clean, posixpath.join(clean, "index.html"), f"{clean}.html"]
        return next((item for item in candidates if item in self.pages), None)


def write_index(directory: Path, pages: list[Page], failures: list[dict], meta: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "pages.jsonl", "w", encoding="utf-8") as out:
        for page in pages:
            out.write(json.dumps(page.to_dict(), ensure_ascii=False) + "\n")
    (directory / "bm25.json").write_text(json.dumps(bm25.build([page.to_dict() for page in pages])), "utf-8")
    (directory / "failures.json").write_text(json.dumps(failures, indent=1), "utf-8")
    (directory / "meta.json").write_text(json.dumps(meta, indent=1), "utf-8")
