# Calculus Tutor

A portfolio project by Thomas Gragossian: build and evaluate a deployed Calculus I tutor.[^ai]

Live: <https://tutor.thomasgragossian.dev>

Status (2026-10-22): **milestone B: practice loop live.** Accounts, practice on three
derivative topics (22 reviewed problems) with MathLive input and a proof-based SymPy grader,
and history. Whole-branch review findings are fixed; the hours log remains.
Host sizing is deferred to C under a recorded exception. See the
[handoff](handoff.md), [what the verifier accepts](docs/verifier/supported.md),
[verifier results](evals/verifier/results/dev-b.md) and [API contracts](contracts/README.md).
Option B remains selected: ship the core early, then restore features in a gated queue.

Hosting is on one AWS instance ([host record](docs/ops/host.md)); the AWS Budget alert emails
at $10/month and is not a spending cap.

Start with the [handoff](handoff.md), [reviews](docs/reviews/README.md),
and [active implementation sequence](docs/superpowers/plans/portfolio-mvp/README.md).

## Documentation tree

```text
README.md → handoff.md → docs/README.md
  docs/decisions/                  Accepted decisions and precedence
  docs/ops/                       Local setup, host record, runbook, security
    debugging/                    Symptom → owner → focused check
  docs/verifier/                  What the grader accepts; results
  docs/superpowers/plans/portfolio-mvp/
    milestone-b/                  Status, rulings, evidence and file map
      tasks/                      One implementation task per file
      r22-r23/, r24/              Verifier changes and debugging
  docs/superpowers/specs/          Approved contracts and preserved design
  docs/handoff/, docs/reviews/     Historical background and dated reviews
  contracts/, content/, evals/     API examples, authoring and evaluation
```

Every Markdown file must remain at most 100 lines. Split by responsibility and link
from a parent index; keep results and proposed work visibly distinct.

The [reviewed release result](evals/verifier/results/dev-b.json) reports FA 0/50 (95% upper
bound 7.1%), FR 0/49, coverage 49/49 and agreement 136/136. These are reviewed dev-set results.
[CI and result evidence](evals/verifier/results/README.md): Python, Node and container smoke
passed for tasks 1–9. [App-track evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
records the app-track checks separately.
RAG hints and final evaluation follow later.

## Development

Install [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`), then:

```bash
uv sync
uv run pytest
uv run python tools/check_docs.py
```

For a migrated local app and browser smoke, use [development setup](docs/ops/development.md).

## Acknowledgments

[^ai]: Planning and technical review were assisted by Anthropic Claude and OpenAI Codex.
