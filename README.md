# Trailmark

A contract-shaped web retrieval container for the AMD AI League on lablab.ai, Match 4, Intelligent Web Information Retrieval. An evaluator execs a command-line program with a question. The program finds the one value on a set of pages that answers it, names only the pages that prove it, and returns an empty answer if they do not.

- **Status page:** https://amd-ai-league-lablab.vercel.app (runs no model and serves no answers)
- **Not submitted.** No evaluator has seen it. "Trailmark" is a working name.

## Status: unfinished

**No real model and no AMD GPU has run this code. The stub only tests plumbing.** No AMD run has taken place. The entry is finished only when a real run on an AMD GPU has produced measured, committed evidence.

The AMD account exists, but https://notebooks.amd.com/hackathon says the email is not registered for the hackathon, so no notebook can launch. That is the blocker, as of 2026-11-03. See `NEEDS.md`.

| Part | State |
|---|---|
| CLI, adapter, page sources, index, verifier, supersession, necessity citations, refusal, socket service | Written. Tested on a Mac with a **stub model**, on a fixture site invented for the purpose |
| The stub (`FakeBackend`) | A hand-written script of replies, **not a model**. It is not the required capability, and passing with it is not a finished entry. It exercises plumbing and the plain-code checks |
| Real model code (`trailmark/model_rocm.py`, Qwen3-4B-Instruct-2507 on ROCm) | **Never run.** No weights have been downloaded. Only its refusal paths have run (no torch, stub torch) |
| Whether Qwen3 follows the reply format, how accurate it is, how fast, how much VRAM | **Unknown.** No figure exists, so none is given |
| `Dockerfile` on the mandated base | **Never built.** Static tests only. The base is about 29.2 GiB |
| `amd/run_on_amd.sh` | **Never run on AMD.** Only its no-GPU refusal and its probe with a fake tool and stub torch have run |
| `tools/vram_sampler.py`, GPU string parsers | **Untested on real tool output.** They have only seen sample text written here. Raw output is kept so a fault shows |
| Forward proxy over https (CONNECT) | **Untested.** The http path is tested against a local server |
| `scripts/walk_demo.py` (browser walk of the status page) | **Not run against this version of the page.** A static test checks that the elements it looks for exist |
| Docker mode of the self-check | Run only on a small plumbing image (`python:3.14-slim`, stub model, no GPU). See [Self-check](#self-check) |
| The Match 4 interface | **Unknown.** Assumed from the official Match 3 kit, whose container rules say they apply across the programme. See `docs/competition.md` |

The status page and `/health` (`status`, `entry_state`, `recorded_amd_runs`) read committed evidence in `amd/evidence/` on each request, so they change only when a qualifying run is committed.

## The contract it implements

From the Match 3 kit. **Everything Match-4-specific is UNVERIFIED** and lives in `app/contract.toml` and `app/adapter.py`, so a real spec should mean editing config rather than core code.

```bash
python3 /app/app.py --index /app/corpus    # once: build the index, start the resident model service
python3 /app/app.py --corpus /app/corpus --query-id query_01 --query "..."    # one new process per question
```

Output is `/app/output/query_01_output.json`, written whole:

```json
{"answer": "85", "citations": ["datasheets/kestrel-k7-rev2.html"], "confidence": 0.9}
```

- **Answer:** the value only, with qualifiers kept (`Q3 FY27`) and units dropped (`85 °C` becomes `85`). Prose is rejected.
- **Citations:** an exact set chosen by necessity, as paths for a mirror and URLs over HTTP.
- **Refusal:** exactly `{"answer": "", "citations": [], "confidence": 0.0}`. Any failure inside a query ends up here, never as a missing file.
- `confidence` is 0.9 for any answer and 0.0 for a refusal. It is a fixed label, not a measurement. The kit says it is recorded and never scored.

## How a question is answered

1. **Index (`--index`).** Walk the page source, catching failures per page and recording them in `index/failures.json`. Store normalised text with hashes and build a BM25 index (own implementation, standard library). Start the model service detached and wait for its warm-up generation.
2. **Plan and retrieve.** A short-lived client, which never imports torch, sends prompts over a unix socket. The model suggests search terms, then reads chunks and either proposes values with verbatim spans, asks to search, or picks a link by the index the code gave it.
3. **Verify (plain code).** A span must be on the stored page it names (exact, then whitespace and case normalised), on a page opened in this run. The value must be in a span on token boundaries. Candidates are rejected if they rest on a sibling item's row (K5 when the question says K7), if the question's identifier is on no evidence page, or if the line is text addressed to a model.
4. **Decide (plain code).** Pages that disagree are resolved by withdrawn or superseded markers, then revision labels, then dates. If nothing settles it, it refuses. A value resting only on withdrawn pages is refused too.
5. **Cite (plain code).** Pages are removed one at a time, least authoritative first, and a removal stands if the remaining spans still hold the value and every linking identifier the chain depends on. A page that repeats the value goes. Both pages of a chain through a ticket id stay.

The model never writes the citation list. The verifier proves words are on a stored page. It does not prove the page is true, or that a model read it correctly.

Known limits: PDFs, office files and images are recorded as failures, since pages are assumed to be HTML or text. On a temporary copy of the Match 3 kit's corpus (read only, not in this repo), the index pass stored the 5 text files and recorded 9 failures without raising; the kit's PDFs, spreadsheet, document and images are among those 9, so this code could not answer questions that live in them. There is no vision. Necessity sees chains only through identifiers such as `HV-3310`. The near-miss and subject guards only help when the question names an identifier. Detached service survival under the real harness is UNVERIFIED.

## Page sources

Set `pages.mode` in `app/contract.toml`. How Match 4 reaches pages with no network at grading is unknown, so this is the largest assumption.

| Mode | Meaning |
|---|---|
| `mirror` (default) | A directory of saved pages. The citation is the relative path. Symlinks and paths outside the root are refused |
| `proxy` | HTTP to `pages.allowed_hosts` and/or through the forward proxy `pages.proxy`, starting from `pages.seeds` |
| `live` | Direct internet, with no proxy. Unlikely given the programme's no-network rule |

Network modes keep the guards: only http and https, no credentials in URLs, private, loopback, link-local and metadata addresses refused on every hop, DNS answers pinned, byte and time caps, `robots.txt` respected. An origin the operator configured is the only exception, by exact scheme, host and port. A redirect away from it gets the full policy.

Page text is untrusted. In prompts it sits inside a per-call random fence it cannot close. Text hidden from readers is dropped at extraction. The model chooses pages and links by labels the code built, never by naming a URL or path.

## Run it on a machine with no GPU

Requires Python 3.12 or newer. The CLI needs only the standard library.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Self-check

```bash
.venv/bin/python tools/selfcheck_m4.py --local
```

This uses the stub model and invented pages, with a guard refusing any non-loopback socket in every process it starts. On a machine with no AMD GPU its best possible final line is:

```
PLUMBING CHECKS PASSED (no AMD GPU, no evidence)
```

That says the plumbing works. **It says nothing about AMD, about a real model, or about the hidden test set.** The words `ALL CHECKS PASSED` appear only with the real backend, on a GPU, with measured VRAM in the 1 to 48 GiB band, and even then it is our own harness and not AMD's evaluator.

`--docker IMAGE` runs the kit's flow against a built image, adding fixtures, faults and `--network none --cap-drop DAC_OVERRIDE`. It has been run against `tools/plumbing.Dockerfile` only, with the stub, and it passed. That image is `python:3.14-slim`, the same Python minor version as the mandated base, and it has no GPU or model. So that run shows the CLI starts on Python 3.14 with no network, a mode 000 file really raises and gets recorded, and a detached service survives `docker exec` calls. It has **not** been run against the mandated base, which has never been pulled or built here.

## The first real GPU run

See [amd/README.md](amd/README.md). In short, from a notebook terminal:

```bash
bash amd/run_on_amd.sh --probe-only
bash amd/run_on_amd.sh
```

## Status page locally

```bash
.venv/bin/python -m uvicorn trailmark.server:app --port 8000
.venv/bin/python scripts/walk_demo.py --url http://127.0.0.1:8000
```

`scripts/walk_demo.py` walks part A of [docs/demo-path.md](docs/demo-path.md) in a real browser, for a person to record. Install Chromium once with `.venv/bin/playwright install chromium`.

## AI tool disclosure

Per lablab's Code of Conduct Rule 13: this project's code, tests and documentation were written with substantial help from Anthropic's Claude, through Claude Code, under Alex Veciana Belmonte's direction. No third-party agent framework is used. Claude takes no part in answering questions at run time.

## Licence

MIT. See [LICENSE](LICENSE). Halvard Instruments and the Kestrel products in `fixtures/` are invented.
