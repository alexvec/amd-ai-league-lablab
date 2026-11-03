"""Samples VRAM use from amd-smi or rocm-smi while a run works, and keeps the raw tool output.

UNTESTED on real hardware: the parsers have only seen text written here, in the shape the Match 3 kit
(USED_VRAM) and rocm-smi output are expected to take. The raw log is kept so a parser fault can be seen.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

GIB = 1024**3
UNITS = {"b": 1, "kb": 1000, "kib": 1024, "mb": 1024**2, "mib": 1024**2, "gb": GIB, "gib": GIB}
COMMANDS = (["amd-smi", "metric", "--mem"], ["amd-smi", "metric", "--mem-usage"], ["rocm-smi", "--showmeminfo", "vram"])


def parse_used_gib(text: str) -> float | None:
    """Highest per-GPU figure in the text, in GiB. None if nothing parses."""
    values: list[float] = []
    for number, unit in re.findall(r"USED_VRAM\W*?(\d+(?:\.\d+)?)\s*([A-Za-z]+)?", text or ""):
        values.append(float(number) * UNITS.get((unit or "mb").lower(), 1024**2) / GIB)
    for number in re.findall(r"VRAM Total Used Memory \(B\)\W*(\d+)", text or ""):
        values.append(int(number) / GIB)
    return max(values) if values else None


def available() -> bool:
    return any(shutil.which(command[0]) for command in COMMANDS)


def read_once() -> tuple[str, str] | None:
    """(command, stdout) of the first tool whose output parses."""
    for command in COMMANDS:
        if not shutil.which(command[0]):
            continue
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0 and parse_used_gib(done.stdout) is not None:
            return " ".join(command), done.stdout
    return None


class Sampler:
    def __init__(self, directory: Path | None, interval: float = 1.0):
        self.directory = directory
        self.interval = interval
        self.peak_gib: float | None = None
        self.samples = 0
        self.command: str | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> "Sampler":
        self._thread.start()
        return self

    def _loop(self) -> None:
        raw = open(self.directory / "vram-raw.log", "a", encoding="utf-8") if self.directory else None
        csv = open(self.directory / "vram-samples.csv", "a", encoding="utf-8") if self.directory else None
        try:
            while not self._stop.is_set():
                found = read_once()
                if found:
                    self.command, text = found
                    used = parse_used_gib(text)
                    self.samples += 1
                    self.peak_gib = used if self.peak_gib is None else max(self.peak_gib, used)
                    if raw:
                        raw.write(f"--- {time.time():.3f} {self.command}\n{text}\n")
                        csv.write(f"{time.time():.3f},{used:.4f}\n")
                        raw.flush()
                        csv.flush()
                self._stop.wait(self.interval)
        finally:
            for handle in (raw, csv):
                if handle:
                    handle.close()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=20)
