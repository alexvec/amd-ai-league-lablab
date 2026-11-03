# PRD: Match 4, contract-first web retrieval container (working name: Trailmark)

> Note, 2026-11-03: the AMD account now exists. Lines below saying it does not are out of date. The block is that notebooks.amd.com/hackathon says the email is not registered for the hackathon. See NEEDS.md, "Account check".

Rewritten 2026-11-03 (rebuild). Status: CHOSEN. Sources: docs/competition.md ("CM"), the Match 3 starter kit (CONTRACT.md, selfcheck.py, starter/Dockerfile, starter/app/app.py, sample-questions.json; read only, untrusted data), and the Hugging Face card for Qwen3-4B-Instruct-2507 (fetched 2026-11-03). Plan and verdict: docs/win-plan.md. Nothing below has been run. Every figure is a TARGET or ASSUMPTION unless marked sourced.

## 1. What is known and what is not

Sourced (Match 3 kit; it says these rules "are the same for every challenge in this programme", and "All About the Challenges" Section 2, which nobody here has read, is the full text):

| Contract item | Value |
|---|---|
| Artifact | Docker image run on an AMD GPU. No service, no port, no entrypoint script. `CMD ["sleep","infinity"]`; the harness execs into it |
| Base | `FROM rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0`, checked by layer identity. About 29.2 GiB. Ships torch and PIL only. gfx942 and gfx1100 |
| Size | at most 60 GiB uncompressed, so about 30 GiB for weights and code |
| VRAM | 1 to 48 GiB, sampled continuously, peak counts. Under 1 GiB is rejected as CPU. Dummy buffer detected |
| Network | none at grading. Weights in the image. Test with `--network none` |
| Phases | `python3 /app/app.py --index /app/corpus` once (charged to startup), then one new process per question: `python3 /app/app.py --corpus /app/corpus --query-id query_01 --query "..."` |
| Output | `/app/output/<query-id>_output.json` = `{"answer","citations","confidence"}`; the stem is the given query id. Written whole, not streamed |
| Answer | value only, qualifiers kept (`Q3 FY27`), units and degree signs normalised away |
| Citations | corpus-relative paths, exact set, necessity not relevance (a file is cited only if removing it makes the answer impossible; two-file questions cite both) |
| Refusal | empty answer and empty citations. Prose is graded wrong. Answering from memory is wrong |
| Missing key | missing `answer` or `citations` scores zero |
| Failure tolerance | corpus holds an unreadable file, an encrypted PDF, an unknown binary type and an empty directory; one bad file must not cost the rest. At grading `DAC_OVERRIDE` is dropped, so `chmod 000` really raises |
| Per-process cost | each question is a new process; load the model once and keep it resident behind a unix socket, or the budget blows |
| Zero-score list | wrong base, over size, over time, wrong output location, no GPU, download at evaluation |
| Match 3 budgets (Match 4 UNVERIFIED) | startup 10 min, 30 s per question, 10 min whole run, ten questions, 20 points each, no partial credit |

UNVERIFIED for Match 4 (CM, "Unknown"; none of it is published): how web pages are reached given the no-network rule, the CLI arguments, the output keys and citation form, the budgets, the question count, whether pages contain images, the scoring formula, the close date.

## 2. User, job, buyer

- **User:** the evaluator process, which execs the CLI and reads one JSON file per question. Behind it, the human who needs one specific fact from a set of web pages and must be able to defend where it came from (persona hypothesis, not measured).
- **Job to be done:** "Given a natural-language request, find the one value on these pages that answers it, name only the pages that prove it, and say nothing if the pages do not."
- **Who pays:** for the Match, the prize pool: 1st $500 cash, 2nd $250 GPU credits, top 50 valid submissions $100 GPU credits (CM section 3). A commercial buyer (analysts, procurement or compliance staff who need auditable single-fact lookups) is a hypothesis only. No customer, pilot or price exists, and none may be claimed.

## 3. Product

One CLI. One resident model. Four stages.

