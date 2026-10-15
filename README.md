# Calculus Tutor

A portfolio project by Thomas Gragossian: build and evaluate a deployed Calculus I tutor.[^ai]

Live: <https://tutor.thomasgragossian.dev>

Status: milestone A skeleton. Six human-reviewed problems load; health and readiness probes,
HTTPS and CI (tests, container smoke test) work. No grading, accounts or experiments yet.
Option B is selected: ship the core early, then restore features in a gated queue.
Tasks 1–7 are done. Task 8's host and budget records and the final branch review remain.

Hosting is on one AWS instance ([host record](docs/ops/host.md)); the AWS Budget alert emails
at $10/month and is not a spending cap.

Start with the [handoff](handoff.md), [review](docs/reviews/2026-10-13/README.md),
and [active implementation sequence](docs/superpowers/plans/portfolio-mvp/README.md).

## Documentation tree

```text
handoff.md                         Current status and next action
README.md                          Project entry point
docs/
  README.md                        Documentation map
  decisions/                       Accepted decisions and precedence
  handoff/                         Preserved Claude background
  reviews/2026-10-13/              Findings, structure, evaluation
  superpowers/
    specs/                         Approved portfolio-core spec; original design
    plans/
      core-practice-loop/          Original task modules (reference)
      portfolio-mvp/              Active delivery sequence and milestone A tasks
```

Every Markdown file must remain at most 100 lines. Split by responsibility and link
from a parent index; keep results and proposed work visibly distinct.

The skeleton uses FastAPI, Jinja, MathLive content tooling and Docker. The practice
loop, SymPy verification, RAG hints and measured evaluation follow in later milestones.

## Development

Install [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`), then:

```bash
uv sync
uv run pytest
uv run python tools/check_docs.py
```

## Acknowledgments

[^ai]: Planning and technical review were assisted by Anthropic Claude and OpenAI Codex.
