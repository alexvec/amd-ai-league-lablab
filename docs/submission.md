> **DRAFT, pending the AMD run.** No real model and no AMD GPU has run this code. Nothing here has been submitted. Alex reviews and submits. A submission now would be an entry with no AMD inference in it.

# Submission text: Trailmark (AMD AI League, Match 4)

- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Status page: https://amd-ai-league-lablab.vercel.app
- Track: Match 4, Intelligent Web Information Retrieval (working name Trailmark)

## Field limits used

Generic lablab form limits from docs/competition.md section 5: title 5-50, short description 50-255, long description 600-2,000 characters. UNVERIFIED for Match 4. The event form takes priority, and the evaluator may want an image rather than text. Counts below were measured on the exact text in this file.

## Title (50 characters)

Trailmark: one value, only the pages that prove it

## Short description, true today (195 characters)

A contract-shaped CLI for Match 4: finds one value on a set of web pages, cites only the pages that prove it, returns nothing otherwise. Draft: no real model and no AMD GPU has run this code yet.

## Long description, true today (1268 characters)

Trailmark is a command-line program for an evaluator to exec, built to the container contract in the official Match 3 kit. The Match 4 interface is unpublished, so its assumptions sit in one config file. An index pass walks a page source (a saved mirror by default, HTTP through a guarded fetcher second), catches failures per page, builds a lexical index and starts one resident model service on a unix socket. Each question is a new short-lived process that never imports torch. The model proposes values with verbatim spans. Plain code decides: the span must be on the stored page, pages that disagree are settled by withdrawn markers, revision labels and dates or the program refuses, and citations come from a necessity test that removes pages one at a time. A refusal is an empty answer with empty citations. Status: no real model and no AMD GPU has run this code. The intended model, Qwen3-4B-Instruct-2507 on ROCm, has never loaded. The image on the mandated base has never been built. The tests use a scripted stub on an invented fixture site, and the stub only tests plumbing. There are no accuracy, speed or memory figures. The code is MIT licensed and was written with substantial help from Anthropic's Claude via Claude Code, under the author's direction.

## AMD statement

### True today. This is the default.

No AMD inference has happened in this entry. The status page runs no model. The ROCm path is written and has never run. The email is not yet registered for the hackathon notebook.

### Template for after a real run. Do NOT use until every blank is filled from the committed folder.

Fill each blank from `amd/evidence/<run>/summary.json`, copying what it says. If it has no value for a blank, delete the sentence.

> On [DATE OF THE RUN], [MODEL] ran on [GPU] with ROCm [HIP], in the notebook session, through this project's own self-check on [FIXTURE TOTAL] questions it invented. Peak VRAM from [VRAM TOOL] was [PEAK] GiB. [FIXTURE CORRECT] of [FIXTURE TOTAL] matched. This is one run in our own harness, not AMD's evaluator, and says nothing about the hidden set. The evidence is committed at [PATH].

Then rewrite the short and long descriptions, since their status sentences will have changed.

## AI-tool disclosure (Code of Conduct Rule 13)

This project's code, tests and documentation were written with substantial help from Anthropic's Claude, through Claude Code, under Alex Veciana Belmonte's direction. No third-party agent framework is used. Claude takes no part in answering questions at run time. These submission texts were also drafted with Claude.

## Alex must confirm before submitting

1. A real run is committed, and this file has been rewritten from it.
2. Match 4 is still live, and its close time (not stated on the event page).
3. How Match 4 takes a submission: image, form, or both. UNVERIFIED.
4. The real Match 4 spec has been read and `app/contract.toml` matches it.
5. The AMD Developer Program account (exists), lablab enrolment and Discord membership are done. See NEEDS.md.
6. `/health` still says what the text says. If a new folder was committed, redeploy first.
7. Evaluator acceptance is unknown. Do not claim it.
