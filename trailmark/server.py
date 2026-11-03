"""The live URL: a status page and /health. It serves no answers and runs no model.

The graded product is the contract CLI in app/, which has no server and no port. This page exists so
a person can see the true state of the entry. Every AMD statement is computed from the machine and
from committed evidence files, on each request.
"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import __version__, evidence, gpu

WEB = Path(__file__).with_name("web")
REPO = "https://github.com/alexvec/amd-ai-league-lablab"
NO_RUN = "No AMD run has taken place. No AMD model has run for this entry."
NO_QUALIFYING_RUN = "No AMD model run qualifies for this entry yet. Committed evidence folders that did not qualify: {count}. Read them in the repository."
UNREADABLE = "This deployment could not read its evidence folder, so it cannot say whether an AMD run took place."
BLOCKED = "As of 2026-11-03 the run is blocked: the hackathon notebook says the operator's email is not registered, so no notebook can launch."
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

app = FastAPI(title="Trailmark status", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers[key] = value
    return response


def _deployment() -> str:
    return "vercel-serverless" if os.environ.get("VERCEL") else "local"


def amd_status() -> dict:
    gpu_name, gpu_source = gpu.detect_cached()
    runs = evidence.amd_runs()
    readable = evidence.folder_readable()
    rejected = evidence.rejected_folders()
    if not readable:
        statement = UNREADABLE
    elif runs:
        names = ", ".join(sorted({run["gpu"] for run in runs}))
        statement = f"Committed AMD runs in this repository: {len(runs)}, on {names}. See the evidence files. This page itself runs no model."
    elif rejected:
        statement = NO_QUALIFYING_RUN.format(count=len(rejected))
    else:
        statement = NO_RUN
    return {
        "model_running_in_this_deployment": False,
        "gpu_reported_by_this_machine": gpu_name,
        "gpu_source": gpu_source,
        "evidence_folder_readable": readable,
        "recorded_amd_runs": len(runs) if readable else None,
        "runs": runs,
        "folders_not_counted": rejected,
        "done_condition_met": bool(runs),
        "statement": statement,
    }


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    amd = amd_status()
    return {
        # Read from this deployment: "ok" means it could read the evidence the statement below rests on.
        "status": "ok" if amd["evidence_folder_readable"] else "degraded",
        "entry_state": "finished: a committed AMD run qualifies" if amd["done_condition_met"] else "unfinished: no qualifying AMD run",
        "recorded_amd_runs": amd["recorded_amd_runs"],
        "service": "status page only",
        "answers_served": False,
        "backend": "none",
        "model": None,
        "deployment": _deployment(),
        "version": __version__,
        "amd": amd,
    }


def _runs_table(runs: list[dict]) -> str:
    if not runs:
        return "<p>The evidence folder holds no qualifying run, so there are no AMD figures to show.</p>"
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(run[key]))}</td>" for key in ("run", "gpu", "hip", "model", "vram_peak_gib", "fixture_correct", "fixture_total")) + "</tr>"
        for run in runs
    )
    return (
        "<table><tr><th>Run</th><th>GPU</th><th>ROCm (torch.version.hip)</th><th>Model</th><th>Peak VRAM GiB</th><th>Fixture matched</th><th>Of</th></tr>"
        f"{rows}</table><p class=\"note\">Fixture questions are invented by this project. They are not the Match's questions.</p>"
    )


def render_index() -> str:
    amd = amd_status()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trailmark status: AMD AI League, Match 4</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<main>
<h1>Trailmark</h1>
<p class="lede">A contract-shaped web retrieval container for the AMD AI League, Match 4. Given a question, it finds the one value on a set of pages that answers it, names only the pages that prove it, and returns nothing if they do not. Not submitted. No evaluator has seen it.</p>
<p class="amd" id="amd-statement">{escape(amd["statement"])}</p>
<section class="card">
<h2>AMD evidence</h2>
{_runs_table(amd["runs"])}
<p class="note" id="done-rule">Done means a real run on an AMD GPU with measured, committed evidence. Until then this entry is unfinished.{" " + escape(BLOCKED) if not amd["runs"] else ""}</p>
</section>
<section class="card">
<h2>What this page is</h2>
<p id="page-scope">A status page. It runs no model and serves no answers. The product is a command-line program in a Docker image that an evaluator execs, so there is nothing to try here.</p>
</section>
<section class="card">
<h2>What exists and what does not</h2>
<ul id="build-state">
<li>Written and tested on a Mac: the CLI, page sources, index, span verifier, citation code and socket service, using a scripted stub in place of the model and a fixture site invented for the purpose. That shows the plumbing works. It is not the required capability.</li>
<li>Written and never run: the model code, and the GPU run script.</li>
<li>Written and never built: the Docker image on the mandated ROCm base.</li>
<li>Unknown: the Match 4 interface. It is assumed from the Match 3 kit, and the assumptions sit in one config file.</li>
</ul>
</section>
<p class="note"><a id="repo-link" href="{REPO}">Source and runbook on GitHub</a> &middot; <a id="health-link" href="/health">/health</a> reads this state as JSON.</p>
</main>
</body>
</html>
"""


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index():
    return HTMLResponse(render_index())


@app.get("/static/style.css")
def stylesheet():
    return FileResponse(WEB / "style.css", media_type="text/css; charset=utf-8")


@app.exception_handler(404)
async def _not_found(_request: Request, _exc):
    return JSONResponse({"error": "not found. This deployment has only / and /health."}, status_code=404)
