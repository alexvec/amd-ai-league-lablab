"""Read the GPU string from the machine. No environment variable can set or override it.

The commands are from ROCm tools. The parsers have only been run against sample text on
a machine with no AMD GPU, so they are untested against real hardware output.
"""

from __future__ import annotations

import argparse
import functools
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RAW_LIMIT = 20_000


def _run(command: list[str]) -> str | None:
    if shutil.which(command[0]) is None:
        return None
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def parse_rocminfo(output: str) -> str | None:
    """First GPU agent's marketing name. CPU agents are also listed by rocminfo."""
    for agent in re.split(r"\n\*+\s*\n", output):
        if re.search(r"Device Type:\s*GPU", agent):
            match = re.search(r"Marketing Name:\s*(.+)", agent)
            if match and match.group(1).strip():
                return match.group(1).strip()
    return None


def parse_rocm_smi(output: str) -> str | None:
    for key in ("Card Series", "Card series", "Card Model", "Card model"):
        match = re.search(rf"{key}:\s*(.+)", output)
        if match and match.group(1).strip() not in ("", "N/A"):
            return match.group(1).strip()
    return None


def parse_amd_smi(output: str) -> str | None:
    match = re.search(r"MARKET_NAME:\s*(.+)", output)
    if match and match.group(1).strip() not in ("", "N/A"):
        return match.group(1).strip()
    return None


def detect(run=_run) -> dict:
    """Returns {"gpu": str|None, "source": str|None}. gpu is None unless a tool reports one."""
    for command, parser in (
        (["rocminfo"], parse_rocminfo),
        (["amd-smi", "static", "--asic"], parse_amd_smi),
        (["rocm-smi", "--showproductname"], parse_rocm_smi),
    ):
        output = run(command)
        if output:
            name = parser(output)
            if name:
                return {"gpu": name, "source": " ".join(command)}
    return {"gpu": None, "source": None}


@functools.lru_cache(maxsize=1)
def detect_cached() -> tuple:
    found = detect()
    return found["gpu"], found["source"]


def vram_snapshot(run=_run) -> str | None:
    """Raw VRAM use as reported by the tool, or None. Stored as text, not interpreted."""
    return run(["rocm-smi", "--showmeminfo", "vram"]) or run(["amd-smi", "metric", "--mem-usage"])


def probe_record(run=_run) -> dict:
    """What the machine reported, with raw tool output so the string can be checked later."""
    found = detect(run)
    raw = run(found["source"].split()) if found["source"] else None
    return {
        "gpu": found["gpu"],
        "source": found["source"],
        "raw_tool_output": raw[:RAW_LIMIT] if raw else None,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Print the AMD GPU this machine reports.")
    parser.add_argument("--require", action="store_true", help="exit 3 when no AMD GPU is reported")
    parser.add_argument("--write", type=Path, help="also write the probe record to this JSON file, only when a GPU is reported")
    args = parser.parse_args(argv)
    record = probe_record()
    found = {"gpu": record["gpu"], "source": record["source"]}
    if args.write and found["gpu"]:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(record, indent=1) + "\n", "utf-8")
    print(json.dumps(found))
    return 3 if args.require and not found["gpu"] else 0


if __name__ == "__main__":
    sys.exit(main())
