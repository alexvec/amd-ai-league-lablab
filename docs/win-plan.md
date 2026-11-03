# Win plan: AMD AI League (lablab.ai)

Written 2026-11-03. Rule book: docs/competition.md (section numbers below refer to it). Nothing here is registered, submitted, or deployed. Anything not sourced in the rule book is marked UNVERIFIED or as a TARGET/ESTIMATE.

## 1. Decision

Chosen track: **Match 4, Intelligent Web Information Retrieval.** PRD: docs/prds/match-4.md.

Recommendation in one line: build one deep product, a web-navigating retrieval agent whose answers carry machine-checked evidence, served from an open-weight model on ROCm, and ship a live URL on day one. Do not split effort across Matches 4, 5 and 6.

## 2. Facts that drive the choice (all from docs/competition.md)

| Fact | Source section | Consequence |
|---|---|---|
| Match 4 is "Live now"; start/end and timezone not stated | 2 | Only prize-eligible Match today, but the clock is unknown. Ship fast. |
| Match 5 is "Coming soon, Nov", no dates | 2 | Cannot submit for a prize yet. Brief may only appear when it opens. |
| Match 6 is "Coming soon, Nov 10-14"; game unknown | 2, 5 | Opens in 7 days; the spec (game, harness, token accounting) does not exist yet. Building now is a guess. |
| "Prizes apply only to submissions made while the Match is live" | 3 | A submission that misses the window earns nothing. |
| Matches 4-6 have no separate pages; format, scoring and AI-tool rules UNVERIFIED | 1, 5, 6 | Plan for both artifact shapes (container and public repo plus URL). Do not claim either is official. |
| Points: M4 1,800, M5 2,100, M6 2,400 | 5, 7 | Points favor later Matches slightly, but points do not pay unless Alex also reaches League podium (needs 5 courses). |
| Match prizes: 1st $500 cash, 2nd $250 GPU credits, top 50 valid submissions $100 GPU credits | 3 | "Valid submission" in the top 50 is the realistic floor. Validity (working artifact) matters more than polish. |
| Solo, individual only | 4 | One person's time. Scope must be small. |
| Notebooks: 3 h/day, idle time counts, ~25 GB | 9 | GPU time is scarce. Plan GPU sessions as short, scripted runs. |
| Submissions must be original, open source, MIT-compatible by default | 8 | MIT licence, public repo, disclose AI tools used. |

## 3. Judging criteria and scoring method

Published criteria: only the generic lablab set (RULES, section 6): Presentation, Business value, Application of technology, Originality, each 1-5. Whether these apply to Matches 4-6 is UNVERIFIED; the League page says "Graded by AMD's evaluator", which suggests automated scoring of an artifact on correctness (inference only, section 5). Match 4 formula is UNVERIFIED.

So every idea is scored two ways:

- A. Evaluator fit: would the artifact plausibly score well under automated grading of "navigate, understand request, retrieve the specific information" (the only sourced description)? Dimensions: correctness of retrieved answer, source URLs returned, robustness, cost/latency.
- B. Generic lablab criteria, 1-5 each.

All numbers below are my planning estimates for comparing options, not measurements.

| Option | Open now? | Spec known? | A. Evaluator fit | Presentation | Business value | Application of technology | Originality | Generic total /20 | Day-one URL feasible? | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| M4: evidence-checked web retrieval agent on ROCm | Yes | Description only | High if answer plus sources are returned; the verifier directly reduces unsupported answers | 4 | 3 | 4 | 3 | 14 | Yes (verifier and replay mode need no GPU) | **Chosen** |
| M5: multi-agent test-gated code repair | No | Description only | Unknown: harness, repos, language unknown | 4 | 4 | 4 | 3 | 15 | Possible, but nothing to test against | Loses on timing and spec risk |
| M6: token-frugal unknown-game agent | No (Nov 10-14) | No: game unknown | Unknown: cannot build or test without the game | 3 | 2 | 4 | 4 | 13 | No: nothing to demo without the game | Loses on spec risk |

M5 scores higher on the generic total, but the generic total does not overcome the fact that it cannot be submitted for a prize today and its harness is unknown. The M4 score rests on the verifier being a real contribution, not on a better model.

## 4. Why Match 4 wins

1. It is the only Match where a prize-eligible submission can be made now. The other two require waiting for an opening that has no stated time (M5) or a game that does not exist yet (M6).
2. Its sourced task description is concrete enough to build to: natural-language request in, specific information out, from website navigation. The one non-official participant entry (section 5) suggests input is a question plus optional start URL and output is an answer with source URLs. UNVERIFIED, so the API is kept flexible (see PRD).
3. The product has one deep idea that is neither a prompt wrapper nor a label: every claim in an answer must carry a verbatim quote from a page the agent actually fetched, and a deterministic checker rejects claims whose quote is not in the stored page text. That is testable offline, without a GPU, so it works on day one.
4. The AMD tech is the inference engine for the agent loop (open-weight model on ROCm), and the artifact is a container on a ROCm base. That is deep use of one partner technology.

## 5. Why the others lose

