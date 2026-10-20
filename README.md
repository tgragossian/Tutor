# Calculus Tutor

A portfolio project by Thomas Gragossian: build and evaluate a deployed Calculus I tutor.[^ai]

Live: <https://tutor.thomasgragossian.dev>

Status: the milestone A skeleton is live, and milestone B's answer verifier and its evaluation
(tasks 1–9) are merged to `main`. Six human-reviewed problems load; health and readiness probes,
HTTPS and CI (tests, reviewed verifier gate, container smoke test) run. The live host still serves
the skeleton: no public grading or accounts yet. Option B is selected: ship the core early, then
restore features in a gated queue. The practice loop, accounts and UI (tasks 10–16) come next.

Hosting is on one AWS instance ([host record](docs/ops/host.md)); the AWS Budget alert emails
at $10/month and is not a spending cap.

Start with the [handoff](handoff.md), [reviews](docs/reviews/README.md),
and [active implementation sequence](docs/superpowers/plans/portfolio-mvp/README.md).

## Documentation tree

```text
handoff.md                         Current status and next action
README.md                          Project entry point
docs/
  README.md                        Documentation map
  decisions/                       Accepted decisions and precedence
  handoff/                         Preserved Claude background
  reviews/                         Historical findings; current 2026-10-19 review
  superpowers/
    specs/                         Approved portfolio-core spec; original design
    plans/
      core-practice-loop/          Original task modules (reference)
      portfolio-mvp/              Active delivery sequence and milestone B tasks
```

Every Markdown file must remain at most 100 lines. Split by responsibility and link
from a parent index; keep results and proposed work visibly distinct.

The bounded SymPy verifier and evaluation (milestone B tasks 1–9) are on `main`.
The [reviewed release result](evals/verifier/results/dev-b.json) reports FA 0/50 (95% upper
bound 7.1%), FR 0/49, coverage 49/49 and agreement 136/136. These are reviewed dev-set results.
[CI and result evidence](evals/verifier/results/README.md): Python, Node and container smoke
pass, including the reviewed dev gate. The practice loop, accounts and UI remain tasks 10–16.
RAG hints and final evaluation follow later.

## Development

Install [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`), then:

```bash
uv sync
uv run pytest
uv run python tools/check_docs.py
```

## Acknowledgments

[^ai]: Planning and technical review were assisted by Anthropic Claude and OpenAI Codex.
