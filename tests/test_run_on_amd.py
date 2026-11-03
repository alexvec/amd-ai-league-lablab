"""The AMD script's preflight, run for real on this machine. Fake tools prove the probe path only, not an AMD run."""

import json
import os
import shutil
import stat
import subprocess
import sys
import time

import pytest

from trailmark import evidence

from .helpers import ROOT

FAKE_ROCMINFO = "#!/bin/sh\nprintf '*******\\nAgent 1\\n*******\\n  Marketing Name: Sample GPU For Test\\n  Device Type: GPU\\n'\n"
STUB_TORCH = "__version__='0-stub'\nclass cuda:\n    is_available=staticmethod(lambda: True)\n    get_device_name=staticmethod(lambda _: 'Stub')\nclass version:\n    hip='0-stub'\n"
SCRIPT = (ROOT / "amd" / "run_on_amd.sh").read_text()


@pytest.fixture
def workdir(tmp_path):
    target = tmp_path / "w"
    target.mkdir()
    (target / "amd").mkdir()
    shutil.copy(ROOT / "amd" / "run_on_amd.sh", target / "amd")
    shutil.copy(ROOT / "amd" / "write_manifest.py", target / "amd")
    shutil.copytree(ROOT / "trailmark", target / "trailmark", ignore=shutil.ignore_patterns("__pycache__"))
    return target


def run(workdir, *args, path=None, extra=None):
    env = {**os.environ, "PYTHON": sys.executable, "PATH": path or os.environ["PATH"], **(extra or {})}
    env.pop("PYTHONPATH", None) if not extra or "PYTHONPATH" not in extra else None
    return subprocess.run(["bash", "amd/run_on_amd.sh", *args], cwd=workdir, env=env, capture_output=True, text=True, timeout=60)


def fake_tools(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "rocminfo"
    tool.write_text(FAKE_ROCMINFO)
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return f"{bin_dir}:{os.environ['PATH']}"


def evidence_folders(workdir):
    root = workdir / "amd" / "evidence"
    return list(root.iterdir()) if root.exists() else []


@pytest.mark.skipif(any(shutil.which(tool) for tool in ("rocminfo", "amd-smi", "rocm-smi")), reason="this machine has ROCm tools")
@pytest.mark.parametrize("args", [(), ("--probe-only",)])
def test_refuses_and_writes_nothing_without_an_amd_gpu(workdir, args):
    done = run(workdir, *args)
    assert done.returncode == 3 and "No AMD GPU" in done.stderr
    assert evidence_folders(workdir) == []


def test_probe_with_a_fake_tool_but_no_rocm_torch_stops(workdir, tmp_path):
    done = run(workdir, "--probe-only", path=fake_tools(tmp_path))
    assert done.returncode == 4 and "cannot reach a ROCm GPU" in done.stderr


def test_probe_only_records_and_installs_nothing(workdir, tmp_path):
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "torch.py").write_text(STUB_TORCH)
    done = run(workdir, "--probe-only", path=fake_tools(tmp_path), extra={"PYTHONPATH": str(stub)})
    assert done.returncode == 0, done.stderr
    folder = evidence_folders(workdir)[0]
    assert json.loads((folder / "gpu-probe.json").read_text())["gpu"] == "Sample GPU For Test"
    assert json.loads((folder / "torch-probe.json").read_text())["hip"] == "0-stub"
    assert not (folder / "pip-install.log").exists() and "nothing installed" in done.stdout
    # A probe folder has no summary, so it cannot count as a run, and it says so.
    assert evidence.amd_runs(workdir / "amd" / "evidence") == []
    assert evidence.rejected_folders(workdir / "amd" / "evidence") == [folder.name]
    assert "gpu-probe.json" in (folder / "MANIFEST.sha256").read_text()


def test_a_probe_that_stops_at_torch_still_gets_a_manifest(workdir, tmp_path):
    done = run(workdir, "--probe-only", path=fake_tools(tmp_path))
    assert done.returncode == 4
    assert "torch-probe.json" in (evidence_folders(workdir)[0] / "MANIFEST.sha256").read_text()


def test_time_budget_stops_a_stuck_install_and_leaves_a_manifest(workdir, tmp_path):
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "torch.py").write_text(STUB_TORCH)
    wrapper = tmp_path / "python-wrapper"
    wrapper.write_text(f'#!/bin/sh\nif [ "$1" = "-m" ] && [ "$2" = "pip" ]; then exec sleep 40; fi\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    started = time.monotonic()
    extra = {"PYTHONPATH": str(stub), "PYTHON": str(wrapper), "RUN_BUDGET_SECONDS": "1", "STORE": str(tmp_path / "store"), "MIN_FREE_GIB": "0"}
    done = run(workdir, path=fake_tools(tmp_path), extra=extra)
    assert time.monotonic() - started < 20
    assert done.returncode == 143, done.stderr
    assert "Time budget" in done.stderr
    assert "gpu-probe.json" in (evidence_folders(workdir)[0] / "MANIFEST.sha256").read_text()


def test_script_parses():
    assert subprocess.run(["bash", "-n", str(ROOT / "amd" / "run_on_amd.sh")]).returncode == 0


def test_script_says_it_is_untested_and_pushes_nothing_itself():
    assert "UNTESTED ON AMD" in SCRIPT
    code = [line for line in SCRIPT.splitlines() if not line.lstrip().startswith("#")]
    assert not [line for line in code if line.startswith(("git push", "  git push")) and "origin main" not in line]
    assert not [line for line in code if line.strip().startswith("git push") and not line.startswith("  git push origin main")]


def test_script_never_sets_the_fake_backend():
    assert "MC4_ALLOW_FAKE" not in SCRIPT and "--backend rocm" in SCRIPT


def test_manifest_round_trip_is_accepted_by_the_evidence_check(tmp_path):
    run_dir = tmp_path / "r"
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "outputs" / "q.json").write_text("{}")
    summary = {"backend": "rocm", "gpu": "G", "hip": "6", "model": "M", "vram_peak_gib": 9.0}
    (run_dir / "summary.json").write_text(json.dumps(summary))
    subprocess.run([sys.executable, str(ROOT / "amd" / "write_manifest.py"), str(run_dir)], check=True, capture_output=True)
    assert [row["gpu"] for row in evidence.amd_runs(tmp_path)] == ["G"]
    (run_dir / "outputs" / "q.json").write_text("{edited}")
    assert evidence.amd_runs(tmp_path) == []
