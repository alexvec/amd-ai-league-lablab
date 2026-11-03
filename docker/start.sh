#!/usr/bin/env bash
# Starts the agent on :8000. With TRAILMARK_SERVE_MODEL set to a model id, also starts vLLM
# on localhost and points the agent at it. The vLLM path is untested.
set -euo pipefail

if [[ -n "${TRAILMARK_SERVE_MODEL:-}" ]]; then
  command -v vllm >/dev/null || { echo "TRAILMARK_SERVE_MODEL is set but this image has no vllm. Build with a rocm/vllm base." >&2; exit 2; }
  vllm serve "${TRAILMARK_SERVE_MODEL}" --host 127.0.0.1 --port 8001 --max-model-len "${TRAILMARK_MAX_MODEL_LEN:-8192}" &
  export TRAILMARK_BACKEND=llm TRAILMARK_LLM_BASE_URL=http://127.0.0.1:8001/v1 TRAILMARK_LLM_MODEL="${TRAILMARK_SERVE_MODEL}"
  export TRAILMARK_REQUEST_SECONDS="${TRAILMARK_REQUEST_SECONDS:-300}"
  for _ in $(seq 1 180); do
    curl -fs http://127.0.0.1:8001/v1/models >/dev/null 2>&1 && break
    sleep 5
  done
fi

exec /opt/trailmark-venv/bin/python -m uvicorn trailmark.server:app --host 0.0.0.0 --port 8000
