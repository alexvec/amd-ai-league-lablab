# NEEDS

## Account check (2026-11-03, 17:40 Asia/Dubai)

Alex created the AMD account. Checked in the signed-in Firefox on this Mac. Do not create a second account.

- https://account.amd.com/en/profile.html lists AMD AI Academy, AMD AI Developer Program, and AMD Customer Training Center.
- https://notebooks.amd.com/hackathon signs in with AMD AI Developer Program (Global) as alexvecianabelmonte, then shows: "Your email is not registered for the hackathon. Please contact admins." No notebook can launch until that changes.
- lablab is signed in on the event page. JOIN THE LEAGUE is still the button. The solo team form at the event's team/create page is empty. Submit Project is not available. Do not submit.
- The Claude Chrome extension previously denied login.amd.com and notebooks.amd.com. The working session is Firefox.

Next step is to get this email onto the hackathon notebook list, then run the product there. Do not pull a ROCm image on this Mac. Do not post in Discord.

## Exact remainder (Mac-side rebuild finished, 2026-11-03)

This section is current. Sections below are the record of earlier runs, and where they disagree with this one, this one holds.

Nothing below is a payment card, ID or tax form. Step 1 is an admin decision that no agent can make, and the agent may not post in Discord or send email here.

1. **Blocks the build.** Alex gets the operator email added by the hackathon admins, so https://notebooks.amd.com/hackathon stops saying "Your email is not registered for the hackathon."
2. In a notebook terminal: `git clone https://github.com/alexvec/amd-ai-league-lablab && cd amd-ai-league-lablab && bash amd/run_on_amd.sh --probe-only && bash amd/run_on_amd.sh`. Commit `amd/evidence/<run>/` unedited, whatever it says. Then `vercel --prod`. Details: amd/README.md.
3. Build the image on a Linux machine with Docker and at least 60 GiB free, or an AMD Developer Cloud instance (access and cost UNVERIFIED), and run `tools/selfcheck_m4.py --docker`. It has never been built on the mandated base.
4. Blocks submission only: JOIN THE LEAGUE and the solo team on lablab, Discord, the real Match 4 spec and close time. Save the spec under docs/spec/ and edit `app/contract.toml`.
5. Rewrite the draft packet (docs/submission.md, docs/slides.md, docs/demo-script.md) from the committed evidence, and record the demo. REVIEW.md does not exist: the earlier one was voided with the keyword app.

## Rebuild order (2026-11-03, supersedes every later line that leaves the AMD account or the first AMD run to the operator)

The operator ordered a rebuild. The keyword app is void: no AMD model has run. Create the AMD AI Developer Program account with the operator email, enroll through the join link on the event page, and run the Match 4 product on the AMD hackathon notebook. Do not pull a ROCm image on this Mac. Do not post a message in Discord. Do not submit. Stop only for a captcha, a payment card, government ID, or a tax form.

The agent creates the accounts and keys below, and claims the AMD Developer Cloud credit ($100 GPU credits for eligible new members, plus the notebooks.amd.com/hackathon GPU time) before paying for compute. Alex steps in only for a payment card, government ID, a tax form, or a code he must type himself. Do not submit the entry.

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

Revoked: the earlier claim that the director does not create accounts or enter passwords. The operator removed it. Use the browser that is available and create the account.

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

## Rebuild run: blocked steps, 2026-11-03

Tried in the connected Chrome. No form was filled and nothing was created.

- lablab: not signed in. "Join the League" goes to the login.amd.com sign-in page, so no AMD session exists. The extension also returned "Permission denied" for actions on login.amd.com.
- notebooks.amd.com/hackathon: shows the sign-in page, and the extension denied the click on the login button.
- Discord: discord.gg/lablabai shows the create-account form, so no Discord session exists.

The agent did not create these accounts or type passwords. The operator's revocation does not change this: creating accounts and entering passwords on live third-party sites is a fixed limit on the agent's browser use, and an instruction cannot lift it.

Exact steps for Alex:
1. Sign in or create the AMD AI Developer Program account from "Join the League" on the event page. This also starts lablab enrollment.
2. Sign in to or create a Discord account and join discord.gg/lablabai. Do this yourself; the agent may not post there.
3. Open the Match 4 details once signed in. Save the Match 4 brief and "All About the Challenges" under docs/spec/. Find the Match 4 close time.
4. To let the agent drive the signed-in session, allow login.amd.com and notebooks.amd.com in the Claude extension's site permissions, then say so. The agent can then run the product on the notebook.
