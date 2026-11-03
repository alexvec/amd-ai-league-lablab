# PRD: Match 5, test-gated multi-agent code repair (working name: Redline)

Status: NOT CHOSEN. Contingency only. Do not build until the Match 5 brief is published. Sources: docs/competition.md.

## Track rule as sourced
Match 5, "AI-Powered Code Repository Repair", "Coming soon, Nov", exact dates not stated (MAIN): build a multi-agent system that analyzes code, detects defects, and proposes fixes with minimal human intervention. 2,100 points. Submission format, languages, repos, harness, scoring: UNVERIFIED. Not prize-eligible until live.

## User
A maintainer with a repository whose tests fail or whose bugs are reported, who wants a reviewable patch rather than a chat reply. (Persona hypothesis.)

## Job to be done
"Given this repo and a failing test or bug report, give me a patch that makes the test pass and show me the evidence."

## Concept
Three roles: localizer (finds suspect files and functions), fixer (proposes a diff), verifier (applies the diff in a sandbox copy and runs the tests). A patch is only emitted if the previously failing test passes and no previously passing test fails. Otherwise the loop retries within a fixed budget and reports failure honestly. Original work.

## Partner capability doing the work
Open-weight code-capable model on ROCm and AMD GPUs serving all three roles through an OpenAI-compatible server (UNVERIFIED on the notebook). The sandbox test runner is plain code.

## Minimum scope that ships on day one
Repo, MIT licence, tests; a CLI and web page that take a repo path or zip and a test command; sandboxed apply-and-test; replay mode; deployed URL with backend label; pluggable backend. Language support limited to what the brief names once published (Python as a placeholder assumption only).

## Explicit non-goals
Network-enabled sandbox runs on untrusted code from the public URL (the live URL must not execute arbitrary uploaded code on a shared host); languages beyond the brief; auto-merge; fine-tuning; claims of fix rates without committed runs.

## AMD engine and how inference runs
Same shape as docs/prds/match-4.md: ROCm container with local model server on AMD notebook runs; labeled hosted or replay backend for the live URL. Backend is always read from the trace.

## Artifact shape
Unknown. Likely a container taking a repo and emitting a patch (inference only). Plus public repo and URL for the generic form. Fix the schema once the brief exists.

## Demo must show, on real input
A real failing repo (Alex-chosen or a public one with a licence permitting it), the failing test output, the three agents' steps, the patch, the passing test output, and one failure where no patch is emitted.

## Who pays
Hypothesis: engineering teams with test-failure triage backlog. No customer exists; none may be claimed.

## What would make a judge call it a wrapper
One prompt asking a model to "fix the bug" with no test verification; the sandbox not actually running tests; AMD only in the README.

## Acceptance tests
Sandbox applies a good diff and reports pass; rejects a diff that breaks another test; refuses patches outside the repo root; budget cap stops the loop; schema test against the official format (once known); live URL does not execute uploaded code.

## Credentials it depends on
AMD SSO account (Alex) for AMD runs; nothing else to build. Match 5 enrollment and submission: Alex.

## Why it lost
No dates, no brief, harness unknown, not prize-eligible now (docs/win-plan.md section 5).
