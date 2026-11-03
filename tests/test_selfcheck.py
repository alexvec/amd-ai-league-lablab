"""PRD acceptance test 9, and that the self-check cannot claim anything about AMD on this machine."""

import shutil
import subprocess
import sys

import pytest

from .helpers import ROOT

SCRIPT = ROOT / "tools" / "selfcheck_m4.py"
HAS_AMD_TOOLS = any(shutil.which(tool) for tool in ("rocminfo", "amd-smi", "rocm-smi"))


def run(*args, env=None, timeout=180):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=timeout, env=env)


@pytest.fixture(scope="module")
def local():
    return run("--local")


@pytest.mark.skipif(HAS_AMD_TOOLS, reason="this machine has ROCm tools")
def test_acceptance_9_final_line_is_plumbing_only(local):
    assert local.returncode == 0, local.stdout[-2000:]
    assert local.stdout.strip().splitlines()[-1] == "PLUMBING CHECKS PASSED (no AMD GPU, no evidence)"


def test_never_says_all_checks_passed_with_the_stub(local):
    assert "ALL CHECKS PASSED" not in local.stdout


def test_stub_notice_is_printed_first_and_last(local):
    lines = [line for line in local.stdout.splitlines() if line.strip()]
    assert lines[0].startswith("STUB MODEL IN USE") and lines[-2].startswith("STUB MODEL IN USE")
    assert "not a finished entry" in lines[0]


@pytest.mark.skipif(HAS_AMD_TOOLS, reason="this machine has ROCm tools")
def test_vram_step_says_skipped_no_gpu(local):
    assert "SKIPPED: no AMD GPU" in local.stdout


def test_all_numbered_steps_ran(local):
    for number in range(1, 9):
        assert f"\n{number}." in "\n" + local.stdout or f"{number}, " in local.stdout


def test_evidence_folder_refuses_a_stub_run(tmp_path):
    done = run("--local", "--evidence-dir", str(tmp_path / "e"))
    assert done.returncode != 0 and "never evidence" in done.stderr
    assert not (tmp_path / "e").exists()


@pytest.mark.skipif(HAS_AMD_TOOLS, reason="this machine has ROCm tools")
def test_real_backend_on_this_machine_fails_and_claims_nothing():
    done = run("--local", "--backend", "rocm")
    assert done.returncode == 1
    assert "--index exited 3" in done.stdout
    assert done.stdout.strip().splitlines()[-1] == "SOME CHECKS FAILED"
    assert "PASSED" not in done.stdout.split("3. the corpus")[1].split("[FAIL]")[-1]


def test_final_line_logic_needs_all_three_for_all_passed():
    sys.path.insert(0, str(ROOT / "tools"))
    import selfcheck_m4 as check

    clean = check.Report()
    assert check.final_line(clean, "fake", False, None).startswith("PLUMBING")
    assert check.final_line(clean, "fake", True, "GPU").startswith("PLUMBING")
    assert check.final_line(clean, "rocm", False, "GPU").startswith("PLUMBING")
    assert check.final_line(clean, "rocm", True, None).startswith("PLUMBING")
    assert check.final_line(clean, "rocm", True, "GPU") == "ALL CHECKS PASSED"
    failed = check.Report()
    failed.failed = True
    assert check.final_line(failed, "rocm", True, "GPU") == "SOME CHECKS FAILED"


def test_vram_parsers_on_written_samples_only():
    import vram_sampler as sampler

    assert sampler.parse_used_gib("    USED_VRAM: 2048 MB\n") == 2.0
    assert sampler.parse_used_gib("GPU: 0\nUSED_VRAM: 1024 MB\nGPU: 1\nUSED_VRAM: 3072 MB") == 3.0
    assert sampler.parse_used_gib("GPU[0] : VRAM Total Used Memory (B): 2147483648") == 2.0
    assert sampler.parse_used_gib("nothing useful") is None
