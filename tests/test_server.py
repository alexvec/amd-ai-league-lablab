"""PRD acceptance tests 3, 4 and 5 through the HTTP surface, with fakes for the network."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trailmark import adapter, agent, config, gpu, replay, server
from trailmark.extract import sha256_text

WEB = Path(server.__file__).with_name("web")
TRACE_KEYS = {"status", "question", "answer", "sources", "claims", "snapshots", "trace", "notes"}
CLAIM_KEYS = {"claim", "quote", "source_url", "verified", "match", "reason", "start", "end", "snapshot_sha256", "in_answer"}
TEXT = "The Alder river is 251 km long."


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for name in ("TRAILMARK_BACKEND", "TRAILMARK_LLM_BASE_URL", "TRAILMARK_LLM_MODEL", "TRAILMARK_LLM_API_KEY", "VERCEL"):
        monkeypatch.delenv(name, raising=False)
    server._hits.clear()


@pytest.fixture
def client():
    return TestClient(server.app, raise_server_exceptions=True)


@pytest.fixture
def trace_dir(tmp_path, monkeypatch):
    """A trace written by the real recorder path, using the real extractive backend on the fake web."""
    monkeypatch.setattr(config, "TRACES_DIR", tmp_path)
    monkeypatch.setattr(replay, "TRACES_DIR", tmp_path)
    monkeypatch.setattr(replay.list_traces, "__defaults__", (tmp_path,))
    monkeypatch.setattr(replay.amd_runs, "__defaults__", (tmp_path,))
    monkeypatch.setattr(replay.replay, "__defaults__", (tmp_path,))
    return tmp_path


def write_recorded(web, directory):
    from trailmark import record
    from trailmark.extractive import ExtractiveBackend

    web.add("https://site.example/", f"<title>Alder</title><p>{TEXT}</p>")
    return record.record_one("How long is the Alder river?", "https://site.example/", ExtractiveBackend(), config.Limits(), directory, fetcher_factory=web.factory)


def use_fake_web(monkeypatch, web):
    real_run = agent.run

    def patched(question, start_url, backend, limits, **kwargs):
        return real_run(question, start_url, backend, limits, fetcher_factory=web.factory, **kwargs)

    monkeypatch.setattr(agent, "run", patched)


def test_health_reports_active_backend(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["backend"] == "extractive-no-llm" and body["model"] is None


def test_health_follows_the_environment(client, monkeypatch, stub_model):
    monkeypatch.setenv("TRAILMARK_BACKEND", "llm")
    monkeypatch.setenv("TRAILMARK_LLM_BASE_URL", stub_model.base_url)
    monkeypatch.setenv("TRAILMARK_LLM_MODEL", "stub-model")
    body = client.get("/health").json()
    assert body["backend"] == "llm-openai-compatible" and body["model"] == "stub-model"


def test_health_reports_misconfiguration(client, monkeypatch):
    monkeypatch.setenv("TRAILMARK_BACKEND", "llm")
    body = client.get("/health").json()
    assert body["status"] == "degraded" and body["backend"] == "misconfigured"
    assert client.post("/ask", json={"question": "hello there"}).status_code == 503


def test_amd_status_says_no_run_when_there_is_none(client, trace_dir):
    amd = client.get("/health").json()["amd"]
    assert amd["this_deployment_inference_on_amd"] is False
    assert amd["recorded_amd_runs"] == 0
    assert "does not run inference on AMD" in amd["statement"] and "No AMD run has taken place" in amd["statement"]


def test_amd_status_changes_only_with_a_recorded_amd_trace(client, trace_dir):
    (trace_dir / "amd.json").write_text(json.dumps({"question": "q", "trace": {"backend": "rocm-vllm", "gpu": "GPU-STRING-FROM-TRACE", "inference_on_amd": True}}))
    amd = client.get("/health").json()["amd"]
    assert amd["recorded_amd_runs"] == 1 and "GPU-STRING-FROM-TRACE" in amd["statement"]


@pytest.mark.parametrize("path", ["/", "/health"])
def test_head_requests_are_answered(client, path):
    assert client.head(path).status_code == 200


def test_acceptance_3_ui_has_no_hard_coded_backend():
    html = (WEB / "index.html").read_text()
    assert "extractive-no-llm" not in html and "rocm" not in html.lower()
    script = (WEB / "app.js").read_text()
    assert 'text("health-backend", health.backend)' in script
    assert 'text("health-amd", health.amd.statement)' in script


def test_ui_never_uses_html_injection_sinks():
    script = (WEB / "app.js").read_text()
    code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert sink not in code


def test_page_is_served_with_a_strict_content_security_policy(client):
    response = client.get("/")
    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy and "unsafe-inline" not in policy


def test_acceptance_4_replay_matches_schema_and_is_labelled(client, trace_dir, web):
    path = write_recorded(web, trace_dir)
    response = client.post("/ask", json={"mode": "replay", "trace_id": path.stem})
    assert response.status_code == 200
    data = response.json()
    assert TRACE_KEYS <= set(data)
    assert isinstance(data["answer"], str) and isinstance(data["sources"], list)
    assert CLAIM_KEYS <= set(data["claims"][0])
    assert isinstance(data["claims"][0]["verified"], bool)
    assert data["trace"]["mode"] == "replay" and data["trace"]["backend"] == "extractive-no-llm"
    assert "Replay of a run recorded" in data["replay_notice"]
    assert TEXT in data["answer"]


def test_replay_mode_set_by_environment(client, trace_dir, web, monkeypatch):
    write_recorded(web, trace_dir)
    monkeypatch.setenv("TRAILMARK_BACKEND", "replay")
    assert client.get("/health").json()["backend"] == "replay"
    assert client.post("/ask", json={"question": "anything"}).json()["trace"]["mode"] == "replay"


def test_replay_does_not_trust_stored_verified_flags(client, trace_dir, web):
    path = write_recorded(web, trace_dir)
    data = json.loads(path.read_text())
    data["claims"][0]["quote"] = data["claims"][0]["claim"] = "A forged claim that was never on the page."
    path.write_text(json.dumps(data))
    result = client.post("/ask", json={"mode": "replay", "trace_id": path.stem}).json()
    assert result["claims"][0]["verified"] is False and result["answer"] is None


def test_replay_detects_a_tampered_snapshot(client, trace_dir, web):
    path = write_recorded(web, trace_dir)
    data = json.loads(path.read_text())
    data["snapshots"][0]["text"] = data["snapshots"][0]["text"] + " edited"
    path.write_text(json.dumps(data))
    result = client.post("/ask", json={"mode": "replay", "trace_id": path.stem}).json()
    assert result["claims"][0]["reason"] == "snapshot_hash_mismatch"


@pytest.mark.parametrize("trace_id", ["../../etc/passwd", "..", "does-not-exist", "a/b"])
def test_replay_refuses_bad_ids(client, trace_dir, trace_id):
    assert client.post("/ask", json={"mode": "replay", "trace_id": trace_id}).status_code == 404


def test_committed_traces_are_real_shape_and_replay_verified(client):
    for row in replay.list_traces():
        data = client.post("/ask", json={"mode": "replay", "trace_id": row["id"]}).json()
        assert data["trace"]["generated_by"]["tool"] == "trailmark.record"
        assert data["trace"]["backend"] == row["backend"]
        assert all(sha256_text(s["text"]) == s["sha256"] for s in data["snapshots"])


def test_acceptance_5_stub_model_fabrication_through_http(client, monkeypatch, stub_model, web):
    monkeypatch.setenv("TRAILMARK_BACKEND", "llm")
    monkeypatch.setenv("TRAILMARK_LLM_BASE_URL", stub_model.base_url)
    monkeypatch.setenv("TRAILMARK_LLM_MODEL", "stub-model")
    web.add("https://site.example/", f"<p>{TEXT}</p>")
    use_fake_web(monkeypatch, web)
    fake = {"claim": "It is 9000 km.", "quote": "The Alder river is 9000 km long.", "source_url": "https://site.example/"}
    stub_model.replies = [{"action": "answer", "claims": [fake]}] * 3
    data = client.post("/ask", json={"question": "How long is the Alder?", "start_url": "https://site.example/"}).json()
    assert data["claims"] and not any(claim["verified"] for claim in data["claims"])
    assert data["answer"] is None and data["sources"] == []


def test_live_ask_through_http_with_real_extractive_backend(client, monkeypatch, web):
    web.add("https://site.example/", f"<title>Alder</title><p>{TEXT}</p>")
    use_fake_web(monkeypatch, web)
    data = client.post("/ask", json={"question": "How long is the Alder river?", "start_url": "https://site.example/"}).json()
    assert data["status"] == "answered" and data["claims"][0]["verified"]
    assert data["trace"]["mode"] == "live"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "gopher://example.com/"])
def test_refused_urls_return_400(client, url):
    response = client.post("/ask", json={"question": "what is here?", "start_url": url})
    assert response.status_code == 400 and response.json()["refused"] is True


@pytest.mark.parametrize(
    "body,status",
    [({"question": ""}, 422), ({"question": "x" * 501}, 422), ({"question": 5}, 422), ({"question": "valid one", "start_url": 5}, 422), ([], 400)],
)
def test_bad_input(client, body, status):
    assert client.post("/ask", json=body).status_code == status


def test_oversized_body_rejected(client):
    assert client.post("/ask", content=b"x" * 20000).status_code == 413


def test_non_json_rejected(client):
    assert client.post("/ask", content=b"nope").status_code == 400


def test_rate_limit():
    results = [server.rate_limited("client-a", now=100.0) for _ in range(server.RATE_MAX + 1)]
    assert results[-1] is True and results[0] is False
    assert server.rate_limited("client-a", now=100.0 + server.RATE_WINDOW + 1) is False


def test_forwarded_header_not_trusted_off_vercel(client, monkeypatch):
    calls = []
    monkeypatch.setattr(server, "rate_limited", lambda who: calls.append(who) or True)
    client.post("/ask", json={"question": "hello there"}, headers={"x-forwarded-for": "1.2.3.4"})
    assert calls and calls[0] != "1.2.3.4"


def test_schema_config_renames_fields(monkeypatch, client, web):
    schema = {"request": {"question": "q", "start_url": "url"}, "response": {"answer": "result", "sources": "urls", "claims": "claims"}}
    assert adapter.read_request({"q": "a", "url": "b"}, schema) == {"question": "a", "start_url": "b"}
    assert set(adapter.write_response({"answer": 1, "sources": 2, "extra": 3}, schema)) == {"result", "urls", "extra"}


def test_gpu_parsers_and_no_env_override(monkeypatch):
    rocminfo = "*******\nAgent 1\n*******\n  Marketing Name: Some CPU\n  Device Type: CPU\n*******\nAgent 2\n*******\n  Marketing Name: Sample GPU\n  Device Type: GPU\n"
    assert gpu.parse_rocminfo(rocminfo) == "Sample GPU"
    assert gpu.parse_rocm_smi("GPU[0] : Card Series: Sample GPU") == "Sample GPU"
    assert gpu.parse_amd_smi("    MARKET_NAME: Sample GPU") == "Sample GPU"
    monkeypatch.setenv("TRAILMARK_GPU", "Fake GPU")
    assert gpu.detect(run=lambda _: None) == {"gpu": None, "source": None}
