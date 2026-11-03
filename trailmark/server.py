"""HTTP surface: GET /, GET /health, GET /traces, POST /ask. Same app on Vercel and in the container."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, adapter, agent, config, gpu, replay
from .extractive import ExtractiveBackend
from .llm import LLMBackend
from .netguard import BlockedURL

WEB = Path(__file__).with_name("web")
SCHEMA = adapter.load_schema()
MAX_BODY = 16_384
MAX_QUESTION = 500
RATE_WINDOW = 60.0
RATE_MAX = 20
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
STATIC = {"app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}

app = FastAPI(title="Trailmark", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
_hits: dict[str, list[float]] = {}
_hits_lock = threading.Lock()


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers[key] = value
    return response


def rate_limited(client: str, now: float | None = None) -> bool:
    """Best effort, per process. On serverless each instance counts separately."""
    now = time.monotonic() if now is None else now
    with _hits_lock:
        recent = [t for t in _hits.get(client, []) if now - t < RATE_WINDOW]
        if len(_hits) > 5000:
            _hits.clear()
        limited = len(recent) >= RATE_MAX
        if not limited:
            recent.append(now)
        _hits[client] = recent
    return limited


def _client_id(request: Request) -> str:
    # Forwarding headers are only trusted on Vercel, whose edge sets them.
    if os.environ.get("VERCEL"):
        forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def make_backend():
    choice = config.backend_choice()
    if choice == "llm":
        settings = config.llm_settings()
        if not settings["base_url"] or not settings["model"]:
            raise ValueError("TRAILMARK_BACKEND=llm needs TRAILMARK_LLM_BASE_URL and TRAILMARK_LLM_MODEL")
        return LLMBackend.from_settings(settings)
    if choice == "extractive":
        return ExtractiveBackend()
    raise ValueError(f"unknown TRAILMARK_BACKEND: {choice}")


def _configured_backend_name() -> tuple[str, str | None, str | None]:
    """(backend, model, config error). Never contacts the network except a configured LLM server."""
    choice = config.backend_choice()
    if choice == "replay":
        return "replay", None, None
    try:
        backend = make_backend()
    except ValueError as exc:
        return "misconfigured", None, str(exc)
    return backend.name, backend.model, None


def amd_status() -> dict:
    """Every field is read from the machine or from the committed traces."""
    gpu_name, gpu_source = gpu.detect_cached()
    runs = replay.amd_runs()
    backend, _, _ = _configured_backend_name()
    on_amd = backend.startswith("rocm-")
    if on_amd:
        statement = f"This deployment is serving inference from a local model server on {gpu_name}."
    else:
        statement = "This deployment does not run inference on AMD hardware."
    if runs:
        statement += f" Recorded AMD runs in this repository: {len(runs)}, on {', '.join(sorted({r['gpu'] for r in runs}))}."
    else:
        statement += " No AMD run has taken place yet: the repository holds no trace recorded on an AMD GPU."
    return {
        "this_deployment_inference_on_amd": on_amd,
        "gpu_reported_by_this_machine": gpu_name,
        "gpu_source": gpu_source,
        "recorded_amd_runs": len(runs),
        "statement": statement,
    }


def _deployment() -> str:
    if os.environ.get("VERCEL"):
        return "vercel-serverless"
    return os.environ.get("TRAILMARK_DEPLOYMENT", "local")


@app.get("/health")
def health():
    backend, model, error = _configured_backend_name()
    body = {
        "status": "ok" if not error else "degraded",
        "backend": backend,
        "model": model,
        "deployment": _deployment(),
        "version": __version__,
        "replay_traces": len(replay.list_traces()),
        "amd": amd_status(),
    }
    if error:
        body["error"] = error
    return body


@app.get("/traces")
def traces():
    return {"traces": replay.list_traces()}


def _error(status: int, message: str, **extra) -> JSONResponse:
    return JSONResponse({"error": message, **extra}, status_code=status)


@app.post("/ask")
async def ask(request: Request):
    raw = await request.body()
    if len(raw) > MAX_BODY:
        return _error(413, "request body too large")
    try:
        body = json.loads(raw)
    except (ValueError, RecursionError):
        return _error(400, "body must be JSON")
    if not isinstance(body, dict):
        return _error(400, "body must be a JSON object")

    if body.get("mode") == "replay" or config.backend_choice() == "replay":
        trace_id = body.get("trace_id")
        if trace_id is not None and not isinstance(trace_id, str):
            return _error(400, "trace_id must be a string")
        try:
            return adapter.write_response(replay.replay(trace_id), SCHEMA)
        except replay.TraceNotFound:
            return _error(404, "no such recorded trace")

    fields = adapter.read_request(body, SCHEMA)
    question, start_url = fields.get("question"), fields.get("start_url")
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= MAX_QUESTION:
        return _error(422, f"question must be text of 3 to {MAX_QUESTION} characters")
    if start_url in ("", None):
        start_url = None
    elif not isinstance(start_url, str):
        return _error(422, "start_url must be a string")
    if rate_limited(_client_id(request)):
        return _error(429, f"limit of {RATE_MAX} questions per minute reached")
    try:
        backend = await run_in_threadpool(make_backend)
    except ValueError as exc:
        return _error(503, str(exc))
    inject = body.get("demo_inject_fabricated_claim") is True
    try:
        result = await run_in_threadpool(agent.run, question.strip(), start_url, backend, config.public_limits(), inject_fabricated=inject)
    except BlockedURL as exc:
        return _error(400, f"URL refused: {exc}", refused=True)
    return adapter.write_response(result, SCHEMA)


@app.get("/")
def index():
    return FileResponse(WEB / "index.html", media_type="text/html; charset=utf-8")


@app.get("/static/{name}")
def static_file(name: str):
    if name not in STATIC:
        return _error(404, "not found")
    return FileResponse(WEB / name, media_type=STATIC[name])
