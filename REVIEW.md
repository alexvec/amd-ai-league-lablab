# REVIEW: AMD AI League (lablab.ai), Match 4

Reviewed 2026-11-03 for Alex. This replaces any earlier review, which is void.

## Verdict: FAIL. The packet is not finished.

The required sponsor capability (an open model answering on an AMD GPU) has not run anywhere. `amd/evidence/` holds one file, `README.md`, and no run folder. The live URL does not run it either. The live URL and the repo are honest about this, and nothing is mocked or passed off as AMD work. The entry is an unfinished, truthfully labelled build, not a submittable one.

The `verify` box in STATE.md is left unchecked. I did not edit STATE.md.

What must be rebuilt: nothing in the code needs redoing first. The missing piece is a real GPU run. Get the notebook allowlist fixed, run `amd/run_on_amd.sh` there, commit the evidence folder unedited, then rewrite the draft packet from it. Details are in the steps below.

## Blockers, by severity

1. **No AMD run exists (fatal).** The sponsor capability has never run. `amd/evidence/` has only `README.md`. `/health` reports `recorded_amd_runs: 0`, `backend: none`, `model: null`, `done_condition_met: false`. The repo's own done condition (docs/win-plan.md section 7) is unmet.
2. **Notebook access (blocks #1).** NEEDS.md records that notebooks.amd.com/hackathon returns `not_registered` for the signed-in AMD account. I did not sign in to confirm. No agent can fix this: it needs the hackathon admins.
3. **The image has never been built or checked on the mandated base.** The Dockerfile is a static match to the kit. `tools/selfcheck_m4.py --docker` has only run against a `python:3.14-slim` plumbing image. The base is about 29.2 GiB and the notebook has about 25 GB, so it needs a separate Linux machine with Docker and 60 GiB or more free.
4. **The Match 4 interface is unpublished.** Everything is assumed from the Match 3 kit. The Match 4 close time is unknown. The competition.md note says the Dec 1 timer is League-wide, not Match 4. Alex must ask on Discord, and no agent may post there.
5. **Not enrolled.** NEEDS.md says JOIN THE LEAGUE and the solo team form are not done, and that Submit Project is not available. Discord membership is not done. I did not check these on the live site.
6. **Draft packet is conditional.** docs/submission.md, docs/slides.md and docs/demo-script.md are labelled DRAFT. Their AMD slots are blank templates. No video exists, no PDF slides exist, and no cover image exists.
7. **Uncommitted NEEDS.md names a private email.** Its "Account check" section contains one. `git status` shows `M NEEDS.md` and a second untracked file at the repo root, which I did not open. Do not `git add` NEEDS.md as it stands. The committed history has no private email, no age, and no team name from the operator profile. I searched all 9 commits.
8. **Win-plan differentiation is thin.** See the table row "Originality / gallery". It does not trip the fail rule, but it concedes the idea is the same.

## Steps for Alex, in order

These come from the NEEDS.md section "Exact remainder". I checked each against competition.md and the code.

1. Get the email added to the notebook list. The notebook page says "contact admins" and names no channel. Use the Help button on the event page or Discord. NEEDS.md has a suggested message. Add both emails yourself. Correct as written. Do not make a second lablab account, since one account per person is the rule.
2. Finish JOIN THE LEAGUE and the solo team form on lablab, and join Discord (discord.gg/lablabai). The rule book says Discord is required for Match participation. Correct, but NEEDS.md calls this "blocks submission only", and it does not block the GPU run.
3. In a notebook terminal: `git clone https://github.com/alexvec/amd-ai-league-lablab && cd amd-ai-league-lablab && bash amd/run_on_amd.sh --probe-only`, then `bash amd/run_on_amd.sh`. Commit `amd/evidence/<run>/` unedited. Then `vercel --prod`. Correct. See the script risks below.
4. Build and check the image elsewhere: `python3 tools/fetch_weights.py models/qwen3-4b`, `docker build -t trailmark:m4 .`, then `tools/selfcheck_m4.py --docker trailmark:m4 --base <mandated tag>`. Correct. `models/` is gitignored, so the build fails until the weights are fetched. The Dockerfile says so.
5. Read the real Match 4 spec and close time. Save them under `docs/spec/`, then edit `app/contract.toml` and `fixtures/questions.json`. Ask for the close time first. If Match 4 has closed by the time the run is done, the prize is gone. The win plan says to reuse the chassis for Match 5 or 6.
6. Rewrite the three draft files from the committed evidence, record the demo, then decide whether to submit. After that, re-run this review.

NEEDS.md also has stale sections (the "Director's reading" and "Rebuild order" blocks say the agent creates accounts). Its own text says the "Exact remainder" section governs. I'd tidy that before anyone relies on the file.

## Checks I ran

- **Tests:** `.venv/bin/python -m pytest -q` exited 0. The output shows 355 dots and no failures. The project's `addopts = -q` doubles the quiet flag, so the summary count line is not printed. The 355 is my count of the dots.
- **Self-check:** `.venv/bin/python tools/selfcheck_m4.py --local` ran. 13 of 13 invented fixture questions matched, HTTP and service fault injection passed, and the guard log was empty. Step 8 VRAM printed `SKIPPED: no AMD GPU`. The last two lines were `STUB MODEL IN USE: ... not a finished entry.` and `PLUMBING CHECKS PASSED (no AMD GPU, no evidence)`. That is the honest best result on this machine, and it says nothing about AMD or a real model.
- **Live URL, unauthenticated:** `/` returned 200 (HTML status page), and `/health` returned 200 JSON. The page says "No AMD run has taken place. No AMD model has run for this entry." `/health` says `answers_served: false`. It responds, but it does not run the sponsor capability.
- **Repo:** public, default branch main, GitHub reports the MIT licence. LICENSE and README.md are tracked. README has the test command and the status table. Sizes and statuses match what I saw in the tree.
- **Secrets and identity:** no `.env` or `.claude-session.json` tracked, and both are in `.gitignore`. All 9 commits have Alex Veciana Belmonte (noreply address) as author and committer, with no agent name in any message or trailer. My history search found no keys or private email. Claude is named only in the README and packet as the lablab Rule 13 AI-tool disclosure, which is the right place for it. No commit message names an agent.
- **Not done by me:** no Docker build or image pull, no weights download, no sign-in, no browser, no check of the lablab, Discord or notebook pages. The notebook and enrollment states are quoted from NEEDS.md, not confirmed.

## Contract comparison against the Match 3 kit

| Item | Kit | This entry | Difference |
|---|---|---|---|
| Base image | `rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0` | Same `FROM` line, asserted by `tests/test_dockerfile.py` | None on the tag. The layers were never built or checked. |
| CMD | `sleep infinity`, no port | Same | None |
| Index call | `python3 /app/app.py --index /app/corpus` | Same | None |
| Query call | `--corpus --query-id --query` | Same, plus an optional `--start-url` (an assumption) | Extra flag, optional |
| Output | `/app/output/<id>_output.json` with `answer`, `citations`, `confidence` | Same keys and path, written whole | None. `confidence` is a fixed 0.9 or 0.0 and the kit says it is never scored. |
| Citations | exact set, necessity, corpus-relative paths | Necessity pruning, paths for a mirror, URLs for HTTP | Match 4 pages may not be a corpus. Unknown. |
| Refusal | empty answer, empty citations | `{"answer":"","citations":[],"confidence":0.0}` | None |
| Time | 10 min startup, 30 s per question, 10 min run | `contract.toml` has 600, 30, 600 and a 4 s margin | Same numbers. These are Match 3 figures, not confirmed for Match 4. |
| Size / VRAM | 60 GiB, 1 to 48 GiB | The 4B model in bf16 should fit. No figure was measured. | Unmeasured |
| Network | none at grading, weights in image | `HF_HUB_OFFLINE=1`, `COPY models/`, `--network none` in docker mode | Only run on the plumbing image |
| Dockerfile extras | `COPY app/`, requirements, mkdir | Also `COPY models/`, `COPY trailmark/`, and ENV offline flags | Needed for the design. The kit's `starter/app/` layout is not copied. |
| Selfcheck | kit's `selfcheck.py` | Own `tools/selfcheck_m4.py` | The kit's script was not run against this. It was written for Match 3, and the kit needs Docker and a GPU. |

## `amd/run_on_amd.sh`: will it work on the notebook?

Plausible, but it has never run past the probe step. Likely failure points, in order:

1. **`pip install --user -r app/requirements.txt` on Python 3.14.** `transformers>=4.51` is unpinned and pulls `tokenizers`, `safetensors`, `numpy` and others. Whether they have 3.14 wheels or build from source is unknown. The script itself says so. If the notebook's Python is marked externally managed, `--user` may be refused. The script records `pip-install.log`, so a failure is still evidence.
2. **Transformers API drift.** `model_rocm.py` calls `from_pretrained(..., torch_dtype=torch.bfloat16)`. A newer transformers may warn or rename that argument. I did not verify this.
3. **Resident service surviving.** Whether a detached child outlives the index process under the harness is unverified. The local self-check shows it surviving `docker exec` on the plumbing image only.
4. **Disk.** About 8 GB for Qwen3-4B-Instruct-2507 (the README's own arithmetic, not measured) plus pip packages fits in 25 GB, and the script refuses below 12 GiB free. The Hugging Face cache could double the weights if it is on the same volume. `fetch_weights.py` uses `local_dir`, which limits that.
5. **Time.** The script stops itself at 3000 s of the 3 h/day quota. Idle time counts. A first failing install could use most of that, and the session must be turned off afterwards.
6. **Network.** The notebook needs to reach Hugging Face and PyPI. Not confirmed.
7. **The image cannot be built there.** A 29.2 GiB base does not fit in about 25 GB. The script does not try, and says so.

## Submission items (generic lablab form; UNVERIFIED for Match 4)

competition.md says the event gives no per-Match field list. The generic form is the best guess, so each row is graded as if it applies.

| Item | Result | Evidence | Text or URL to paste |
|---|---|---|---|
| Title (5 to 50) | PASS (as a draft) | 50 characters, counted | `Trailmark: one value, only the pages that prove it` |
| Short description (50 to 255) | PASS on length, but it must change | 195 characters, and it says no AMD run has happened | Text in docs/submission.md, "Short description, true today". Rewrite it after the run. |
| Long description (600 to 2,000) | PASS on length, but it must change | 1,268 characters, and it says the model has never loaded | Text in docs/submission.md. Rewrite it after the run. |
| AMD capability statement | FAIL | The template in docs/submission.md has blanks. Nothing real exists to fill them. | None. Do not use the template. |
| GitHub repo, public | PASS | API: public, MIT. Commits are clean. | https://github.com/alexvec/amd-ai-league-lablab |
| Licence | PASS | LICENSE tracked, GitHub reports MIT | n/a |
| Run instructions in the repo | PASS | README sections "Run it on a machine with no GPU" and "The first real GPU run", plus amd/README.md | n/a |
| Demo application URL | PASS (it responds) but not a demo | A status page that serves no answers | https://amd-ai-league-lablab.vercel.app |
| Video (MP4 or MOV, 300 MB, under 5 min) | FAIL | Not recorded. docs/demo-script.md Part 2 needs a real run. | none |
| Slides PDF | FAIL | docs/slides.md is an outline, not a PDF. Slides 5 and 8 cannot be filled yet. | none |
| Cover image 16:9 | Not made | Optional. If Alex wants one, use the avatar file named in CLAUDE.md. Do not generate one. | none |
| Evaluator image submission | FAIL | Never built. How an image is submitted is unknown. | none |
| AI-tool disclosure (Rule 13) | PASS | In README, docs/submission.md, slides and the demo script | Text in docs/submission.md, "AI-tool disclosure" |
| Eligibility (individual, Discord, enrolled) | FAIL | Per NEEDS.md, not enrolled and not on Discord | n/a |

## Rules against competition.md

| Rule | Result | Evidence |
|---|---|---|
| Sponsor capability runs on the live URL | FAIL | The live URL runs no model. `/health`: `backend: none`. |
| Capability not mocked | PASS, with a caveat | The stub is labelled everywhere, and the CLI refuses a stand-in outside tests per the win plan. But the only thing that has run is the stub. |
| Real run with evidence a judge can check | FAIL | `amd/evidence/` holds `README.md` only. |
| Follows the evaluator contract where known | PASS on paper | See the contract table. No run on the mandated image. |
| Original work, MIT, open source | PASS | LICENSE, public repo, `fixtures/` invented and said so. |
| AI-tool disclosure | PASS | See above. |
| No invented metrics or users | PASS | README, submission, slides and demo script quote no accuracy, speed or user figure. The only numbers are counts and limits from the kit, such as the 13 invented fixture questions, which `selfcheck_m4.py --local` reproduced for me. One README sentence (index pass stored 5 text files and recorded 9 failures on a kit-corpus copy) I did not re-run. |
| Stale text from the voided keyword app | PASS | A search of README, packet, `amd/` and docs found no `keyword`, `extractive` or `/ask` text. The win-plan header notes that its "no AMD account" lines are out of date, and its section 5 still says it. NEEDS.md has stale sections as noted. |
| Match 4 live and prize-eligible | UNVERIFIED | The close time is unknown. Prizes need submission while live. |
| Submitted, joined, posted | Not done | Correct per CLAUDE.md. |

## Judging criteria against Past winners

No Match 4 criteria are published. competition.md section 6 and the Match 4 specification say an AMD evaluator grades Matches, and the lablab business rubric counts only if the event page says so. It does not, so I do not apply it as the main rubric. For reference, I score the four generic criteria against the Past winners section anyway.

| Criterion | Score (1 to 5) | Against Past winners |
|---|---|---|
| Application of technology | 1 | The only comparison point in the rule book that published hardware proof is REPOMIND (rocm-smi, benchmarks, self-reported and not checked by anyone here). This entry has no run at all. |
| Originality | 2 | The win plan itself says the idea is not different. The difference is the execution (contract fit, necessity citations, fault tolerance, evidence), and most of that is untested against a real model. |
| Presentation | 2 | A clear, honest status page and README. No video, no PDF, no cover. |
| Business value | 1 | Slides say no customer, price or pilot exists. Honest, but empty. |

I did not open any of the three winning pages from the other event, and competition.md says it did not either, so I do not claim a gap to them beyond the table above.

## Gallery overlap

The win plan does name the gallery (Aperture, WebScout Exact, AMD Volta, Exact Web Answer Agent, GreYat, SourceCourt, ChronosGraph, ROMA, others) and the past winners. It states plainly that the idea is the same job as Aperture and most of the gallery. It then lists four concrete execution differences from Aperture: contract fit, necessity citations, a committed self-check, and GPU evidence. The fourth does not exist yet. It also admits the difference could shrink to nothing.

Result: the entry is a gallery-shaped product, and the plan does state a difference, so the clone-fail rule does not trigger on its own wording. It is still a weak position. A win needs the hidden-set result, which nothing here can show.

## Links and where the form text is

- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Live: https://amd-ai-league-lablab.vercel.app
- Draft form text: `docs/submission.md` (title, short and long descriptions, AMD statement template, disclosure). Do not paste until it is rewritten from a committed run.
- Slides outline: `docs/slides.md`. Demo script: `docs/demo-script.md`. Demo path: `docs/demo-path.md`.

## Git state

`git status`: `M NEEDS.md` (unpushed, adds the Account check) and one untracked file at the repo root that I did not open. Everything else is committed. Do not commit NEEDS.md until the private email is removed from the Account check.
