# Demo path

The walk a person records. `scripts/walk_demo.py` runs the same steps and fails if the app does not do what is written here.

```bash
.venv/bin/python scripts/walk_demo.py --url https://amd-ai-league-lablab.vercel.app
# To record it: --headed --slow-mo 600 --video-dir demo-recordings
```

Fetches in steps 2 and 3 are live, so the page can change. Alex picks the questions used in the recorded demo from live pages at record time. The questions below are the script's defaults, not an evaluation set.

## What the demo is and is not

The live URL runs `extractive-no-llm`, a keyword-based backend with no language model. Nothing on this path uses a model or AMD hardware, and the narration must not suggest it does. The header shows the backend from `/health`, and it says no AMD run has taken place until a trace recorded on an AMD GPU is committed.

Once the AMD run exists, re-record with that trace in step 5, so the trace panel shows the model and GPU string from the machine.

## Steps

1. **Open the page.** The header shows the active backend, the model, the deployment and the AMD statement. All of it is read from `/health`.
2. **Ask a real question on a real page.** Click "Fill in an example", which fills "What does the key word MUST mean?" and `https://www.rfc-editor.org/rfc/rfc2119.html`, then click "Find it". Show the answer, each claim marked Verified, and the quote highlighted in the stored page. Scroll the Trace panel to show the robots check, the fetch with its SHA-256, the sentence selection and the verify steps.
3. **Show the failure case.** Tick "Failure demo", then click "Find it" again. One quote is deliberately altered before the verifier sees it. It comes back marked "Unverified, removed from the answer", labelled "Altered by the demo switch", and its text is not in the answer.
4. **Show a refused URL.** Replace the start URL with `http://169.254.169.254/latest/meta-data/` and click "Find it". The app refuses it and fetches nothing.
5. **Replay a recorded run.** Choose a run in the replay list and click Replay. The notice says it is a replay, with the recording date and the backend that produced it. No page is fetched, and the verifier re-checks the stored snapshot.
