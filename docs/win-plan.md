# Win plan: AMD AI League (lablab.ai), Match 4 rebuild

Rewritten 2026-11-03 on the operator's rebuild order. Rule book: docs/competition.md (cited as "CM", with its section names). Product spec: docs/prds/match-4.md. Nothing here was registered, signed in, posted or submitted. Anything not sourced in CM or the Match 3 kit is marked UNVERIFIED, TARGET or ASSUMPTION. No result in this plan has been measured.

## 0. Verdict, stated plainly

**Track: Match 4, Intelligent Web Information Retrieval. One track.**

**Under what is known today, this plan does not win the $500 first prize by being a better idea. It wins only if all of the following hold:**

1. The Match 4 spec follows the programme-wide container contract in the Match 3 kit (CM, "Official evaluator contract evidence"). The kit says those rules "are the same for every challenge in this programme". Match-4-specific parts are unknown (section 6 of the PRD).
2. Alex gets an AMD account and a real GPU run happens while Match 4 is still live. The Match 4 close date is UNVERIFIED (CM section 2), and "Prizes apply only to submissions made while the Match is live" (CM section 3).
3. The image passes the evaluator's hard gates: mandated base by layer identity, size, GPU use, time budgets, no network, output file. The kit lists these as score-zero conditions.
4. It then reaches the top of the hidden-set accuracy ranking. That is a contest against at least nine gallery entries of the same shape (section 4), and the ceiling may be shared: seven MC3 teams are listed at 10/10 and three MC2 teams at 10/10 (CM, Past winners). If Match 4 also has a ceiling, ties are likely and the tie-break rule is UNVERIFIED.

**Realistic expectation, given what is known:** the achievable and defensible target is a valid, evaluator-accepted submission, which is the floor for the top-50 $100 GPU-credit prize and for the Match's 1,800 points (whether points go to every valid submission is UNVERIFIED). First place is conditional on item 4 and cannot be promised. If conditions 1 to 3 fail, the expected result is no prize. I am recommending this plan because it is the only one where a prize-eligible submission exists today, not because I expect to win it.

