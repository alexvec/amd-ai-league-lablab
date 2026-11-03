# First real GPU run

Status: **no AMD run has taken place.** Nothing in this folder has run on AMD hardware. Numbers appear here only after a run has produced them.

The AMD account exists. As of 2026-11-03 https://notebooks.amd.com/hackathon says the email is not registered for the hackathon, so this waits until the email is on that list. See `NEEDS.md`.

## Shortest sequence

1. Sign in at https://notebooks.amd.com/hackathon and click Launch Notebook. Quota is 3 h per day and idle time counts, with about 25 GB of storage.
2. In a notebook terminal, record what the machine is. This installs nothing and takes seconds:

   ```bash
   git clone https://github.com/alexvec/amd-ai-league-lablab
   cd amd-ai-league-lablab
   bash amd/run_on_amd.sh --probe-only
   ```

   Exit 3 means no AMD GPU was reported, and nothing is written. Exit 4 means torch cannot reach a ROCm GPU. Neither can earn an AMD label, so stop and read the output. A probe writes a folder with its manifest. It does not count as a run, and `/health` lists it under `folders_not_counted`.
3. Run it. This installs `transformers`, fetches Qwen3-4B-Instruct-2507 (about 8 GB by arithmetic, not measured), starts the service on the GPU, runs every fixture question as a new process, and samples VRAM throughout:

   ```bash
   bash amd/run_on_amd.sh
   ```

4. Read `amd/evidence/<run>/summary.json` and `selfcheck.log`. **Commit the folder unedited, even if checks failed.** A failed first run is a result, and the manifest makes later edits visible. The manifest is written however the script ends: finished, failed install, or time budget (`RUN_BUDGET_SECONDS`, default 3000). The script prints the exact commit command with the right identity.
5. Turn off the session. On a machine with Vercel access, run `vercel --prod`. The status page then reads the new evidence.

If the notebook cannot push, download the evidence folder and commit it elsewhere, unchanged.

## After that: the image

The notebook cannot hold the 29.2 GiB base. This needs a Linux machine with Docker and at least 60 GiB free, or an AMD Developer Cloud instance, whose access and cost are UNVERIFIED:

```bash
python3 tools/fetch_weights.py models/qwen3-4b
docker build -t trailmark:m4 .
python3 tools/selfcheck_m4.py --docker trailmark:m4 --base rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0
```

Before submitting, read the real Match 4 spec, put it in `docs/spec/`, and update `app/contract.toml` and `fixtures/questions.json` per section 6 of `docs/prds/match-4.md`. How an image is submitted is UNVERIFIED, and submitting is Alex's step.

## What each step proves

| Evidence | Proves | Does not prove |
|---|---|---|
| `gpu-probe.json`, `torch-probe.json` | What the machine and torch report, with raw tool output | That the model used the GPU |
| `service.json`, `service.log` | The GPU assertion passed, weights landed on the GPU, a warm-up generation finished | Accuracy |
| `vram-samples.csv`, `vram-raw.log`, `summary.json` | Peak VRAM against the 1 to 48 GiB band, sampled once a second | That AMD's sampler would read the same |
| `outputs/`, `traces/` | What the model proposed and what the checks did with it, for each fixture question | Anything about the hidden set: the questions are invented |

## What is tested and what is not

| Item | Status |
|---|---|
| Refusal when no AMD GPU is reported | Run on a Mac, covered by a test |
| `--probe-only` | Run with a fake `rocminfo` and a stub `torch` only. Never on real hardware |
| The time budget stopping a stuck install, manifest on exit | Run with a fake `rocminfo`, stub `torch` and a fake `pip` that hangs. Never on real hardware |
| Everything else after the probe in `run_on_amd.sh` | **Never run** |
| `trailmark/model_rocm.py` load, warm-up, generate | **Never run**. Refusal paths only |
| `transformers` and its dependencies on Python 3.14 | UNVERIFIED. The run records `pip-freeze.txt`. Pin from it afterwards |
| `tools/fetch_weights.py` | **Never run** |
| Real `amd-smi`, `rocm-smi`, `rocminfo` output against the parsers | Untested. Parsers have only seen text written here |
| Whether a detached service survives under the real harness's exec | UNVERIFIED. It survived plain `docker exec` calls in the plumbing image, with the stub. The client refuses before the deadline if it does not |
| Time per question with the real model against the 30 s budget | Unknown. Match 4's budget is also UNVERIFIED |
| Whether notebook outbound access reaches Hugging Face | UNVERIFIED |
| Whether the self-check runs as root in the notebook | If so, mode 000 does not stop root, and it warns that this path was not exercised |

## How a run comes to count

`trailmark/evidence.py` counts a folder only if `summary.json` says backend `rocm`, names a GPU, a ROCm build and a model, has peak VRAM in band, and every file matches `MANIFEST.sha256`. No setting overrides this. The self-check refuses to write evidence for the stub. This checks committed files, so it is strong evidence rather than proof, which is why the raw tool output is kept next to the summary.