- **Match 5 (code repair).** "Coming soon, Nov", no date. The brief may be released only at opening, so any code built now risks missing its repo format, language, test harness, and scoring. A PRD is written (docs/prds/match-5.md) so Alex can switch fast, but no application code should be written for it until the brief exists.
- **Match 6 (unknown game).** Opens Nov 10 and closes Nov 14 (year/timezone not stated). The brief says the game is unknown to the agent, and the harness is unknown to us. A generic "token-frugal agent" built blind could not be demonstrated on real input, and its demo would be fabricated. Its PRD (docs/prds/match-6.md) is a contingency only.
- Entering all three shallowly is rejected: a wrapper in three Matches loses to one deep entry, and it halves the time for the part that decides validity (a working artifact).

## 6. Risks, stated openly

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Match 4 closes before the entry is ready. Close date unknown. | Unknown / total loss of the prize | Ship a submittable container and live URL within the first build day. Alex asks in the lablab Discord for the close time now (NEEDS.md, last row). Cut features, never the artifact. |
| Official evaluator contract (endpoint schema, time limits, base image tag) differs from my assumption | Likely partly / could invalidate the artifact | Keep the agent core behind one thin adapter; the HTTP schema is a config file. Re-read the live page before submitting. Do not claim evaluator acceptance. |
| Live URL cannot run on AMD hardware | Likely | See section 7. Label the backend truthfully. |
| Notebook quota (3 h/day) too small for tuning | Medium | Scripted short runs; model chosen to fit; no fine-tuning planned. |
| Alex's AMD account not ready | Blocking for AMD runs | Day-one build proceeds without it using the labeled fallback. |
| The checker is judged a gimmick if answers are poor | Medium | The checker's value is measured by the acceptance tests on real pages, and any quality numbers reported must be produced by an actual run. No numbers are written before they exist. |
| Rival M4 entries already exist | Certain (at least one found) | Differentiate on verification, not on having a browser agent. |

## 7. What can really run on AMD, and the fallback

Truthful split:

| Component | Where it can run | Needs from Alex |
|---|---|---|
| Fetch, extract, link-follow, quote-verifier, tests, UI | Anywhere, no GPU | Nothing |
| Open-weight model served by an OpenAI-compatible server (for example vLLM with ROCm) | AMD GPU in notebooks.amd.com/hackathon (3 h/day) during Alex's session; possibly AMD Developer Cloud ($100 credits for eligible new members, eligibility UNVERIFIED) | AMD Developer Program SSO account |
| Container on a ROCm base, weights included (the shape the participant entry describes, UNVERIFIED as official) | Built and tested in the notebook if Docker/container tooling is available there (UNVERIFIED), otherwise built elsewhere and only smoke-tested on AMD | AMD account; container registry (optional, UNVERIFIED) |
| Permanent public live URL | The notebook is a time-limited Jupyter session; I found no source saying it exposes a stable public port. A permanent AMD-GPU-backed endpoint would need a persistent AMD cloud instance (UNVERIFIED availability). Treat "always-on AMD inference behind the URL" as NOT available by default. | Possibly AMD Developer Cloud access |

Fallback so a URL exists before Alex supplies anything:

1. The web app is deployed (plan: Vercel, per the builder rules) with the verifier, a "replay" mode and a pluggable inference backend.
2. Replay mode serves previously recorded agent traces and stored page snapshots, so the UI is demonstrable without any model. It is always labelled "Replay of a recorded run" with the recording date and the backend that produced it.
3. If Alex provides an optional third-party hosted open-weight API key (unverified as allowed for the Match), that backend can power live runs, and the UI shows that provider by name.
4. When Alex runs the agent on the AMD notebook, the trace records `backend: rocm-vllm` and the GPU name reported by the machine. Only traces actually produced that way may be labelled AMD. The UI and README must read the backend from the trace, never hard-code "AMD".
5. Never write "runs on AMD" for the live URL unless the endpoint behind it is on AMD hardware at the time. State the real deployment in the README.

## 8. Deployment tooling (planning note only)

I have no shell in this run, so I did not inspect the machine. Facts from the repo instructions: the builder agent is told to deploy to Vercel if the CLI is already authenticated, to create a public GitHub repo and push, and to record missing credentials in NEEDS.md. Whether `vercel`, `gh` and Docker are installed and authenticated on this machine is UNVERIFIED; the builder checks first. Vercel serves the app and verifier only. It cannot host a ROCm GPU container, which is why section 7 separates the two.

## 9. Day-by-day plan (targets, not promises)

- Build day 1 (target): repo, MIT licence, README, tests, verifier, fetch/extract tools, replay mode, deployed URL responding. Container Dockerfile drafted.
- Build day 2 (target): agent loop against an OpenAI-compatible backend; AMD notebook run once Alex's account exists; recorded traces committed; container built.
- Then: presentation assets, verification, and Alex submits via submit.sh when the Match is confirmed still live.
- Re-check docs/competition.md sources before submitting; confirm the Match 4 close time via Discord (Alex).

## 10. What would change this decision

- Match 4's close time is announced as earlier than the entry can be ready: stop M4 and wait for M5 or M6, or accept it is lost.
- The Match 4 evaluator contract rules out the verifier approach, or requires a specific model or endpoint that cannot be met.
- Match 5's brief is published with a concrete harness and a window that outlasts M4: reconsider, using docs/prds/match-5.md. Not before the brief is read.
- Match 6's game and harness are published and fit a small, testable agent: possible second entry after M4 ships. Whether one person may enter several Matches is not stated outright (prize stacking between League and Match prizes is stated, section 3); UNVERIFIED.
- Alex cannot obtain AMD access: the entry still ships with the labeled fallback, but its "application of technology" claim weakens and the track choice should be re-examined.