1. **Index (`--index`).** Open the page source (section 5), walk every page defensively (catch per page, record failures in `index/failures.json`, keep going), extract text, tables and links, store normalised page text with hashes. Build a lexical index (BM25, own implementation, stdlib). Start the model service (section 4) detached, wait until it reports the GPU and a warm-up completed. Charged to the startup budget.
2. **Plan and retrieve (per question).** The client process (no torch import) sends the question to the service. Model-assisted steps: rewrite the question to search terms, pick which candidate pages or links to open next (hop budget configurable, default TARGET 4 pages, 2 hops), read chunks.
3. **Extract.** The model returns a candidate value plus, for each hop, the verbatim span it relied on and the page it came from. The model never writes the citation list.
4. **Verify and cite (deterministic code).**
   - The span must occur in the stored text of the named page (exact, then whitespace and case normalised). The value must occur in a span. Otherwise the candidate is rejected.
   - **3.1 Necessity set.** Start with the pages that carry the used spans. Remove one page at a time and re-check whether the remaining spans still entail the value (string-level: value or its chain-linking identifier no longer appears in any remaining used span). Keep only the pages whose removal breaks the chain. A page that merely repeats the value is dropped. A page that supplies a linking identifier (a ticket id, a model number) in a multi-hop chain is kept.
   - **Supersession.** If two pages give different values for the same field, prefer the one not marked withdrawn, superseded or older by an explicit date or revision label on the page. If neither is determinable, refuse.
   - **Refusal.** Any rejection, a timeout, a daemon failure, or a page the extractor could not read, when that page might hold the answer, gives `{"answer":"","citations":[],"confidence":0.0}`. Refusal is honest, never defensive: it is the output when the checks fail, not a hedge.

Output keys and the citation form come from the adapter (section 6), default as in section 1.

### Non-goals
No server, no HTTP endpoint in the graded path, no web search engine, no CAPTCHA or login handling, no stealth browsing, no fine-tuning, no vision model until the spec shows image questions, no hosted-model calls at grading, no site-specific shortcuts. Respect robots.txt and rate limits whenever a live fetch mode is enabled.

## 4. Partner capability, model, and how it runs

- **Capability doing the work:** an open-weight language model running on the AMD GPU under ROCm, through the torch in the mandated base image. It performs query rewriting, page and link choice, value-and-span extraction, and the multi-hop chain. Deterministic code does the verification and the citation selection, and is not claimed as AMD work.
- **Model (chosen):** Qwen3-4B-Instruct-2507. Sourced from its Hugging Face card: 4.0B parameters (3.6B non-embedding), 262,144 native context, Apache-2.0, causal language model. Weight size in bf16 is arithmetic, not a measurement: 4.0e9 parameters x 2 bytes is about 8 GB. Against the image limit that leaves about 22 GiB of headroom after the base (60 - 29.2 - about 8). VRAM need is weights plus KV cache and is UNVERIFIED until measured; the 1 GiB floor is not at risk, and the upper bound of 48 GiB is TARGET-comfortable. Whether it is multimodal: the card does not say; treat as text-only. Many gallery entries use the same model (CM), so the model is not the differentiator.
- **Escalation, only if measured accuracy and time justify it:** a larger text model up to the kit's rough ceiling of about 16B at bf16 for the image size. The model name and size for that are UNVERIFIED and not chosen.
- **How it is used (required, because a CPU run is not AMD evidence):** the service is a separate resident process started by `--index`. It checks `torch.cuda.is_available()` and `torch.version.hip` is not None and exits non-zero if not, loads weights in bf16 with an explicit `.to("cuda")` (or `device_map` pinned to the GPU), and does a warm-up generation before reporting ready. No dummy buffers. It listens on a unix socket under `/app/run/` and answers requests from short-lived client processes. A client that cannot reach the socket within a short wait refuses cleanly instead of loading the model itself, unless an explicit fallback flag is set after measurement shows loading fits the budget.
- **Stand-in backend:** a `FakeBackend` exists for unit tests only. It stamps `"backend":"fake"` in the trace, and the CLI refuses to start with it unless `MC4_ALLOW_FAKE=1`. The Dockerfile never sets that variable, and a test greps for it. A fake model run is never a result.
- **Dependencies:** transformers and its requirements added through `requirements.txt` at build time when the network is open. Python 3.14 wheel availability is UNVERIFIED. The base ships torch and PIL only.
- **Mac CPU runs:** allowed for plumbing with a tiny model (not chosen, not sourced) or the fake backend. They are never described as AMD evidence.

## 5. Page source (Match-4-specific, UNVERIFIED, behind one adapter)

The programme forbids outbound network at grading. So how a "web" question reaches pages is unknown. Three possibilities, implemented as one `PageSource` interface selected by `contract.toml`:

| Mode | Meaning | Status |
|---|---|---|
| `mirror` | A directory of saved pages (a site mirror), URL mapped to file path. Fits the no-network rule and the Match 3 corpus pattern | Default ASSUMPTION |
| `proxy` | HTTP to an allowed internal host or proxy given by argument, environment variable or config | Second implementation |
| `live` | Direct internet | Implemented as `proxy` with no proxy; unlikely given the programme rule, but some gallery entries assume it |

