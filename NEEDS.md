# NEEDS

The agent creates the accounts and keys below. Alex steps in only for a payment card, government ID, a tax form, or a code he must type himself. Do not submit the entry.

Checked on 2026-11-03 before this rule: no agent had signed in or joined. The agent now does the rows that are not a payment card or the final submission.

| Item | Blocks | Unlocks |
|---|---|---|
| AMD AI Developer Program account (SSO), via the join link on https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge | Blocking the build | notebooks.amd.com/hackathon GPU notebooks (3 h/day, ~25 GB), $100 AMD GPU credits for eligible new members, Match enrollment |
| lablab.ai account enrolled in the challenge (one account only, individual) | Blocking submission only | Submitting to a live Match; points and prizes |
| lablab Discord membership (discord.gg/lablabai) | Blocking submission only (required for Match participation per MAIN) | Match eligibility |
| Notebooks event password, only if not using AMD SSO | Optional (unverified need) | Alternate sign-in at notebooks.amd.com/hackathon |
| Fireworks or other third-party API key | Optional; MAIN says Fireworks credits are not required. Whether allowed in Matches 4-6 is UNVERIFIED | Hosted inference alternative |
| GitHub public repo (Alex's account) | Blocking submission only if the generic lablab form applies (UNVERIFIED for Matches 4-6) | Repo link field |
| Docker or container registry access | Optional / UNVERIFIED. A participant entry mentions a Docker image on a ROCm base; not confirmed officially | Possible artifact submission |
| At least 5 completed Academy courses | Optional for building; required only to claim League podium prize | League podium eligibility (Dec 1) |
| Confirmation of Match 4 close date and Match 5/6 submission mechanics (from the lablab Discord or Match announcements) | Blocking the build plan (cannot pick a prize-eligible Match without it) | Knowing which Match is feasible |

No paid plan is required per MAIN (no own AMD hardware, Developer Cloud credits, or Fireworks credits needed). Nothing on opened pages mentions a paid tier. Joining Discord, registering, and submitting must be done by Alex.

## Director's reading, 2026-11-03 (stage 3)

The build continues. No missing item makes the product impossible to run: fetching, extraction, the quote verifier, the UI and the non-LLM backend need no credentials. The "Blocking" labels above change as follows.

- AMD account: blocks every AMD run and any claim of running on AMD. It does not block the build. Until Alex completes a run on the notebook, the entry has no AMD inference. Partner technology is meant to be the engine of the product, so this is the largest gap in the entry, and Alex must close it before submitting.
- Match 4 close date: blocks knowing whether a submission is prize-eligible. It does not block the build. Alex should confirm it on Discord, since no agent may post there.

Checked on this machine: `gh` is logged in as alexvec, `vercel` is logged in, and Docker is running (the build run section below supersedes this for Docker). No model API key is set in the environment, so the live URL has no LLM until Alex supplies one or runs the AMD notebook.

Nothing has been registered, joined, or submitted.

## Remaining steps for Alex (updated on the resumed run, 2026-11-03)

Alex asked for the AMD account, lablab enrollment and Discord join to be done by the agent. None of them were done. No account page was opened and no form was filled.

Why:
- The Claude in Chrome extension is not connected (`tabs_context_mcp` returned "not connected", and `list_connected_browsers` returned an empty list, while Chrome was running). So no signed-in session was reachable.
- Separately, the director does not create accounts or enter passwords on live third-party sites, even when asked. That is a fixed limit on its browser use, so connecting the extension will not change it for the account creation in step 1.

Steps, in order:
1. Create the AMD AI Developer Program account with the operator email in operator.json, using the join link on https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge. The same SSO link enrolls you on lablab. Whether a separate lablab account is also needed is UNVERIFIED.
2. Join the lablab Discord at discord.gg/lablabai. It is required for Match participation. Do not skip it.
3. Ask in Discord for the Match 4 close time and the submission format. The director may not post there.
4. Run the first real AMD inference: sign in at https://notebooks.amd.com/hackathon, launch a notebook, and follow amd/README.md. Until this is done the entry has no AMD inference.

Once steps 1 and 2 exist and the extension is connected, the agent can do enrollment clicks in the signed-in session if you ask. Steps 1 to 3 do not block the build. Step 4 blocks any claim that the entry runs on AMD.

## Build run, 2026-11-03

Repo and live URL exist; see STATE.md. This run created no accounts and signed in nowhere new. No model API key was available, so the live URL runs the non-LLM backend.

Exact remainder, all for Alex:
1. Steps 1 to 3 above.
2. The first AMD run, per amd/README.md: `bash amd/run_on_amd.sh --probe-only`, then `bash amd/run_on_amd.sh`. Until it is done, the partner technology does no work in the entry: no AMD run has taken place and no real model has answered this code.
3. Build the container on a ROCm base somewhere with disk to spare, then check `/health` on it. It has never been built on a ROCm base. This Mac had 17 GiB free and the Docker daemon returned EOF.
