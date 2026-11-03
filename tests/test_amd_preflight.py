"""The AMD script's preflight, run for real. A fake rocminfo proves the probe path only; it is not an AMD run."""

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FAKE_ROCMINFO = """#!/bin/sh
printf '*******\\nAgent 1\\n*******\\n  Marketing Name: Sample GPU For Test\\n  Device Type: GPU\\n'
"""


@pytest.fixture
def workdir(tmp_path):
    shutil.copytree(ROOT / "amd", tmp_path / "amd", ignore=shutil.ignore_patterns("logs", "first-run"))
    shutil.copytree(ROOT / "trailmark", tmp_path / "trailmark", ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def run_script(workdir, *args, env_path):
    env = {**os.environ, "PATH": env_path, "PYTHON": sys.executable}
    return subprocess.run(["bash", "amd/run_on_amd.sh", *args], cwd=workdir, env=env, capture_output=True, text=True, timeout=60)


def bare_path(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    return bin_dir


@pytest.mark.skipif(any(shutil.which(tool) for tool in ("rocminfo", "amd-smi", "rocm-smi")), reason="this machine has ROCm tools")
def test_refuses_and_writes_nothing_without_an_amd_gpu(workdir, tmp_path):
    done = run_script(workdir, env_path=os.environ["PATH"])
    assert done.returncode == 3 and "No AMD GPU" in done.stderr
    assert not (workdir / "amd" / "first-run").exists() and not (workdir / "traces").exists()


def test_probe_only_records_the_string_from_the_tool_and_stops(workdir, tmp_path):
    bin_dir = bare_path(tmp_path)
    tool = bin_dir / "rocminfo"
    tool.write_text(FAKE_ROCMINFO)
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    done = run_script(workdir, "--probe-only", env_path=f"{bin_dir}:{os.environ['PATH']}")
    assert done.returncode == 0, done.stderr
    record = json.loads((workdir / "amd" / "first-run" / "gpu-probe.json").read_text())
    assert record["gpu"] == "Sample GPU For Test" and record["source"] == "rocminfo"
    assert "Marketing Name" in record["raw_tool_output"]
    assert not (workdir / "traces").exists()
