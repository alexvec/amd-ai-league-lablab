# PRD: Match 4, evidence-checked web retrieval agent (working name: Trailmark)

Status: CHOSEN. Working name only; change freely. Sources: docs/competition.md.

## Track rule as sourced
Match 4, "Intelligent Web Information Retrieval", "Live now" (MAIN): build an AI agent that navigates websites, understands a natural-language request, and retrieves the specific information requested. 1,800 points. Close date and timezone: not stated. Submission format, scoring, allowed inference, required model: UNVERIFIED. A non-official participant entry (UNVERIFIED hint) describes a prebuilt Docker image on a required ROCm base with weights included, taking a question plus optional start URL and returning an answer with source URLs.

## User
A researcher or analyst who needs one specific fact from the open web and has to be able to defend it (for example, someone who must cite where a figure or policy came from). This is a persona hypothesis, not a measured user. For the Match, the immediate "user" is the evaluator that sends questions and reads answers and URLs.

## Job to be done
"Find this specific piece of information on the web and show me exactly where it is, so I can trust it without re-reading the pages."

## Concept
An agent that navigates from a start URL or a search step, reads pages, and answers. The differentiator is an evidence contract: every claim in the final answer must cite a source URL and a verbatim quote. A deterministic verifier checks that the quote appears in the stored text of the page the agent fetched. Claims that fail are removed or the agent is sent back to look again (bounded retries). The response contains the answer, the cited claims, and a "verified / unverified" flag per claim. Original work; no third-party agent framework is copied.

## Partner capability doing the work
AMD ROCm and AMD GPUs: an open-weight instruct model served through an OpenAI-compatible server on ROCm (for example vLLM, UNVERIFIED on the notebook) performs the planning, link-choice, extraction and claim-writing steps of the agent loop. The verifier is plain code and is not claimed as AMD work. Model choice is deferred until Alex's notebook shows what fits (target: a model that serves within the notebook's GPU memory; not yet checked). No fine-tuning planned.

## Minimum scope that ships on day one (live URL)
1. Public repo, MIT LICENSE, README, tests, .gitignore.
2. Fetch and extract tools (HTTP fetch, readable-text extraction, link listing, page snapshot stored with hash).
3. Quote verifier with unit tests (exact and whitespace-normalised match).
4. Web UI plus `POST /ask` and `GET /health` (health reports the active backend).
5. Replay mode serving stored snapshots and a recorded trace, clearly labelled as replay.
6. Pluggable inference backend via environment variables (base URL, key, model name); trace records which backend produced it.
7. Deployed URL responding (target: Vercel, per builder rules).

## Explicit non-goals
- No CAPTCHA solving, login walls, paywall bypass, or headless-browser stealth.
- No scraping of sites that forbid it; respect robots.txt and a polite rate limit.
- No fine-tuning, no custom model training.
- No multi-user accounts, billing, or database.
- No claim of official evaluator acceptance.
- No benchmark numbers unless produced by a run that is committed.
- JavaScript-heavy sites are best-effort only.

## AMD engine and how inference runs
- Production shape: container on a ROCm base image (tag UNVERIFIED, take from the official page when found) running the agent plus a local model server; the agent talks to the server over localhost.
- Development on AMD: Alex launches a notebook at notebooks.amd.com/hackathon (3 h/day), starts the model server, runs the scripted evaluation set, and commits the resulting traces. Traces store backend name, model name, GPU string, token counts and wall time as measured.
- Before AMD access exists: same code, backend set to replay or an optional hosted API. The UI shows the backend actually used. A live URL on Vercel is not on AMD hardware and must not be described as such.

## Artifact shape
Two, satisfying both possible rules (neither confirmed as official):
1. Container: Dockerfile on a ROCm base, exposing an HTTP endpoint (question, optional start_url, returns answer, sources[], claims[]). The schema lives in one config file so it can be changed to the official one.
2. Public repo plus live URL, demo video and slides prepared by later stages; Alex submits.

## Demo must show, on real input
- A real question typed by a person, a real public site, live fetches, the agent's navigation steps, the answer, and each claim with its quote highlighted in the stored page.
- A failure case: a claim whose quote is not on the page is flagged and removed or re-searched.
- The trace panel showing backend and model, with the AMD GPU string only if the run was on AMD.
- Questions for the demo are chosen by Alex from live pages at record time; no invented question set or accuracy figure.

## Who pays
Hypothesis, unvalidated: teams that need auditable web research (analysts, compliance and procurement staff, journalists) could pay for answers with checkable evidence. No customers, pilots or prices exist; none may be claimed. For the Match, the payer is the prize pool.

## What would make a judge call it a wrapper
- The only logic is one LLM prompt plus a search API.
- The verifier is absent or cosmetic (quotes not actually checked against stored text).
- The AMD part is a logo: model actually served elsewhere while the README says AMD.
- The demo uses canned answers presented as live.
Defences: verifier tests that fail on fabricated quotes; trace-derived backend labels; replay always labelled.

## Acceptance tests
1. Verifier accepts a quote present in a snapshot and rejects an altered quote (unit).
2. Verifier handles whitespace and case rules as specified (unit).
3. `/health` returns the backend name, and the UI displays that value, not a constant (integration).
4. `/ask` in replay mode returns answer, sources, and per-claim flags matching the declared schema (integration).
5. A response with an unverifiable claim never marks it verified (integration with a stub model that fabricates a quote).
6. Fetcher refuses disallowed schemes and private IP ranges (unit, to prevent SSRF).
7. Playwright walks the demo path in docs/demo-path.md against the deployed URL.
8. Container builds, starts, and answers `/health` (smoke).
9. On Alex's notebook: one real end-to-end question against a live site with a committed trace (manual, needs credentials).

## Credentials it depends on
- None to build, test, and deploy the replay version (GitHub and Vercel auth are builder-side, to be checked).
- AMD Developer Program SSO account (Alex) for any AMD run.
- Optional hosted-model API key (Alex), only if allowed (UNVERIFIED).
- Optional container registry (UNVERIFIED).
- lablab account, Discord membership, and submission: Alex only.
