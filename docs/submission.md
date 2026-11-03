# Submission text: Trailmark (AMD AI League, Match 4)

Prepared 2026-11-03. Nothing here has been submitted. Alex reviews and submits.

## Read this first

Per the event's partner focus, submitting before the AMD run would be a weak entry. Today no AMD inference has happened and `recorded_amd_runs` is 0. The partner technology does no work in the entry yet. Whether to submit now or after the notebook run is Alex's decision. The default text below is version (a), which is true today.

- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Live: https://amd-ai-league-lablab.vercel.app
- Track: Match 4, Intelligent Web Information Retrieval (working name Trailmark)

## Field limits used

Generic lablab form limits from docs/competition.md section 5: title 5-50, short description 50-255, long description 600-2,000 characters. Source: lablab's delivery and rules pages. UNVERIFIED for Match 4: the rule book found no Match 4 page, and the event form takes priority. Re-read the live form before pasting. Counts below were measured on the exact lines in this file (plain ASCII, spaces counted, no line breaks inside a field).

## Title (42 characters, limit 5-50)

Trailmark: web answers with checked quotes

## Short description (203 characters, limit 50-255)

Ask for one fact from the web. Trailmark reads real pages and quotes the source for each claim. A plain program checks each quote is on the fetched page. The live demo uses a keyword backend, not an LLM.

## Long description, version (a), true today (1,294 characters, limit 600-2,000)

Trailmark is an agent for Match 4. You ask a question in plain language, optionally with a start URL. It fetches pages through a guarded fetcher (http and https only, private addresses refused, robots.txt respected, capped pages and time), stores a snapshot with its SHA-256, and follows links. A backend drafts claims, each with a quote and a source URL. A plain-code verifier checks that each quote appears in the stored text of a page fetched in that run. Exact and whitespace-normalised matches pass. Case is never folded, nothing is fuzzy-matched, and a number in a claim must also appear in its quote. The answer is built only from claims that passed. The limit: a verified quote is really on the page, but it may not answer the question. Status today: the live demo runs extractive-no-llm, a keyword-based backend with no language model, on Vercel. An LLM backend for an OpenAI-compatible server on ROCm is written and tested against a stub only. No AMD run has taken place, no real model has answered this code, the container has never been built, and evaluator acceptance is unknown. There are no accuracy figures. MIT licence, 184 offline tests passing on the build machine. Code was written with substantial help from Anthropic's Claude via Claude Code, under the author's direction.

## AMD statement

### (a) True today. This is the default. Use it.

No AMD inference has happened in this entry. The live URL runs on Vercel with a backend that uses no language model. The ROCm path (an open-weight model served on an AMD GPU) is written but has not been run on AMD hardware.

### (b) Template for after Alex's notebook run. Do NOT use until every blank is filled from the committed trace.

Fill each blank from the new file in `traces/`, copying what the trace says. Leave a blank blank if the trace does not have the value, and then delete the sentence.

> On [DATE FROM trace.recorded_at], Trailmark's LLM backend answered [NUMBER] question(s) in an AMD notebook. The trace reports the GPU as [GPU STRING FROM trace.gpu] and the backend as [trace.backend]. The model was [MODEL FROM trace.model], served by [SERVER AND VERSION]. The run took [MEASURED WALL TIME] and used [MEASURED TOKEN COUNT]. Result: [status, and verified claims out of total claims, copied from the trace]. This is one recorded run, not an evaluation. The live URL on Vercel is [STILL NOT / NOW, per /health] on AMD hardware.

Before using (b), also check that `gpu_vram_after_run` in the trace shows memory in use, as amd/README.md says. Then redeploy so `/health` reads the new trace.

## AI-tool disclosure (Code of Conduct Rule 13)

This project's code, tests and documentation were written with substantial help from Anthropic's Claude, through Claude Code, under Alex Veciana Belmonte's direction. No third-party agent framework is used. The default backend of the live demo uses no AI model. These submission texts were also drafted with Claude.

## Suggested form extras (Alex's choice)

- Categories and technologies: not verified for this event. Safe, true tags today: Python, FastAPI, Vercel, web retrieval. Add ROCm or AMD only after version (b) is true.
- Cover image: Alex's choice. None has been made in the repo.
- Video: MP4 or MOV, up to 300 MB, recommended under 5 minutes (generic limits, UNVERIFIED for Match 4). Script: docs/demo-script.md.
- Slides: export docs/slides.md to PDF.
- Demo application URL: https://amd-ai-league-lablab.vercel.app

## Alex must confirm before submitting

1. Match 4 is still live and its close time (Discord; not stated on the event page).
2. The Match 4 form fields and limits match the generic ones above, and whether it asks for a container, a URL, or both.
3. Whether to wait for the AMD run. See the top of this file.
4. AMD Developer Program account, lablab enrolment and Discord membership are done (see NEEDS.md).
5. The repo is public and the MIT LICENSE is in place.
6. The live URL still responds and `/health` still says what the text says. If a new trace was added, redeploy first.
7. The test count (184) still holds: run `.venv/bin/python -m pytest`.
8. The recorded video shows the backend honestly (see docs/demo-script.md).
9. Production check by Alex: for the RFC 2119 page, the question "What does MUST NOT mean?" returned verified quotes about MUST and SHOULD instead of MUST NOT. This is not in a committed trace. Keep the limit sentence in the long description.
10. Evaluator acceptance is unknown. Do not claim it.