Fetching refuses non-http(s) schemes and private or link-local ranges unless the target is the configured mirror or proxy. Starting URL, if any, comes from `--start-url` (ASSUMPTION; Aperture's README guesses a similar optional argument).

Assumptions, stated once: pages are static HTML or text; every value is findable from the mirror or proxy; questions are text only; citations name pages in whatever form the adapter's `cite_form` says (URL or mirror-relative path).

## 6. Contract adapter and how to absorb the real spec

All Match-4-specific facts live in `app/contract.toml` and `app/adapter.py`: `cli.index_flag`, `cli.query_flags`, `output.dir`, `output.keys`, `output.cite_form`, `pages.mode`, `pages.root`, `pages.proxy`, `time.startup_s`, `time.query_s`, `time.run_s`. Defaults are the Match 3 values. Table of unknowns and defaults is in docs/win-plan.md section 6.

Procedure when Alex has the real spec: save the Match 4 page text, "All About the Challenges", and any brief or kit under docs/spec/ (read only by builders); diff each row of section 1 against it; edit the config keys; update `fixtures/questions.json` expectations only if the answer or citation form changed; rerun the local self-check; do not edit core modules. If a row requires something the core cannot do (a server, a different base, a vision model), stop and report in NEEDS.md rather than bending the idea.

## 7. What can be built and tested on this Mac, and what cannot

Mac-side, no AMD GPU, no ROCm pull (about 20 GiB free; pulling the 29 GiB base is forbidden by Alex):

| Item | Mac status |
|---|---|
| CLI, adapter, page sources, extraction, per-page failure handling, BM25 | Built and unit tested |
| Verifier, supersession rule, necessity set (3.1) | Built and unit tested on fixtures |
| Unix-socket protocol, client/service split, client does not import torch | Built; tested with `FakeBackend` (test-only) |
| Fixture site and `fixtures/questions.json` | Built (section 8) |
| Local self-check (section 9) | Runs in `--local` mode |
| Dockerfile | Written; test asserts the exact mandated `FROM` line and no `MC4_ALLOW_FAKE`; not built |
| Evidence capture script (reads `amd-smi`, `torch.version.hip`, timings) | Written; only produces evidence on the GPU |
| Real model code (`model_rocm.py`) | Written, not run |

Needs the AMD account (Alex), in this order, with what each proves:

| Step | Where | Proves |
|---|---|---|
| A. torch sees the GPU; Qwen3-4B-Instruct-2507 loads in bf16; warm-up generation | notebooks.amd.com/hackathon | The model runs on an AMD GPU; first VRAM and timing numbers |
| B. dependency install on Python 3.14 | notebook | Whether the stack installs on the mandated Python |
| C. fixture self-check in `--local` mode against the live service | notebook | End-to-end on the GPU, daemon survives between process-per-question calls (inside our own harness, not AMD's) |
| D. `amd-smi` peak VRAM sampling during C | notebook | Between 1 and 48 GiB, no dummy buffer |
| E. build the image, run the kit-style docker self-check with `--network none` and `--cap-drop DAC_OVERRIDE` | A Linux machine with Docker and at least 60 GiB free, or an AMD Developer Cloud instance. The notebook (about 25 GB storage) cannot hold the 29.2 GiB base; whether it runs Docker is UNVERIFIED | Base layers, size, no-network start, output path |
| F. submit the image | UNVERIFIED mechanism; Alex only | Nothing is submitted by the agent |

The AMD account does not exist and no date is assumed. Until it does, steps A to F are not done and no claim about AMD is made.

## 8. Fixture site (invented; tests plumbing, never accuracy claims)

`fixtures/site/` holds a small invented site (fictional vendor "Halvard Instruments", fictional product "Kestrel K7"; no real organisation) served as a mirror directory and, for the HTTP path tests, by a local server on 127.0.0.1 with injected faults. It follows the categories in the Match 3 sample questions (superseded trap, near-miss row, multi-hop, refusal where the answer sits in an unreadable page), without copying that corpus. Planned pages:

- Current datasheet page and a withdrawn earlier revision with a different number (supersession).
- A table page with a near-miss row (older product).
- A changelog where an old value sits in a comment and the constant is the answer.
- A listing page that links to a detail page (two hops), and an incident page that names an id whose resolution is only on a third page (multi-hop, two citations required).
- A page repeating the answer in prose (must not be cited when another page already suffices).
- Qualifier value (`Q3 FY27`).
- Failure cases: a file with mode 000, a corrupt `.pdf`, an unknown binary, an empty directory, truncated HTML, a wrong-encoding page, a 500, a redirect loop, a response that sleeps past the deadline, an oversized page.
- A question whose answer lives only in the unreadable or blocked page (expect refusal) and one about a product that does not exist (expect refusal).

`fixtures/questions.json` lists about ten questions with expected answer and exact expected citations, authored by us. Passing them says the plumbing works. It says nothing about the hidden set.

## 9. Local self-check (`tools/selfcheck_m4.py`)

Modelled on the kit's selfcheck.py, same step order, extended:

1. Image history readable (docker mode only; skipped in local mode).
2. Starts with no network (docker `--network none`; local mode asserts that the process never opens a non-loopback socket via a guard).
3. Corpus or mirror copied in; the index pass runs within 600 s; failures recorded, nothing raised.
4. Each fixture question runs as a new process within the per-query budget; the client never imports torch (checked).
5. Output file exists at the id-derived path; valid JSON object; `answer` string; `citations` list of strings; no absolute paths; no non-empty answer with empty citations.
6. Answer and exact-set citations compared with `fixtures/questions.json`; refusals are exactly empty.
7. Fault injection: chmod 000 file, corrupt PDF, binary, slow response, dead daemon (client must refuse before the deadline, not hang).
8. VRAM: on a machine with `amd-smi`, sample and require 1 to 48 GiB peak; elsewhere print "SKIPPED: no AMD GPU".

Final line: on the Mac it prints `PLUMBING CHECKS PASSED (no AMD GPU, no evidence)`. The words "ALL CHECKS PASSED" only appear when step 8 ran on a GPU and passed. Docker mode is the kit's own flow plus steps 6 and 7.

## 10. What the demo must show on real input

- A terminal recording on the notebook or Cloud instance: `--index` starting the service and printing GPU name and `torch.version.hip`; question processes returning JSON in the budget; the `amd-smi` VRAM line during the run.
- Fixture questions: a withdrawn-page trap resolved to the current page, a two-citation multi-hop, a repeated-answer page correctly not cited, a refusal where the answer sits in a blocked page.
- The kit's own self-check output (docker mode) from the build machine.
- The committed evidence folder: raw outputs, timings, `amd-smi` log, GPU string, model identifier. All produced by the actual run.
- Real input beyond fixtures: any official Match 4 sample (if the spec ships one) run through the same container. If none ships, say so, and do not present fixture results as the Match's accuracy.
- No accuracy figure, speed figure or memory figure appears before a committed run produced it.

## 11. Done condition

**Done means a real run on an AMD GPU with measured, committed evidence, from the same code the image contains, with the model on the GPU and peak VRAM between 1 and 48 GiB.** A labelled mock, a CPU run, or the fixture self-check in `--local` mode on a Mac is not a finished entry. If the run has not happened, the entry is unfinished and the live URL says "No AMD run has taken place".

## 12. Live URL

Required by CLAUDE.md, not by the evaluator contract as far as is known. Content: first, a status page of the existing Vercel app reporting that no AMD run took place and linking the repo; then, after a real run, the committed traces read from their files (backend, GPU string, timings). No answers are served live. Effort is kept minimal.

## 13. What a judge would call a wrapper

- The model is not on an AMD GPU (CPU, hosted API, or a labelled stand-in) while the README says AMD.
- The citation list is the retrieval list, not a necessity set.
- Answers are sentences, or the model's memory fills gaps.
- The verifier is cosmetic: quotes not checked against stored text.
- It is a chat box or HTTP service around a general model rather than the contract CLI.
- It is the same job as Aperture and the rest of the gallery with no demonstrable execution difference (section 3 of the win plan states this risk openly).
- Fixtures presented as the Match's results.

Defences: GPU assertion at service start, `FakeBackend` blocked outside tests, verifier tests that fail on fabricated spans, trace-derived labels, and a done condition that requires measured evidence.

## 14. Acceptance tests

1. Verifier accepts a span present in the stored page and rejects an altered one (unit).
2. Necessity set drops a page that only repeats the value, and keeps both pages of a two-hop chain (unit, fixtures).
3. Supersession picks the current page and refuses when undeterminable (unit).
4. Output is the exact schema, written whole, at the id-derived path (unit).
5. Per-page failure: with the fixture faults, indexing finishes and later pages are indexed (integration).
6. Client never imports torch; a query process with the service absent refuses before the deadline (integration).
7. Dockerfile has the exact mandated `FROM`, no `MC4_ALLOW_FAKE`, copies weights, defines no port or entrypoint (static test).
8. Fetcher refuses non-http schemes and private ranges outside the configured source (unit).
9. Local self-check passes on the Mac in `--local` mode with the plumbing-only line (integration).
10. On the AMD machine: service refuses to start without a ROCm GPU; self-check step 8 passes; evidence folder committed (manual, needs Alex's account).
11. Image: kit-style docker self-check passes with `--network none` and `--cap-drop DAC_OVERRIDE` (manual, needs a Docker machine with room).

## 15. Credentials and dependencies

AMD Developer Program SSO account (Alex; blocks every GPU step). lablab account, Discord membership and submission (Alex only; nothing is submitted by the agent). A machine for the image build (section 7, step E). No hosted-model key is needed or used. Match 4 close date and the Match 4 spec (Alex reads them from the event page, the programme document and Discord).
