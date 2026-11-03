# Slides: Trailmark (AMD AI League, Match 4)

Outline for export to PDF, one `---` per slide. Every number comes from a repo file, named in brackets. No metrics, users, testimonials, prices or market sizes exist, so none appear. The cover image, if any, is Alex's choice.

---

## 1. Trailmark

Ask for one fact from the web. See the quote behind every claim. Know a program checked the quote is on the page.

- AMD AI League, Match 4: Intelligent Web Information Retrieval [docs/competition.md]
- Live: https://amd-ai-league-lablab.vercel.app
- Repo: https://github.com/alexvec/amd-ai-league-lablab (MIT)
- Working name. Not submitted. No evaluator has accepted it [README.md]

---

## 2. The problem

- A web answer you cannot trace is an answer you cannot defend.
- The need: one specific fact, with the place it came from [docs/prds/match-4.md, job to be done].
- The persona (researcher or analyst who must cite a source) is a hypothesis, not a measured user [docs/prds/match-4.md].

---

## 3. How it works

1. Find pages: a given URL, a URL in the question, or a Wikimedia search of English Wikipedia.
2. Fetch through a guarded fetcher, extract text, store a snapshot with its SHA-256, follow links.
3. A backend drafts claims, each with a quote and a source URL. Backends cannot mark anything verified.
4. A plain-code verifier checks each quote against the stored page text. Exact or whitespace-normalised only. No case folding, no fuzzy matching. Numbers in a claim must be in the quote.
5. The answer is built only from claims that passed.

[README.md, How it works]

---

## 4. The product on real input

- Real question, real page: "What does the key word MUST mean?" on the RFC 2119 page [docs/demo-path.md].
- Committed trace, 2026-11-03: 3 claims, all verified, each with its position in the stored page [traces/extractive-no-llm-what-does-the-key-word-must-mean-379b7acb7090.json].
- Failure case: a quote altered on purpose comes back "Unverified, removed from the answer" [docs/demo-path.md, step 3].
- A refused URL (cloud metadata address) fetches nothing [docs/demo-path.md, step 4].

---

## 5. What the check proves, and what it does not

- Proves: the quote is on the page that was fetched in this run.
- Does not prove: that the quote answers the question, or that the page is true [README.md].
- Seen in the committed MUST trace: the first claim answers the question; the other two verified claims are real quotes that are only partly relevant (a boilerplate sentence, and the definition of SHOULD).
- Seen by Alex in a production test, not in a committed trace: "What does MUST NOT mean?" returned verified quotes about MUST and SHOULD.
- The extractive backend picks sentences by keywords. A language model is meant to do better at relevance. That is untested.

---

## 6. Honest status

| Part | State | Source |
|---|---|---|
| Live URL backend | `extractive-no-llm`, no language model | README.md |
| LLM backend | Tested against a stub only. No real model has answered it | README.md |
| AMD runs | 0 (`recorded_amd_runs`). No AMD run has taken place | README.md, amd/README.md |
| Container | Never built | README.md |
| Offline tests | 184 passed on the build machine | README.md |
| Recorded traces | 2, both from the extractive backend | README.md |
| Evaluator acceptance | Unknown | README.md |

No accuracy, speed or usage figure exists.

---

## 7. Why the partner technology matters (and where it stands)

- Design: an open-weight model served on ROCm does the planning, link choice and claim writing. The verifier is plain code and is not AMD work [docs/prds/match-4.md].
- Today: that part has not run. The label `rocm-*` can only be earned by a trace from a machine whose ROCm tool reports a GPU, and no setting can force it [README.md, amd/README.md].
- First AMD run: a short notebook job with one question and a small model [amd/README.md].
- Slide for after the run, only once filled from the committed trace: GPU [ ], model [ ], measured values [ ].

---

## 8. Who pays (unvalidated hypothesis)

- Hypothesis: teams that need auditable web research, such as analysts, compliance and procurement staff, and journalists, might pay for answers with checkable evidence [docs/prds/match-4.md].
- No customers, pilots or prices exist. Nothing here is validated.

---

## 9. What is next

1. The first real run on an AMD GPU in the notebook, committed as a trace as it is [amd/README.md].
2. Run the LLM backend against a real model and see whether it follows the JSON protocol [amd/README.md].
3. Build the container on a ROCm base and check `/health` [NEEDS.md].
4. Confirm the Match 4 submission format and close time [docs/competition.md section 5].
5. Compare the model's answers with the keyword backend on the same questions, then report only what the committed traces show.

---

## 10. Links and disclosure

- Live: https://amd-ai-league-lablab.vercel.app
- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Built with substantial help from Anthropic's Claude via Claude Code, under Alex Veciana Belmonte's direction. No third-party agent framework [README.md, AI tool disclosure].
