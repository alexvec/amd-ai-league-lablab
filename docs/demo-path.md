# Demo path

The walk a person records. `scripts/walk_demo.py` runs part A in a real browser and fails if the page does not do what is written here. The script has not been run against the current page; a static test checks that the elements it looks for exist. Run it once before recording.

```bash
.venv/bin/playwright install chromium   # once
.venv/bin/python scripts/walk_demo.py --url https://amd-ai-league-lablab.vercel.app
# To record it: --headed --slow-mo 600 --video-dir demo-recordings
```

## What this demo is and is not

No AMD model has run, so **this is not the demo the PRD requires.** Section 10 of `docs/prds/match-4.md` needs a terminal recording on the GPU, and that waits for the first real run. Until then, the most this path can show is the true state and the plumbing. Narration must say the model in part B is a scripted stub.

## Part A: the status page (walked by the script)

1. **Open the page.** The statement at the top is read from committed evidence: no AMD run has taken place. It matches `/health`.
2. **Show that it answers nothing.** There is no form and no input. The page says it runs no model and serves no answers, because the product is a CLI an evaluator execs.
3. **Show what exists.** The list separates what was tested with a stub, what has never run and what has never been built.
4. **Open `/health`.** `status` is `ok`, which means this deployment could read its evidence folder. `entry_state` says unfinished, `backend` is `none`, `answers_served` is false, and `recorded_amd_runs` is 0.
5. **Follow the repo link.** It leads to the source and runbook.

## Part B: the plumbing, in a terminal (not walked by the script)

```bash
.venv/bin/python tools/selfcheck_m4.py --local
```

6. Point at the first line: the stub model is not a model.
7. Point at step 3: the unreadable file, corrupt PDF, binary and empty directory are recorded, and the page sorted after them was indexed.
8. Point at step 6: the withdrawn value lost, the page repeating the value was not cited, the two-hop questions cite two pages, and the blocked-page question got an exact refusal. These checks were handed scripted candidates, so this shows what the checks do. It does not show what a model would do.
9. Point at step 8 and the last line: `SKIPPED: no AMD GPU`, and `PLUMBING CHECKS PASSED (no AMD GPU, no evidence)`.

## After the first real run

Replace part B with the terminal recording from the GPU: `--index` printing the GPU name and `torch.version.hip`, question processes returning JSON, the VRAM line, and the committed evidence folder.
