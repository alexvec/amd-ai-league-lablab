> **DRAFT, pending the AMD run.** No real model and no AMD GPU has run this code. Slides 5 and 8 cannot be filled until a run is committed. Do not present this as a finished entry.

# Slides: Trailmark (AMD AI League, Match 4)

Outline for export to PDF, one `---` per slide. No metrics, users, testimonials, prices or market sizes exist, so none appear. Any cover image is Alex's choice.

---

## 1. Trailmark

One value from a set of web pages. Only the pages that prove it. Nothing if they do not.

- AMD AI League, Match 4: Intelligent Web Information Retrieval [docs/competition.md]
- Repo: https://github.com/alexvec/amd-ai-league-lablab (MIT)
- Status page: https://amd-ai-league-lablab.vercel.app
- Working name. Not submitted. No evaluator has seen it.

---

## 2. The job

- The user is an evaluator process that execs a CLI and reads one JSON file per question [docs/prds/match-4.md].
- An answer is a value, not a sentence. Citations are graded as an exact set. A refusal is an empty answer and empty citations [Match 3 kit; UNVERIFIED for Match 4].
- A human analyst who must defend a single fact is a persona hypothesis, not a measured user.

---

## 3. How it works

1. `--index`: walk the pages, catching failures per page. Build a lexical index. Start one resident model service on a unix socket.
2. Each question is a new short-lived process that never imports torch and talks to the service.
3. The model suggests terms, picks links by index, and proposes values with verbatim spans.
4. Plain code decides: the span must be on the stored page, the value must be in the span.

---

## 4. What plain code decides

- **Supersession:** pages that disagree are settled by withdrawn markers, then revision labels, then dates. Otherwise it refuses.
- **Necessity:** pages are removed one at a time. A page that only repeats the value goes. Both pages of a chain through an identifier stay.
- **Refusal:** any rejected candidate set, timeout or dead service gives exactly `{"answer":"","citations":[],"confidence":0.0}`.
- The model never writes the citation list. Page text is untrusted data inside a per-call random fence.

---

## 5. The AMD part, and where it stands

- Design: an open-weight model, Qwen3-4B-Instruct-2507, on an AMD GPU through ROCm, in the mandated base image, with weights in the image [docs/prds/match-4.md].
- Today: **it has not run.** The model code, weights download and GPU script have never been executed.
- The block: the hackathon notebook says the email is not registered.
- After a run, from `amd/evidence/<run>/summary.json` only: GPU [ ], model [ ], peak VRAM [ ], time per question [ ].

---

## 6. What was actually tested

- On a Mac, with a scripted stub in place of the model, on a fixture site invented for the purpose. The stub only tests plumbing.
- In a small non-ROCm image on Python 3.14 with `--network none --cap-drop DAC_OVERRIDE`, with the same stub.
- This says nothing about accuracy, speed, memory or the hidden set. Those have no figures.

---

## 7. Who pays (unvalidated hypothesis)

- For the Match: the prize pool [docs/competition.md section 3].
- Commercially, analysts, procurement or compliance staff who need auditable single-fact lookups are a hypothesis only. No customer, pilot or price exists.

---

## 8. What is next

1. Get the email on the notebook list.
2. The first real GPU run, committed unedited, misses included.
3. Build the image on the mandated base, on a machine with room, and run the docker self-check.
4. Read the real Match 4 spec and change the config to match.

---

## 9. Links and disclosure

- Repo: https://github.com/alexvec/amd-ai-league-lablab
- Status page: https://amd-ai-league-lablab.vercel.app
- Built with substantial help from Anthropic's Claude via Claude Code, under Alex Veciana Belmonte's direction. No third-party agent framework. Claude takes no part in answering questions at run time.
