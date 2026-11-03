"""The live page: truthful about AMD, reads real state, serves no answers."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from trailmark import evidence, gpu, server


@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "EVIDENCE_DIR", tmp_path)
    return tmp_path


def add_run(folder, name="run1", **changes):
    summary = {"backend": "rocm", "gpu": "GPU-FROM-FILE", "hip": "6.0", "model": "M", "vram_peak_gib": 9.5, "fixture_correct": 7, "fixture_total": 13, "final_line": "x", "git_commit": "abc", **changes}
    run = folder / name
    run.mkdir()
    data = json.dumps(summary)
    (run / "summary.json").write_text(data)
    (run / "MANIFEST.sha256").write_text(f"{hashlib.sha256(data.encode()).hexdigest()}  summary.json\n")
    return run


def test_no_run_is_stated_on_page_and_health(client, folder):
    (folder / "README.md").write_text("no run yet")
    amd = client.get("/health").json()["amd"]
    assert amd["recorded_amd_runs"] == 0 and amd["done_condition_met"] is False and amd["model_running_in_this_deployment"] is False
    assert "No AMD run has taken place" in amd["statement"] and "No AMD model has run" in amd["statement"]
    page = client.get("/").text
    assert amd["statement"] in page and "github.com/alexvec/amd-ai-league-lablab" in page


def test_committed_repo_state_has_no_run(client):
    assert evidence.amd_runs() == []
    body = client.get("/health").json()
    assert body["recorded_amd_runs"] == 0 and body["amd"]["recorded_amd_runs"] == 0
    assert body["status"] == "ok" and body["entry_state"].startswith("unfinished")


def test_status_is_degraded_when_the_evidence_folder_is_gone(client, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "EVIDENCE_DIR", tmp_path / "missing")
    body = client.get("/health").json()
    assert body["status"] == "degraded" and body["recorded_amd_runs"] is None
    assert "could not read" in body["amd"]["statement"] and "No AMD run has taken place" not in body["amd"]["statement"]


def test_a_committed_folder_that_does_not_qualify_changes_the_statement(client, folder):
    add_run(folder, vram_peak_gib=0.5)
    body = client.get("/health").json()
    assert body["recorded_amd_runs"] == 0 and body["amd"]["folders_not_counted"] == ["run1"]
    assert "did not qualify: 1" in body["amd"]["statement"] and "No AMD run has taken place" not in body["amd"]["statement"]


def test_page_gives_the_block_only_while_no_run_counts(client, folder):
    assert "not registered" in client.get("/").text
    add_run(folder)
    assert "not registered" not in client.get("/").text


def test_health_reports_no_model_and_no_answers(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["backend"] == "none" and body["model"] is None and body["answers_served"] is False


@pytest.mark.parametrize("path", ["/", "/health"])
def test_head_is_answered(client, path):
    assert client.head(path).status_code == 200


@pytest.mark.parametrize("path,method", [("/ask", "post"), ("/traces", "get"), ("/answer", "post")])
def test_no_answer_endpoints_remain(client, path, method):
    assert getattr(client, method)(path).status_code in (404, 405)


def test_page_has_no_form_or_script_and_a_strict_policy(client):
    response = client.get("/")
    assert "<form" not in response.text and "<script" not in response.text and "<input" not in response.text
    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy and "unsafe-inline" not in policy
    assert client.get("/static/style.css").status_code == 200


def test_page_does_not_describe_the_keyword_app(client):
    text = client.get("/").text.lower()
    assert "extractive" not in text and "keyword" not in text


def test_valid_committed_run_changes_the_statement_from_the_file(client, folder):
    add_run(folder)
    amd = client.get("/health").json()["amd"]
    assert amd["recorded_amd_runs"] == 1 and amd["done_condition_met"] is True and "GPU-FROM-FILE" in amd["statement"]
    assert amd["model_running_in_this_deployment"] is False
    assert "GPU-FROM-FILE" in client.get("/").text


@pytest.mark.parametrize(
    "changes",
    [{"backend": "fake"}, {"backend": None}, {"gpu": None}, {"gpu": ""}, {"hip": None}, {"model": ""}, {"vram_peak_gib": None}, {"vram_peak_gib": 0.5}, {"vram_peak_gib": 60}, {"vram_peak_gib": "9"}, {"vram_peak_gib": True}],
)
def test_a_run_that_does_not_qualify_does_not_count(client, folder, changes):
    add_run(folder, **changes)
    assert client.get("/health").json()["amd"]["recorded_amd_runs"] == 0


def test_an_edited_evidence_file_stops_counting(folder):
    run = add_run(folder)
    (run / "summary.json").write_text((run / "summary.json").read_text().replace("9.5", "9.6"))
    assert evidence.amd_runs() == []


def test_missing_manifest_or_escape_stops_counting(folder):
    run = add_run(folder, "a")
    (run / "MANIFEST.sha256").unlink()
    run = add_run(folder, "b")
    (run / "MANIFEST.sha256").write_text("00  ../a/summary.json\n")
    assert evidence.amd_runs() == []


def test_corrupt_summary_is_ignored(folder):
    (folder / "x").mkdir()
    (folder / "x" / "summary.json").write_text("{not json")
    assert evidence.amd_runs() == []


def test_evidence_text_is_escaped_on_the_page(client, folder):
    add_run(folder, gpu="<script>alert(1)</script>")
    page = client.get("/").text
    assert "<script>" not in page and "&lt;script&gt;" in page


def test_environment_cannot_claim_a_gpu(monkeypatch, client, folder):
    monkeypatch.setenv("TRAILMARK_GPU", "Fake GPU")
    monkeypatch.setenv("MC4_BACKEND", "rocm")
    assert gpu.detect(run=lambda _: None) == {"gpu": None, "source": None}
    assert client.get("/health").json()["amd"]["done_condition_met"] is False


def test_gpu_parsers_on_written_samples_only():
    rocminfo = "*******\nAgent 1\n*******\n  Marketing Name: Some CPU\n  Device Type: CPU\n*******\nAgent 2\n*******\n  Marketing Name: Sample GPU\n  Device Type: GPU\n"
    assert gpu.parse_rocminfo(rocminfo) == "Sample GPU"
    assert gpu.parse_rocm_smi("GPU[0] : Card Series: Sample GPU") == "Sample GPU"
    assert gpu.parse_amd_smi("    MARKET_NAME: Sample GPU") == "Sample GPU"
