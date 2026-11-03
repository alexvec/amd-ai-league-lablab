"""What the repository can prove about AMD runs, read from committed files on every request.

A run counts only if its summary says backend rocm, names a GPU and a ROCm build, measured peak VRAM
inside the 1 to 48 GiB band, and every file in its manifest still has the recorded hash. Nothing in
configuration can make a run count. This is a check on committed files, so it is strong evidence
rather than proof: whoever commits the files is trusted not to have forged them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import ROOT

EVIDENCE_DIR = ROOT / "amd" / "evidence"
VRAM_FLOOR_GIB = 1.0
VRAM_CEILING_GIB = 48.0 * 1.01


def _manifest_ok(run_dir: Path) -> bool:
    try:
        lines = (run_dir / "MANIFEST.sha256").read_text("utf-8").splitlines()
    except OSError:
        return False
    if not lines:
        return False
    for line in lines:
        digest, _, name = line.partition("  ")
        target = (run_dir / name).resolve()
        if run_dir.resolve() not in target.parents:
            return False
        try:
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                return False
        except OSError:
            return False
    return True


def valid_run(summary: dict, run_dir: Path) -> bool:
    peak = summary.get("vram_peak_gib")
    return (
        summary.get("backend") == "rocm"
        and bool(summary.get("gpu"))
        and bool(summary.get("hip"))
        and bool(summary.get("model"))
        and isinstance(peak, (int, float))
        and not isinstance(peak, bool)
        and VRAM_FLOOR_GIB <= peak <= VRAM_CEILING_GIB
        and _manifest_ok(run_dir)
    )


def folder_readable(directory: Path | None = None) -> bool:
    """False means this deployment lost the evidence folder, so it cannot say what was recorded."""
    directory = directory or EVIDENCE_DIR
    return directory.is_dir() and any(True for _ in directory.iterdir())


def rejected_folders(directory: Path | None = None) -> list[str]:
    """Committed folders that do not count as a run: a probe, or a run that failed its checks."""
    directory = directory or EVIDENCE_DIR
    if not directory.is_dir():
        return []
    counted = {row["run"] for row in amd_runs(directory)}
    return sorted(path.name for path in directory.iterdir() if path.is_dir() and path.name not in counted)


def amd_runs(directory: Path | None = None) -> list[dict]:
    """Public fields of each committed run that counts, oldest first."""
    directory = directory or EVIDENCE_DIR
    rows: list[dict] = []
    if not directory.is_dir():
        return rows
    for summary_path in sorted(directory.glob("*/summary.json")):
        try:
            summary = json.loads(summary_path.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(summary, dict) or not valid_run(summary, summary_path.parent):
            continue
        rows.append(
            {
                "run": summary_path.parent.name,
                "gpu": summary["gpu"],
                "hip": summary["hip"],
                "model": summary["model"],
                "vram_peak_gib": summary["vram_peak_gib"],
                "fixture_correct": summary.get("fixture_correct"),
                "fixture_total": summary.get("fixture_total"),
                "final_line": summary.get("final_line"),
                "git_commit": summary.get("git_commit"),
            }
        )
    return rows
