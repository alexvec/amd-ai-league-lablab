# REVIEW: Trailmark, AMD AI League, Match 4

Checked 2026-11-03 by fetching and running things, not from the docs. For Alex.

## Verdict: NOT READY to submit as a strong entry. Technically READY to submit as an honest, weak one.

The product works, is honest about itself, and is safe at its public edge. The live URL responds, the repo is public with an MIT licence, and 184 tests pass. But the partner technology does no work in this entry. No AMD account exists, no AMD run has happened, no real model has answered the code, and the container was never built. The live demo is a keyword extractor with no language model, and its answers are often poor. The entry depends entirely on your unperformed notebook run to have any AMD story. The submission text is accurate and says all of this, so submitting now is truthful. It is also the weakest version of this entry. Whether to submit now is your call.

## Blocking, by severity

1. HIGH. No AMD inference exists. `/health` reports `recorded_amd_runs: 0`. The required AMD technology for Match 4 is UNVERIFIED, but the partner focus makes this the largest gap. Only you can close it (step 4 below).
2. HIGH. No AMD Developer Program account, no lablab enrollment, no Discord join. None were done by any agent. Joining the Discord is required for Match participation (competition.md, MAIN). You cannot enroll, run the notebook, or submit without them.
3. HIGH. Match 4 close time unknown. The live event page still says Match 4 is "Live now", but lists no deadline and no submission format for it. Prizes apply only while the Match is live, so you could miss it without knowing. Ask in Discord.
4. MEDIUM. Answer quality on the live demo is weak (details below). A judge who types their own question will likely get a real but unhelpful quote.
5. MEDIUM. Match 4 form fields and limits are unverified. The title, short and long limits used in docs/submission.md are lablab's generic ones. Re-read the live form before pasting.
6. MEDIUM. Container never built. The Docker daemon is not running on this machine. If the Match wants an image, there is none.
7. LOW. Four files have uncommitted edits and three docs are untracked (list below). Nothing in them is secret, but the public repo does not yet contain docs/submission.md, slides, or the demo script.

## Steps for Alex, in order

1. Decide: submit now with version (a) text, or wait for the AMD run. If you want a credible AMD story, do not submit yet.
2. Create the AMD AI Developer Program account via the join link on https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge. Confirm whether a separate lablab account is needed.
3. Join https://discord.gg/lablabai. Ask for the Match 4 close time and the submission format (a form, a container, a URL, or all).
4. Run the AMD notebook job: sign in at https://notebooks.amd.com/hackathon, launch a notebook, then `bash amd/run_on_amd.sh --probe-only` and `bash amd/run_on_amd.sh`, per amd/README.md. Check the new trace (`trace.gpu`, `trace.backend` starts `rocm-`, `gpu_vram_after_run` shows memory in use). Commit it as is, push, redeploy, and confirm `/health` changes. Then fill in template (b) in docs/submission.md only from that trace.
5. Commit and push the untracked docs (submission.md, slides.md, demo-script.md) and the edited files if you want them public. This review did not do it.
6. Record the video (docs/demo-script.md, choose Version A or B), export docs/slides.md to PDF, choose a cover image if the form wants one. None of these exist yet.
7. Re-run `.venv/bin/python -m pytest -q`, re-fetch the event page and `/health`, then paste the text from docs/submission.md into the real form and submit it yourself.

## Links and form text

- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Live: https://amd-ai-league-lablab.vercel.app
- Form text (title, short, long, AMD statement, AI disclosure, extras): `docs/submission.md` in this directory. It is untracked. Use version (a) of the long description and the AMD statement unless the AMD run is done.
- Slides outline: `docs/slides.md`. Video script: `docs/demo-script.md`. Both untracked.

## Rule-by-rule

Legend: MET, NOT MET, CAN'T TELL (rule unverified in docs/competition.md).

| Rule | Status | Evidence |
|---|---|---|
| Match 4 still live | MET | Re-fetched the event page today: "Live now", "Match 4: Intelligent Web Information Retrieval is LIVE." Match 5 "Coming soon · Nov"; Match 6 "Coming soon · Nov 10–14". No Match 4 deadline, end date, or submission format is listed. Only "Final Match ends Nov 14". |
| Submit while the Match is live (prizes) | CAN'T TELL | No close time published. |
| Individual only, one account | CAN'T TELL | No entry made yet. The repo is under your name; no team created. |
| Join lablab Discord | NOT MET | Not done (NEEDS.md says so, and nothing contradicts it). |
| AMD Developer Program SSO / enrollment | NOT MET | Not done. |
| Public GitHub repo (generic form) | MET | `gh repo view`: PUBLIC, default branch main, pushed head c9aab2e matches local. Whether Match 4 needs it: unverified. |
| MIT / open source (TERMS s.16) | MET | GitHub detects the MIT licence; README states it. |
| Working online demo URL | MET | `/` 200 HTML, `/health` 200 JSON, `/traces` 200, real `POST /ask` 200 unauthenticated. |
| Demo video (MP4/MOV, 300 MB, under 5 min) | NOT MET | Not recorded. Generic limit, unverified for Match 4. |
| Slides PDF | NOT MET | Only a markdown outline exists, untracked. |
| Title 5-50, short 50-255, long 600-2,000 chars | MET (generic limits) | Measured the lines in docs/submission.md: 42, 203, 1,294. All correct as stated. |
| Cover image 16:9 | CAN'T TELL | Optional; none made. |
| AI-tool disclosure (CoC Rule 13) | MET | README, submission.md and the demo script each disclose Claude / Claude Code. |
| Originality / no invented claims | MET | No invented metrics, users, testimonials or outcomes found in README, submission, slides, or demo script. Hypotheses are labelled as such. |
| Required AMD tech / model / endpoint for Match 4 | CAN'T TELL | Not published. The entry uses none. |
| Container / endpoint schema for Match 4 | CAN'T TELL | Not published. The schema in `trailmark/api_schema.json` is a guess and says so. |
| Judging criteria | CAN'T TELL | None published for Match 4. |

