# Demo script: Trailmark (about 4:30)

For Alex to record himself against https://amd-ai-league-lablab.vercel.app. Target 4:30 and stay under 5:00 (the generic form recommends under 5 minutes; UNVERIFIED for Match 4). Steps follow docs/demo-path.md. Nothing is uploaded or posted by anyone but Alex.

## Rules for the recording

- The live URL runs `extractive-no-llm`, a keyword backend with no language model. Never call it an LLM, an AI model, or AMD.
- A replay is a replay. Say "replay" when it is on screen.
- Do not show or say any GPU output unless it comes from a committed trace of a real AMD run.
- Fetches are live, so the pages can change. Do a dry run first. If a result differs from what is written here, narrate what is on screen.
- Alex chooses any further questions at record time and tests them first. This script only uses the questions whose outcomes are in docs/demo-path.md or a committed trace.
- Optional record settings from docs/demo-path.md: `--headed --slow-mo 600 --video-dir demo-recordings` with scripts/walk_demo.py. A screen recording by hand also works.

## Script

### 0:00 to 0:30. Problem (on slide 2 or the top of the live page)

Say: "If you need one fact from the web and you have to defend it, an answer without a source is not enough. Trailmark goes to a page, answers, and shows the exact quote behind every claim. Then a plain program checks that each quote is really on the page it fetched."

### 0:30 to 1:00. Be upfront about the backend (step 1: open the page)

Click: open the live URL. Point at the header: backend, model, deployment, AMD statement.
Say: "The header is read from the server's health report. This deployment runs a keyword-based backend with no language model, on Vercel. It does not run on AMD hardware, and no AMD run has taken place yet. I will come back to that."

### 1:00 to 2:00. The product on real input (step 2)

Click: "Fill in an example" (fills "What does the key word MUST mean?" and the RFC 2119 URL), then "Find it".
Show: the answer, each claim marked Verified, the quote highlighted in the stored page. Scroll the Trace panel: robots check, fetch with SHA-256, sentence selection, verify steps.
Say: "This is a real fetch of a real page. The page is stored with its hash. Every claim carries a quote, and the quote is highlighted at its position in the stored text."

### 2:00 to 2:40. What the check does and does not prove (same result)

Show: the claims returned. In the committed trace for this question there are three: the MUST definition, a sentence about the boilerplate phrase, and the definition of SHOULD. Confirm that is what you see.
Say: "Look at what 'verified' means. The first claim answers the question. The other two are real quotes that are on the page, but they are only partly relevant. The check proves a quote is on the page. It does not prove the quote answers the question. This backend picks sentences by keywords, so it can return a real sentence that does not answer. That is the limit, and I would rather show it than hide it."

Optional, only if Alex has tested it and it did not come out well on the live site: show the "What does MUST NOT mean?" question on the same page, which in a production test returned verified quotes about MUST and SHOULD. Do not script an outcome you have not seen on the day.

### 2:40 to 3:10. The failure case (step 3)

Click: tick "Failure demo", then "Find it" again.
Show: one quote comes back "Unverified, removed from the answer", labelled "Altered by the demo switch", and its text is not in the answer.
Say: "I altered one quote on purpose before the verifier saw it. The verifier rejected it and the answer was built without it. Backends cannot mark their own claims verified."

### 3:10 to 3:30. A refused URL (step 4)

Click: replace the start URL with `http://169.254.169.254/latest/meta-data/`, then "Find it".
Show: the refusal.
Say: "This endpoint fetches addresses from strangers, so it refuses private and metadata addresses and fetches nothing."

### 3:30 to 3:50. Replay (step 5)

Click: choose a run in the replay list, then Replay.
Show: the notice that this is a replay, with its recording date and the backend that produced it.
Say: "This is a replay of a recorded run, not a live fetch. No page is fetched. The verifier re-checks the stored snapshot. Both recorded runs here are from the keyword backend."

### 3:50 to 4:10. Why the partner technology matters (choose ONE version)

Version A, true today. Use this one unless the AMD run is done and committed.
Say: "The design is for an open-weight model, served on AMD GPUs through ROCm, to plan the navigation, choose links and write the claims, with this verifier checking its output. That part is written and tested against a stub only. It has not run on a real model, and it has not run on AMD hardware. So today the partner technology is the plan, not a result."

Version B. RECORD ONLY AFTER the notebook run, with the new trace committed and deployed. No fake output: show only what is on screen from the real run.
Click: choose the new AMD trace in the replay list, then Replay. Open the trace panel.
Say (fill from the trace, leave out anything it does not show): "This is a replay of a run recorded on [GPU string shown in the trace], with [model shown in the trace], backend [backend shown in the trace]. It answered [N] question(s), with [verified claims out of total] verified. It took [measured time]. This is one run, not an evaluation."
Then say: "The live site itself is [still not / now] on AMD hardware, as its header says."

### 4:10 to 4:30. Who pays, and what is next

Say: "Who pays is a hypothesis I have not validated: teams that need auditable web research, such as analysts, compliance staff and journalists, might pay for answers with checkable evidence. There are no customers or prices. Next: the first real run on an AMD GPU, the LLM backend against a real model, and the container on a ROCm base. The code is MIT licensed, and was written with substantial help from Claude through Claude Code."

## Before recording, Alex checks

1. The live URL responds and the header matches the words in the script.
2. The Step 2 result on the day matches the three claims described. If not, change the narration.
3. For version B only: the new trace is committed, the live site is redeployed, and `gpu_vram_after_run` in the trace shows memory in use.
4. The video is MP4 or MOV, under 300 MB (generic limits, UNVERIFIED for Match 4).
