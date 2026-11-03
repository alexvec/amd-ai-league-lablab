# PRD: Match 6, token-frugal agent for an unknown game (working name: Lean Scout)

Status: NOT CHOSEN. Contingency only. Cannot be built meaningfully until the game and harness are published. Sources: docs/competition.md.

## Track rule as sourced
Match 6, "Can Your AI Master the Unknown?", "Coming soon, Nov 10-14" (year and timezone not stated) (MAIN): build an agent that learns an unfamiliar strategy game, navigates hidden maps, and completes missions while minimizing compute and inference tokens. 2,400 points. Game, interface, scoring formula, token accounting: UNVERIFIED. Not prize-eligible until live.

## User
The evaluator running the game harness; beyond that, a developer who needs agents that act under a fixed token budget. (Hypothesis.)

## Job to be done
"Complete the mission in an unfamiliar environment while spending as few model tokens as possible."

## Concept
An agent that spends tokens only when needed: a compact state summary, a persistent map and rules memory written by code, a cheap rule-based policy for actions it has already learned, and a model call only on novel situations. A hard per-episode token budget and a per-call token log. Original work.

## Partner capability doing the work
Open-weight model on ROCm and AMD GPUs for the novel-situation calls; token counts measured from the server. The caching, memory and policy layer is plain code.

## Minimum scope that ships on day one
Because the game is unknown, only the harness-independent parts can be built early: a state-memory module, a token-budget meter, a generic environment adapter interface, a simulated toy environment for tests (clearly labelled as a test fixture, not the real game), and a deployed page that explains and replays a trace from that toy environment. Real scope is set when the brief is published (target: within hours of publication).

## Explicit non-goals
Training on the real game; exploiting harness bugs; claims about performance on the real game before a run exists; hard-coded knowledge of a guessed game.

## AMD engine and how inference runs
ROCm container and local model server on AMD notebook runs; live URL shows replay with the backend label from the trace.

## Artifact shape
Unknown. Likely a container that connects to the harness (inference only). Adapter interface isolates the unknown protocol.

## Demo must show, on real input
The real Match game, once published: mission completion or failure, per-step token log, and total tokens against the budget. A toy-environment demo may not be presented as the real game.

## Who pays
Hypothesis: teams running many agent calls where token cost dominates. No customer exists; none may be claimed.

## What would make a judge call it a wrapper
Every step calls the model; "token saving" is only a shorter prompt; no measured token log; AMD only in the README.

## Acceptance tests
Budget meter stops calls at the cap; memory module reproduces a learned rule without a model call (toy environment); adapter contract test; token log totals equal server-reported totals; schema test once the harness is known.

## Credentials it depends on
AMD SSO account (Alex); Match 6 enrollment and submission: Alex.

## Why it lost
Spec does not exist yet, opens Nov 10, window is five days, and a blind build cannot be shown on real input (docs/win-plan.md section 5).
