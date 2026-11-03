#!/usr/bin/env bash
# First real AMD run. Alex launches this from a terminal in a notebooks.amd.com/hackathon session:
#
#   git clone https://github.com/alexvec/amd-ai-league-lablab && cd amd-ai-league-lablab
#   bash amd/run_on_amd.sh --probe-only     # seconds: records the GPU string, installs nothing
#   bash amd/run_on_amd.sh                  # short job: one question, small model, time budget
#
# It reads the GPU string from the machine and writes it to amd/first-run/gpu-probe.json. The full
# run then starts an OpenAI-compatible model server on ROCm, runs the agent on one live question,
# and writes a trace with measured values to traces/. It stops if no AMD GPU is reported, stops at
# RUN_BUDGET_SECONDS, and pushes nothing.
#
# UNTESTED ON AMD: this has never run on an AMD machine. Run for real here: the refusal with no GPU
# and --probe-only with a fake rocminfo. The flow after that has only been run with a fake rocminfo
# and a stub model server, never with vLLM or a GPU. Unverified: which GPU the notebook has, whether
# it allows vLLM installs, whether it can reach public websites, and whether the default model fits.
# See amd/README.md.
#
# Overrides:
#   MODEL=<hf id>             model to serve (default below; fit in GPU memory unverified)
#   MODEL_SERVER_CMD="..."    your own server command; must listen on 127.0.0.1:$PORT
#   QUESTIONS=amd/questions.json   the longer set, after the first run has worked
#   RUN_BUDGET_SECONDS, SERVER_WAIT_SECONDS, PORT, MAX_MODEL_LEN, GPU_MEMORY_UTILIZATION, REQUEST_SECONDS
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
PORT="${PORT:-8001}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.85}"
REQUEST_SECONDS="${REQUEST_SECONDS:-300}"
QUESTIONS="${QUESTIONS:-amd/first-question.json}"
RUN_BUDGET_SECONDS="${RUN_BUDGET_SECONDS:-2400}"
SERVER_WAIT_SECONDS="${SERVER_WAIT_SECONDS:-900}"
PYTHON="${PYTHON:-python3}"
PROBE_FILE="amd/first-run/gpu-probe.json"

echo "== 1/5 Reading the GPU string from this machine"
if ! "$PYTHON" -m trailmark.gpu --require --write "$PROBE_FILE"; then
  cat >&2 <<'MSG'
No AMD GPU was reported by rocminfo, amd-smi or rocm-smi. Stopping, because a trace written
here could not honestly be called an AMD run.
MSG
  exit 3
fi
echo "Recorded in $PROBE_FILE"
if [[ "${1:-}" == "--probe-only" ]]; then
  cat <<'MSG'
Probe done, nothing installed. Read the file above, then run this script again without
--probe-only for the short model run, or use "Turn-off Session". Idle time counts against the quota.
MSG
  exit 0
fi

# The whole job has a budget, so a stuck install or server cannot eat the 3 h/day quota.
( sleep "$RUN_BUDGET_SECONDS"; echo "Time budget of $RUN_BUDGET_SECONDS s reached. Stopping." >&2; kill -TERM $$ ) &
BUDGET_PID=$!
SERVER_PID=""
trap 'kill "$BUDGET_PID" 2>/dev/null || true; [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Notebook storage per docs/competition.md section 9: /persistent or /workspace, about 25 GB.
STORE=""
for candidate in /persistent /workspace; do
  if [[ -d "$candidate" && -w "$candidate" ]]; then STORE="$candidate/trailmark"; break; fi
done
STORE="${STORE:-$PWD/.amd-store}"
mkdir -p "$STORE" amd/logs
export HF_HOME="${HF_HOME:-$STORE/hf}"
LOG="amd/logs/model-server-$(date -u +%Y%m%dT%H%M%SZ).log"
echo "Storage: $STORE  Model cache: $HF_HOME  Server log: $LOG"

echo "== 2/5 Preparing the model server"
if [[ -n "${MODEL_SERVER_CMD:-}" ]]; then
  SERVER=(bash -c "$MODEL_SERVER_CMD")
else
  VLLM_BIN="$(command -v vllm || true)"
  if [[ -z "$VLLM_BIN" ]]; then
    # Command from the vLLM install docs, read 2026-11-03: ROCm wheels are Python 3.12 only, and other
    # versions can silently fall back to the CUDA wheel. https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html
    # AMD's docs give a different path for ROCm 10.1 (Python 3.14, per GPU target):
    # https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html
    # If this fails, follow AMD's page and rerun with MODEL_SERVER_CMD set.
    command -v uv >/dev/null || "$PYTHON" -m pip install --user uv
    export PATH="$HOME/.local/bin:$PATH"
    uv venv --python 3.12 --seed "$STORE/vllm-venv"
    uv pip install --python "$STORE/vllm-venv/bin/python" vllm --extra-index-url https://wheels.vllm.ai/rocm/ --upgrade
    VLLM_BIN="$STORE/vllm-venv/bin/vllm"
  fi
  SERVER=("$VLLM_BIN" serve "$MODEL" --host 127.0.0.1 --port "$PORT" --max-model-len "$MAX_MODEL_LEN" --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION")
fi

echo "== 3/5 Starting the model server on 127.0.0.1:$PORT"
"${SERVER[@]}" >"$LOG" 2>&1 &
SERVER_PID=$!
WAITED=0
while (( WAITED < SERVER_WAIT_SECONDS )); do
  if curl -fs "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then READY=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "The model server exited. Last lines of $LOG:" >&2
    tail -n 30 "$LOG" >&2
    exit 4
  fi
  sleep 5
  WAITED=$((WAITED + 5))
done
if [[ -z "${READY:-}" ]]; then
  echo "The model server was not ready after $SERVER_WAIT_SECONDS s. See $LOG" >&2
  exit 4
fi
SERVED_ID="$(curl -fs "http://127.0.0.1:$PORT/v1/models" | "$PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')"
echo "Serving: $SERVED_ID"

echo "== 4/5 Running the agent on live pages"
export TRAILMARK_BACKEND=llm TRAILMARK_LLM_BASE_URL="http://127.0.0.1:$PORT/v1" TRAILMARK_LLM_MODEL="$SERVED_ID"
# record.py refuses unless the backend label resolves to rocm-*, which needs the GPU reported here
# and a model server on this machine. Each trace stores the GPU string, tokens and wall time as measured.
"$PYTHON" -m trailmark.record --questions "$QUESTIONS" --require-amd --request-seconds "$REQUEST_SECONDS"

echo "== 5/5 Done. Read these before committing:"
git status --short traces/ "$PROBE_FILE" 2>/dev/null || true
cat <<'MSG'

  git add amd/first-run/gpu-probe.json traces/
  git -c user.name="Alex Veciana Belmonte" -c user.email="38962279+alexvec@users.noreply.github.com" commit -m "Add first AMD run"
  git push

Then turn off the session with "Turn-off Session". Idle time counts against the 3 h/day quota.
MSG
