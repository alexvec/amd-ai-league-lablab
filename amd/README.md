# First AMD run

Status: **no AMD run has taken place.** `amd/run_on_amd.sh` has never run on AMD hardware, and no real model has answered this code.

The first session is meant to be short. The probe takes seconds. The model run does one question with a small model, and stops itself at a time budget (`RUN_BUDGET_SECONDS`, default 2400).

## Steps for Alex

1. Sign in at https://notebooks.amd.com/hackathon with the AMD Developer Program account and click Launch Notebook.
2. Open a terminal in the notebook and record the GPU string. This installs nothing:

   ```bash
   git clone https://github.com/alexvec/amd-ai-league-lablab
   cd amd-ai-league-lablab
   bash amd/run_on_amd.sh --probe-only
   ```

   It prints the string and writes it, with the raw tool output, to `amd/first-run/gpu-probe.json`. If it reports no AMD GPU it stops with exit code 3 and writes nothing. In that case, no later step can earn the AMD label.
3. Run the short job:

   ```bash
   bash amd/run_on_amd.sh
   ```

   This serves `Qwen/Qwen2.5-1.5B-Instruct` through vLLM and asks the one question in `amd/first-question.json` against a live page. If the default install fails, follow AMD's vLLM page and rerun with `MODEL_SERVER_CMD` set to your server command.
4. Read the new file in `traces/`. Check that `trace.gpu` shows the real GPU, `trace.backend` starts with `rocm-`, `gpu_vram_after_run` shows memory in use, and the claims are what they appear to be. A `no_answer` result is still a real result. Commit it as it is, and do not edit a trace.
5. Commit and push. The script prints the command with the right identity. The notebook needs git push access to the repo. Otherwise, download the files and commit them elsewhere.
6. Click Turn-off Session. Idle time counts against the 3 h/day quota.
7. Redeploy the live URL with `vercel --prod`, so `/health` and the UI read the new trace. Unless the Vercel project was connected to the repo, a push alone does not update them.

Once that works, `QUESTIONS=amd/questions.json bash amd/run_on_amd.sh` runs the three longer starting points. They are not an evaluation set, and no accuracy figure comes from them.

## What is tested and what is not

| Item | Status |
|---|---|
| Refusal when no AMD GPU is reported | Run for real on a machine with no AMD GPU, and covered by a test |
| `--probe-only` | Run with a fake `rocminfo` on the PATH only. Covered by a test. Never run on real hardware |
| Script flow after the probe (server start, wait, record, cleanup) | Run once in a temporary copy with a fake `rocminfo` and a stub server that is not a model. That trace was deleted and is not in this repo. Not an AMD run |
| GPU string parsing of real `rocminfo`, `amd-smi`, `rocm-smi` output | Untested. Parsers have only seen sample text. The probe keeps the raw output so a parser fault can be seen and fixed |
| vLLM install command in the script | Untested. Copied from the vLLM docs on 2026-11-03. AMD's docs give a different path for ROCm 10.1 (Python 3.14, per GPU target) |
| Default model | Exists and is not gated, per the Hugging Face API on 2026-11-03, with 3.09 GB of weights. Never served. Fit in the notebook's GPU memory is unknown. Override with `MODEL=` |
| Whether notebooks permit installs, background servers or outbound web access | Unverified. If outbound web is blocked, the trace will show fetch failures |
| Whether a real model follows the JSON protocol in `trailmark/llm.py` | Untested. Only a stub server has answered it |
| `Dockerfile` on a ROCm base, and `TRAILMARK_SERVE_MODEL` | Untested. Never built on a ROCm base. The `rocm/vllm` image is 31.3 GB per Docker Hub, more than the notebook's roughly 25 GB of storage |
| Whether the Match requires a specific base image, model or endpoint schema | Unverified. See `docs/competition.md` section 5 |

## How the AMD label is earned

Nothing can set it by configuration. `trailmark/llm.py` labels a backend `rocm-*` only if a ROCm tool on the machine reports a GPU and the model server is on loopback. `trailmark.record --require-amd` refuses to write a trace otherwise. No environment variable overrides the GPU string.

This is strong evidence, not proof. A CPU-only model server on the same machine would get the same label, and so would a faked tool on the PATH, as the flow test above shows. The trace therefore stores the raw VRAM report from after the run in `gpu_vram_after_run`, and the probe stores the raw tool output. Check that they look right before committing.