**Why the previous keyword app lost (operator's finding, accepted):** no AMD model ran, so the required stack was never exercised. That entry is void. This plan makes the done condition a real AMD GPU run with measured evidence (section 7).

## 1. How this is scored

This is an automated-evaluator contest. CM section 6 records that no judging criteria are published for any Match, that the generic lablab business rubric (Presentation, Business value, Application of technology, Originality) applies only if an event page says so, and that MAIN does not say so. LIVE says "Graded by AMD's evaluator". So the lablab 1 to 5 rubric is not used here, and the old plan's rubric table is dropped.

Criteria used instead, taken from the Match 3 kit (the only official evaluator contract seen; Match 4 may differ):

| Criterion | Source | What passes |
|---|---|---|
| Built on the mandated base | kit CONTRACT.md | `rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0`, layer identity |
| Image size | kit | at most 60 GiB uncompressed; base is 29.2 GiB, so about 30 GiB for weights |
| GPU used | kit | peak VRAM 1 to 48 GiB, sampled; under 1 GiB rejected; dummy buffer detected |
| Network | kit | none at grading; weights in the image; test with `--network none` |
| Time | kit (Match 3 numbers) | startup 10 min, 30 s per question, 10 min whole run. Match 4 numbers UNVERIFIED |
| Output | kit | `/app/output/<query-id>_output.json` with `answer`, `citations`, `confidence`. Missing field scores zero |
| Answer | kit | value only, qualifiers kept, units normalised away |
| Citations | kit | exact set, necessity not relevance |
| Refusal | kit | empty answer and empty citations; prose is wrong |
| Per-item failure | kit | one unreadable file must not cost the rest |

Ideas are scored on one question: how likely is each to clear every row above on a hidden set, with the information available now.

| Option | Open for prizes | Contract known | Clears the table | Verdict |
|---|---|---|---|---|
| Match 4, contract-first web retrieval container | Yes (close date UNVERIFIED) | Pattern known; Match 4 specifics unknown | Plausible; depends on Alex's GPU run | Chosen |
| Match 4, the old keyword app plus HTTP server | Yes | Violates the pattern (server, port, no AMD model) | No | Void |
| Match 5, code repair | No ("Coming soon, Nov") | Harness, repos, language unknown | Cannot be tested | Not now |
| Match 6, unknown game (Nov 10 to 14) | No | Game and harness do not exist yet | Cannot be tested | Not now |
| Match 3 | Closed for prizes, open for points | Fully known | Prize: none | Not a track (see 5) |

## 2. Past winners and comparable entries, and the level they reached

This event (AMD AI League): no winners are published for Matches 1 to 3 (CM, Past winners). Score listings only: MC2 teams Nyctophile, J-I-N, TEST TEST each 10/10; MC3 teams System Builder, AMDLab, Knight Eterniti, AIDLC, Athos Felipe, Moyu-Sentinel, Saudi Sign Intelligence each 10/10. Level reached: a ceiling score from an automated evaluator. I know nothing about what those projects did. The lesson is that a clean pass is not rare; a pass is the entry ticket, not the differentiator.

Different event (AMD Developer Hackathon 2026, judged, hybrid, finished; not this League):
- 1st: Chaos Economy, Multi-Agent RL Market Simulator, by TechMavericks.
- 2nd: Strike Lab. 3rd: Automato by BISAKOLAI. Shortlisted without placement: StudioMI300, Lumi, AtlasOps.
- I did not open any of the three winner pages (CM). What they showed and which AMD capability did the work is UNVERIFIED. I do not use them as a quality benchmark.
- REPOMIND, same event, placement unverified. It published an evidence pack (7 JSON results, 5 plots, raw outputs, rocm-smi, benchmark scripts) and said one MI300X ran a Qwen3-Coder-Next-FP8 workload. Self-reported, not checked by me.

What I take from them, labelled as derived: the highest-profile entry from the nearest AMD event showed hardware-specific proof and committed raw output. This League's evaluator may not read any of that, but Alex's own judge-checkable record is the same kind of artifact: `amd-smi` VRAM log, `torch.version.hip`, GPU name, per-question wall times, raw outputs. That is the level this plan commits to reaching. It does not copy any project. A hardware evidence pack is a practice, not a product, and REPOMIND is a coding agent on a different Match topic.

## 3. Match 4 gallery and how this product differs

All gallery facts below are the participants' own descriptions, unofficial, and no scores are visible (CM, Match 4 gallery). I do not claim any rival fails. What is known about each is stated; where I cannot see a difference I say so.

Honest base rate: CM records that nearly every entry converges on "question plus optional URL in, one exact value plus source out, empty answer when unsupported, local Qwen3-4B on the ROCm image, no external API keys". Evidence-checked retrieval is therefore the default shape, not a difference. **The idea is not different. If there is a difference it is execution against the contract, and whether that matters is decided only by the hidden test set.**

| Entry | What is known (own description) | How this product differs, concretely, or does not |
|---|---|---|
| Aperture | Question plus optional start URL in; answer plus source URLs out; structure-preserving parsing; checks literal support, provenance, answer type, qualifiers; empty answer if unsupported; Qwen3-4B-Instruct-2507; prebuilt image with weights, pinned ROCm digest; README says its contract "is a guess"; page says AMD GPU execution and evaluator acceptance "have not yet been verified"; fresh process per request with a 24 s deadline (search snippet only) | Same model, same abstain behaviour, same concept. Stated differences: (a) our contract is built from the official Match 3 kit rules (exact-set necessity citations, two-phase index then query, resident model on a unix socket, per-page failure tolerance, `--network none`); Aperture's I/O is its own guess (`sources` key, a start URL argument). (b) Our citation set is computed by a necessity test (section 3.1 of the PRD), not by listing support. (c) A local self-check modelled on the official one and a fixture site with injected failures, committed. (d) GPU evidence will be committed once it exists. Where Aperture's guess happens to match the real spec, (a) is no difference. I cannot see Aperture's code beyond its README, so (b) may or may not differ in practice. |
| WebScout Exact | One exact value plus source page, JSON file; answer normalised for the grader; one Docker container on the ROCm PyTorch image; local Qwen3-4B; self-reports 7 of 8 on its own test set | Same shape. Our normalisation follows the kit's rule (value only, qualifiers kept, units dropped). No difference in concept; differences only in the listed engineering. |
| AMD Volta | Multi-hop; HTML tables to Markdown; search fallbacks; abstains on fictional hardware | Multi-hop and table handling overlap with ours. We do not use search-engine fallbacks (no network at grading). |
| Exact Web Answer Agent | Single value plus source; empty answer rather than guess | Same shape. |
| GreYat Web Scout | Exact value; reads package registries for "latest version" | We do no site-specific shortcuts; if versions appear we handle them as page content. |
| SourceCourt Exact Lite | Exact answers when sources support; refuses otherwise; SSRF protections; CLI and container | Same shape. SSRF guard is on our list too; not a difference. |
| ChronosGraph | 6-page, 2-hop budget; verbatim quote with SHA-256 receipt; prefers newer figures; refuses fictional queries; public demo on CPU (its own description) | Quote receipts overlap with our verbatim-span check. Our supersession handling (withdrawn and stale pages) overlaps with its "newer figures" preference. No claim of better. |
| ROMA | Normalised values plus source URL; resident local model; literal-substring verifier; empty on ungrounded queries | Resident model and literal verifier overlap with ours. |
| Trifecta Checker, AI Evaluation Lab | Not Match 4 retrieval products (one mentions Match 4 only as a planned extension) | Different job. |
| GitHub-only: Source Trail, Tega1234567890/amd-match4-agent, Rafa-Innerchispa, Ghafardesk, others | Several state that the Match 4 interface was unpublished as of their dates (before 2026-11-03) | No comparison possible. |

Summary of the claimed differentiator, with its limits: the same job as Aperture and most of the gallery, executed to the programme contract with an evidence record. It is a bet that execution details decide the score (unreadable pages, necessity-only citations, time budgets, resident model, network off). It is not a bet that our idea is better. If the real spec is simpler than the kit pattern, or the hidden set does not test these cases, the difference shrinks to nothing and the outcome is a coin toss against the field.

## 4. Match 4 now, or wait for Matches 5 and 6

Decision: **Match 4 only. No second track.**

- A contract pattern is now known. That lowers spec risk for Match 4, whose container rules are stated as programme-wide. It does not lower it for Matches 5 and 6: their tasks (repo repair, an unknown game with token accounting) have no published harness, and the kit's rules only cover the container, not the task. Building for them now would still be a guess.
- Points rise on later Matches (M4 1,800, M5 2,100, M6 2,400; CM section 7), but prizes need submission while the Match is live (CM section 3). M5 has no dates. M6 is Nov 10 to 14 (year and timezone unstated). A path through M6 requires the game spec to appear and an AMD GPU session to exist inside a window of five days. The AMD account does not exist yet, and a search snippet (UNVERIFIED) suggests approval can take 2 to 3 business days. Waiting for later Matches therefore risks having no entry at all.
- The chassis is Match-agnostic and is built so it can be reused: two-phase CLI, resident model behind a unix socket, per-item failure isolation, GPU assertion, evidence capture, local self-check. If Match 4 closes before Alex's first GPU run, or its spec rules the product out, that chassis is retargeted once the Match 5 or 6 spec is readable. No Match 5 or 6 task code is written until then. docs/prds/match-5.md and match-6.md stay as contingencies and are not altered here.
- Match 3 (closed for prizes, open for points, with an official kit and self-check) is not a track. Using its sample corpus, read-only from the kit path, as an extra local chassis test is allowed. Submitting to it for points would be Alex's decision. It has value because it is the one place the real contract is fully known, so a first GPU run there tests the chassis against official rules. This is a note, not a plan item.

## 5. The hard constraint: no AMD account

No AMD account exists, and the agent cannot create it (CLAUDE.md allows account creation, but the operator states this one cannot be done by the agent). Every step that needs a GPU belongs to Alex until he has the account. No date is assumed.

What is done on the Mac, without an AMD GPU, without pulling the 29 GiB base image (about 20 GiB free; ROCm pull forbidden by Alex):
- All Python code: CLI, contract adapter, page sources (mirror directory and HTTP/proxy), HTML and text extraction, per-page failure handling, quote and answer verifier, necessity selection, unix-socket daemon and client, evidence capture script, and the model class itself (written against transformers and torch, not run).
- A fixture site (invented pages with injected failures) and a local self-check modelled on the kit's selfcheck.py. See the PRD.
- Unit tests, the process-per-question timing of the client (no torch import), the socket protocol, behaviour with the model service absent.
- A Dockerfile whose `FROM` is the mandated line, with a test asserting that exact string. It is not built on the Mac. Optionally, a plumbing-only `docker run --network none` on a tiny non-ROCm image if the daemon works, labelled as not evidence.
- A CPU run of a tiny model on the Mac for plumbing is allowed but yields no AMD evidence and must not be reported as one.

What can only be proven on notebooks.amd.com/hackathon (3 h per day running time, idle counts, about 25 GB; MAIN FAQ):
- That torch sees the GPU (`torch.cuda.is_available()` true and `torch.version.hip` set) on the mandated image.
- That Qwen3-4B-Instruct-2507 loads and runs on the GPU, its wall time per question, and the peak VRAM from `amd-smi`.
- That the pip dependencies install on Python 3.14 (the base uses py3.14; wheel availability for transformers' dependencies there is UNVERIFIED).
- That a resident daemon started by the index pass survives the end of that process. This is a harness behaviour. The kit says to "keep the model resident behind a unix socket", but how the harness's exec treats a detached child is UNVERIFIED.
- The committed trace and evidence.

What neither the Mac nor the notebook can do (a third place is needed): build and self-check the image. The base is 29.2 GiB, the notebook has about 25 GB of storage, and the Mac is forbidden to pull it. Whether the notebook can run Docker at all is UNVERIFIED. Likely needs: a Linux machine with Docker and at least 60 GiB free, or an AMD Developer Cloud instance (needs the AMD account and possibly a payment card, CM section 2, UNVERIFIED). Where and how the image is submitted is UNVERIFIED (registry push or upload). These are Alex's steps, and are recorded as unknowns, not assumed.

## 6. Absorbing the real Match 4 spec quickly

Alex reads the Match 4 page and the programme document "All About the Challenges" (Section 2 was not read by anyone here) and, if there is one, a Match 4 brief or kit. Drop them as files under docs/spec/ (not opened or edited by me). Then one pass of changes, all confined to the adapter (`app/contract.toml` plus `app/adapter.py`):

| Unknown | Config key | Default assumption |
|---|---|---|
| How web pages are reached (mirror directory, allowed proxy or host, live web) | `pages.mode`, `pages.root`, `pages.proxy` | mirror directory, with HTTP-via-proxy as the second implementation |
| Index phase argument | `cli.index_flag` | `--index <path>` |
| Query arguments | `cli.query_flags` | `--query-id`, `--query`, optional `--start-url` |
| Output path and key names | `output.dir`, `output.keys` | `/app/output/<query-id>_output.json`, `answer`, `citations`, `confidence` |
| Citation form (URL or relative path) | `output.cite_form` | `url` if the pages are served by host, relative path if a mirror directory |
| Budgets | `time.startup_s`, `time.query_s`, `time.run_s` | 600, 30, 600 (from Match 3) |
| Questions: counts, images in pages | none | text only; image questions are a contingency, not built |

If the spec matches the defaults, nothing changes. If it differs, the change is these keys plus fixture and self-check updates. The core (extraction, verification, necessity, daemon, model) is not supposed to change.

## 7. Done condition

The entry is not finished until a real run on an AMD GPU has produced committed, measured evidence: `amd-smi` VRAM peak between 1 and 48 GiB, `torch.version.hip`, GPU name, the model's identity, per-question wall times against the budget, and the raw outputs. A fake or mock model never counts. The CLI refuses to start with a stand-in backend outside tests. If the run does not happen, the finished-entry claim is not made, and the live URL says so.

## 8. Live URL

CLAUDE.md requires one. It should be honest and small, and the plan does not spend time on it:
1. Now: the existing Vercel app, changed to a status page that states "No AMD run has taken place" and shows no answers.
2. After the real run: the same page lists the committed traces, reading backend, GPU string and timings from the trace files. Nothing is hard-coded as "AMD".
3. It is not part of the evaluator contract, and it does not run the model. App code in the tree was not re-inspected in this run.

## 9. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Alex's AMD account is late | No GPU run, no valid entry | Everything else is ready first so the first GPU session is used for proof only; the plan states when this would be a loss |
| Match 4 closes before the first GPU run (date UNVERIFIED) | No prize | Alex asks on Discord (he must; the agent may not post) |
| Real Match 4 spec differs from the pattern | Adapter rework; possibly more | Adapter isolation; section 6 |
| Pages are images or need JavaScript | Extraction misses values | Non-goal until the spec says so |
| Daemon does not survive between harness calls | Model load per question, likely over 30 s | Client falls back to refusing before the deadline rather than overrunning; measure on the notebook |
| py3.14 wheels missing | Build fails | Found on the notebook first; fallback is pinning to what the base ships |
| Hidden set is dominated by cases every rival handles | Tie at the ceiling | Stated in section 0 |
| Notebook quota (3 h per day) | Few iterations | Scripted runs; measure only what is needed |

## 10. What would change this decision

- Match 4 spec read: if it forbids a resident process, requires a server, or requires a different base, rework the adapter, and if that is not enough, reconsider the track.
- Match 4 closes, or its close is confirmed too soon for Alex's GPU access: stop and wait for the Match 5 or 6 spec, then reuse the chassis.
- Match 5 or 6 publishes a spec with a harness that Alex can reach first: reconsider, only after reading it.
- A rival entry is shown to pass the real evaluator and ours cannot differ: this plan would be expected to lose on a tie-break, and the honest recommendation would be to submit for the floor and not spend more.
