#!/usr/bin/env bash
# First real GPU run. A person, or a later agent with an AMD session, starts this from a terminal in
# a notebooks.amd.com/hackathon session:
#
#   git clone https://github.com/alexvec/amd-ai-league-lablab && cd amd-ai-league-lablab
#   bash amd/run_on_amd.sh --probe-only     # seconds: records the GPU and torch state, installs nothing
#   bash amd/run_on_amd.sh                  # installs deps, gets weights, runs the fixture self-check on the GPU
#
# UNTESTED ON AMD. This has never run on an AMD machine. Exercised on a Mac: the refusal with no GPU,
# and --probe-only with a fake rocminfo and a stub torch, manifest included. Everything after the probe
# has never run.
# It stops at RUN_BUDGET_SECONDS, pushes nothing, and leaves evidence files as produced.
#
# Overrides: PYTHON, STORE, MODEL_DIR, RUN_BUDGET_SECONDS, MIN_FREE_GIB
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python3}"
RUN_BUDGET_SECONDS="${RUN_BUDGET_SECONDS:-3000}"
MIN_FREE_GIB="${MIN_FREE_GIB:-12}"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$COMMIT"
EVIDENCE="amd/evidence/$RUN_ID"
PROBE_TMP="$(mktemp -d)"
BUDGET_PID=""
# However this ends (probe, failed install, time budget), a folder that exists gets its manifest,
# so a partial run can be committed unedited too.
finish() {
  [[ -n "$BUDGET_PID" ]] && kill "$BUDGET_PID" 2>/dev/null || true
  rm -rf "$PROBE_TMP"
  if [[ -d "$EVIDENCE" ]]; then "$PYTHON" amd/write_manifest.py "$EVIDENCE" || true; fi
}
trap finish EXIT
trap 'exit 143' TERM

echo "== 1/5 Probe: what this machine reports"
if ! "$PYTHON" -m trailmark.gpu --require --write "$PROBE_TMP/gpu-probe.json"; then
  cat >&2 <<'MSG'
No AMD GPU was reported by rocminfo, amd-smi or rocm-smi. Stopping, and writing no evidence, because
nothing run here could honestly be called an AMD run.
MSG
  exit 3
fi
set +e
"$PYTHON" - >"$PROBE_TMP/torch-probe.json" <<'PY'
import json, sys
try:
    import torch
except ImportError as exc:
    print(json.dumps({"torch": None, "error": str(exc)}))
    sys.exit(4)
hip = getattr(torch.version, "hip", None)
available = bool(torch.cuda.is_available())
print(json.dumps({"torch": str(torch.__version__), "hip": None if hip is None else str(hip), "cuda_available": available, "device": torch.cuda.get_device_name(0) if available else None}))
sys.exit(0 if available and hip is not None else 4)
PY
TORCH_STATUS=$?
set -e
cat "$PROBE_TMP/torch-probe.json"
mkdir -p "$EVIDENCE"
cp "$PROBE_TMP/gpu-probe.json" "$PROBE_TMP/torch-probe.json" "$EVIDENCE/"
"$PYTHON" --version >"$EVIDENCE/python-version.txt" 2>&1
df -h . >"$EVIDENCE/df.txt" 2>&1 || true
echo "Recorded in $EVIDENCE"
if [[ "$TORCH_STATUS" -ne 0 ]]; then
  echo "torch cannot reach a ROCm GPU here (see above). The rocm backend will refuse to run." >&2
  echo "Commit $EVIDENCE as it is: it records what this machine reported." >&2
  exit 4
fi
if [[ "${1:-}" == "--probe-only" ]]; then
  echo "Probe done, nothing installed. $EVIDENCE is a probe and does not count as a run. Commit it unedited."
  echo "Run this script again without --probe-only, or turn the session off: idle time counts against the quota."
  exit 0
fi

# Notebook storage per docs/competition.md: /persistent or /workspace, about 25 GB.
if [[ -z "${STORE:-}" ]]; then
  for candidate in /persistent /workspace; do
    if [[ -d "$candidate" && -w "$candidate" ]]; then STORE="$candidate/trailmark"; break; fi
  done
fi
STORE="${STORE:-$PWD/.amd-store}"
MODEL_DIR="${MODEL_DIR:-$STORE/models/qwen3-4b}"
mkdir -p "$STORE" amd/logs
FREE_GIB="$(df -Pk "$STORE" | awk 'NR==2 {print int($4/1048576)}')"
if [[ ! -f "$MODEL_DIR/config.json" && "$FREE_GIB" -lt "$MIN_FREE_GIB" ]]; then
  echo "Only $FREE_GIB GiB free at $STORE, and the weights need about 8 GB plus room. Stopping." >&2
  exit 5
fi

# The whole job has a budget, so a stuck install cannot eat the 3 h/day quota.
# The trap on TERM waits for the foreground command, so the children are stopped too.
( sleep "$RUN_BUDGET_SECONDS"; echo "Time budget of $RUN_BUDGET_SECONDS s reached. Stopping." >&2; kill -TERM $$; pkill -TERM -P $$ ) &
BUDGET_PID=$!

echo "== 2/5 Installing dependencies on this Python"
"$PYTHON" -m pip install --user -r app/requirements.txt 2>&1 | tee "$EVIDENCE/pip-install.log"
"$PYTHON" -m pip freeze >"$EVIDENCE/pip-freeze.txt"

echo "== 3/5 Getting weights (skipped if present): $MODEL_DIR"
if [[ ! -f "$MODEL_DIR/config.json" ]]; then
  "$PYTHON" tools/fetch_weights.py "$MODEL_DIR" 2>&1 | tee "$EVIDENCE/fetch-weights.log"
fi
if [[ -f "$MODEL_DIR/SOURCE.json" ]]; then cp "$MODEL_DIR/SOURCE.json" "$EVIDENCE/model-source.json"; fi

echo "== 4/5 Self-check on the GPU with the real model. Failures here are results: they get committed too."
set +e
"$PYTHON" tools/selfcheck_m4.py --local --backend rocm --model-dir "$MODEL_DIR" --evidence-dir "$EVIDENCE"
CHECK_STATUS=$?
set -e

echo "== 5/5 Done. The manifest is written on exit."
cat <<MSG

Self-check exit status: $CHECK_STATUS. Read $EVIDENCE/summary.json and $EVIDENCE/selfcheck.log.
Commit the folder as it is, whatever it says. Do not edit, trim or rerun over it:

  git add $EVIDENCE
  git -c user.name="Alex Veciana Belmonte" -c user.email="38962279+alexvec@users.noreply.github.com" commit -m "Add GPU run $RUN_ID, unedited"
  git push origin main

Then turn the session off, and run: vercel --prod
MSG
exit "$CHECK_STATUS"