## Evidence

Tests. `.venv/bin/python -m pytest -q`: three progress lines of 72, 72 and 40 dots, so 184 passed, no failures. This matches README, submission.md and slides (184).

Live endpoints. `/health` returned `backend: extractive-no-llm`, `model: null`, `deployment: vercel-serverless`, `replay_traces: 2`, `recorded_amd_runs: 0`, with a statement that no AMD run has taken place. Both traces in `/traces` and in the repo list `gpu: null`, `inference_on_amd: false`. Their claims are all verified (3 and 1). That matches what the docs say.

SSRF. Each was refused with HTTP 400 and no fetch: `localhost`, `127.0.0.1`, `169.254.169.254`, `file://`, `ftp://`, `http://0x7f000001/`, `http://[::1]/`, port 8080, and credentials in the URL. Response headers carry a strict CSP and HSTS. I did not test DNS rebinding or redirect-to-private paths against the live site; tests/test_netguard.py and tests/test_transport.py cover them offline.

Answer usefulness, my own questions, live, no auth:
- "What does MUST NOT mean?" on the RFC 2119 page. The first claim is the correct definition of MUST NOT, which is good. Two more verified quotes (MUST, SHOULD) are padding. This is better than the failure described in submission.md item 9, but the extras are still noise.
- "Who created the Python programming language and when was it first released?" on its Wikipedia page. Verified, but the answer is a mix: "Van Rossum first released it in 1991 as Python 0.9.0", then a stray quote ("Why was Python created in the first place?") and an unrelated sentence about the AAEC Pascal 8000 Compiler. Partly right, with irrelevant filler.
- "What is the capital of Australia?" with no URL. Answer: "Federal Capital Press of Australia. pp. Australian Capital Territory (Australia) Canberra: history of Australia's national capital." All quotes verified, but it never states in a usable way that Canberra is the capital. Not useful.

So the verifier keeps the answer faithful to the page but not relevant. README, slides and submission text state this limit plainly. That is honest. It is still a poor first impression for a judge.

Repo hygiene. Tracked files hold no `.env`, keys, private email, or age. `.env`, `.vercel/`, `.claude-session.json` are gitignored. All four commits are authored and committed as Alex Veciana Belmonte with the noreply address. No agent name appears in author, committer, or message fields. Note: the tracked CLAUDE.md, AGENTS.md and NEEDS.md mention Claude and a local path to `operator.json`. No contents of that file are in the repo. The README disclosure names Claude Code, which is intended.

Claims check (README, submission, slides, demo script). All true against the code and live behaviour. Confirmed: backend label, 184 tests, 2 traces, 0 AMD runs, container never built (Docker daemon not responding here), MIT, SSRF refusals, 3 verified claims in the MUST trace. The AMD claims go no further than what happened: all say no AMD run has taken place. No benchmark or accuracy figure appears. Two small spots: submission.md item 9 describes the MUST NOT result as quotes about MUST and SHOULD instead of MUST NOT, while today the MUST NOT definition came first, so re-test before recording and narrate what you see. Item 4 lists the AMD account, enrolment and Discord as things for you to confirm; they are not done.

Partner technology. Plainly: today it is a plan, not a result. The live product contains no language model and no AMD hardware. The LLM backend (`trailmark/llm.py`) has only been tested against a stub server. The entry's whole AMD story rests on one notebook run that has not happened. `amd/run_on_amd.sh` is plausible by reading: it stops when no GPU is reported, has a time budget, serves a small model (Qwen2.5-1.5B-Instruct) with vLLM, requires the GPU to be reported before a trace can be labelled `rocm-*`, and pushes nothing. It describes itself as never run on AMD. Unknowns it admits: which GPU, whether vLLM installs, whether the notebook can reach public sites, whether the model fits. Expect possible trouble there. I could not run it here.

Container. Never built. `Dockerfile` exists with a ROCm base (`rocm/dev-ubuntu-22.04:7.2.4`). Docker is not responding on this machine. I did not build it.

## Uncommitted changes (`git status`)

- Modified: AGENTS.md and CLAUDE.md (added a sentence: "Redeem every promo code and platform credit in docs/competition.md before any payment card"). docs/competition.md contains no promo code, so that instruction has nothing to act on.
- Modified: NEEDS.md (adds that the agent claims the $100 AMD GPU credit "before paying for compute"). The credit is "for eligible new members"; eligibility is unverified.
- Modified: STATE.md (stage verify; presentation ticked). I ticked the verify box after this review.
- Untracked: docs/submission.md, docs/slides.md, docs/demo-script.md, and the operator's submit script at the entry root. It exists and is untracked. I did not open or run it.

## NEEDS.md versus what happened

NEEDS.md is internally inconsistent about who creates accounts. The top says "The agent creates the accounts and keys below" and that "The agent now does the rows that are not a payment card or the final submission". The later sections say the agent did none of them, that it does not create accounts or enter passwords on third-party sites, and that "Joining Discord, registering, and submitting must be done by Alex". The later sections match what actually happened: no AMD account, no lablab enrollment, no Discord join, no sign-in anywhere. The `needs-cleared` box in STATE.md is ticked, but the AMD account and Discord rows are still open. That box is misleading.

## What I did not do

No sign-in, registration, post, or submission. Did not open or run the submit script. Did not fix anything. The only edits are this file and the verify box in STATE.md.
