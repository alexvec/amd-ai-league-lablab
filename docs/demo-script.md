> **DRAFT, pending the AMD run.** No real model and no AMD GPU has run this code. The recording this entry needs does not exist yet. Part 2 can only be recorded after a real run. Nothing here has been recorded or uploaded.

# Demo script: Trailmark

For Alex to record himself. The generic lablab form recommends under 5 minutes (UNVERIFIED for Match 4). Steps follow docs/demo-path.md.

## Rules for the recording

- Show only output produced on screen in that take. No output is written into this script in advance, except the fixed lines the self-check prints.
- The stub is called a stub. It is never called a model, and nothing it does is described as AMD work.
- Fixture questions are invented. They are never presented as the Match's questions or as accuracy.
- Do not show or say a GPU name, a VRAM figure, or a time per question unless it comes from a committed folder in `amd/evidence/`.

## Part 1: true today. Use this until a run is committed.

### The job (on the status page)

Open https://amd-ai-league-lablab.vercel.app.

Say: "This is the status page for a command-line program, not the product itself. An evaluator gives the program a question. It has to find the one value on a set of pages that answers it, name only the pages that prove it, and return nothing if they do not."

### The state (status page, then /health)

Point at the statement at the top, then open `/health`.

Say: "No AMD run has taken place. No real model has run this code. This page reads the evidence folder on every request, and recorded runs is zero. The hackathon notebook has not accepted my email yet, so that is the next step."

### The plumbing (terminal)

Run `.venv/bin/python tools/selfcheck_m4.py --local`.

Say: "This runs the whole CLI with a scripted stub standing in for the model. The stub only tests plumbing. Its replies are written by hand, including some deliberately wrong ones."

Point at step 3. Say: "A file nobody can read, a corrupt PDF, a binary and an empty directory are recorded, and the page sorted after them is still indexed."

Point at step 6. Say: "Given those scripted candidates, the plain-code checks reject the withdrawn value, drop a page that only repeats the answer, keep both pages of a two-hop chain, and refuse exactly when the answer sits in a page it could not read. That shows what the checks do, not what a model would do."

Point at the last line. Say: "It says plumbing checks passed, no AMD GPU, no evidence. That line is the most this machine can print."

### Close

Say: "The code is MIT licensed, and was written with substantial help from Claude through Claude Code. Who would pay for this outside the Match is a hypothesis, with no customers or pilots behind it."

## Part 2: RECORD ONLY AFTER a real run is committed

Do not record this from anything other than a real GPU session. Leave out anything the run did not show.

1. Terminal on the GPU machine: `--index` starting the service and printing the GPU name and `torch.version.hip`.
2. Question processes writing JSON, each a new process.
3. The VRAM line from step 8 of the self-check.
4. The committed folder: `summary.json`, `selfcheck.log`, `vram-samples.csv`, `MANIFEST.sha256`.
5. The fixture results as they came out, including misses. Say that the questions are invented and the result says nothing about the hidden set.
6. The status page and `/health` after `vercel --prod`, now showing the run read from its files.
7. If the real Match 4 spec ships a sample, the same container on that sample. If none ships, say so.

## Before recording, Alex checks

1. `/health` still says what the narration says.
2. The self-check's last line is what the script says it is.
3. For part 2: the folder is committed unedited and the live site is redeployed.
