"""Loads the contract and is the only place that turns it into CLI flags, paths and output keys.

Environment variables exist so the same code can run where /app does not exist (a Mac, a notebook).
They are never set in the image.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAFE_QUERY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ENV_OVERRIDES = {
    "MC4_OUTPUT_DIR": ("output", "dir"),
    "MC4_INDEX_DIR": ("paths", "index_dir"),
    "MC4_RUN_DIR": ("paths", "run_dir"),
    "MC4_MODEL_DIR": ("service", "model_dir"),
    "MC4_MODEL_NAME": ("service", "model_name"),
    "MC4_BACKEND": ("service", "backend"),
    "MC4_PAGES_MODE": ("pages", "mode"),
    "MC4_PROXY": ("pages", "proxy"),
}


class BadQueryId(ValueError):
    pass


@dataclass(frozen=True)
class Contract:
    data: dict
    source: str

    def section(self, name: str) -> dict:
        return self.data[name]

    @property
    def index_dir(self) -> Path:
        return Path(self.data["paths"]["index_dir"])

    @property
    def run_dir(self) -> Path:
        return Path(self.data["paths"]["run_dir"])

    @property
    def socket_path(self) -> Path:
        return self.run_dir / self.data["service"]["socket_name"]

    def query_seconds(self) -> float:
        """Seconds a query may work before it must refuse."""
        return max(0.5, float(self.data["time"]["query_s"]) - float(self.data["time"]["margin_s"]))

    def cite_form(self) -> str:
        form = self.data["output"]["cite_form"]
        if form != "auto":
            return form
        return "path" if self.data["pages"]["mode"] == "mirror" else "url"

    def output_path(self, query_id: str) -> Path:
        """The id is given by the harness, but it still must not be able to leave the output dir."""
        if not SAFE_QUERY_ID.match(query_id or ""):
            raise BadQueryId(f"unsafe query id: {query_id!r}")
        return Path(self.data["output"]["dir"]) / self.data["output"]["filename"].format(query_id=query_id)

    def payload(self, answer: str, citations: list[str], confidence: float) -> dict:
        keys = self.data["output"]["keys"]
        return {keys["answer"]: answer, keys["citations"]: list(citations), keys["confidence"]: confidence}


def load(path: str | os.PathLike | None = None, env: dict | None = None) -> Contract:
    env = os.environ if env is None else env
    source = Path(path or env.get("MC4_CONTRACT") or HERE / "contract.toml")
    with open(source, "rb") as handle:
        data = tomllib.load(handle)
    for name, (section, key) in ENV_OVERRIDES.items():
        if env.get(name):
            data[section][key] = env[name]
    return Contract(data, str(source))


def write_whole(path: Path, payload: dict) -> None:
    """Temp file then rename, so a reader can never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False)
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
