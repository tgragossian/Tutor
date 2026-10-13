# Calculus Tutor

A portfolio project by Thomas Gragossian: build and evaluate a deployed Calculus I tutor.[^ai]

Status: design review completed on 2026-10-13. No application code or deployment exists.
Option B is selected: ship the core early, then restore features in a gated queue.
No experiments have run.

Start with the [handoff](handoff.md), [review](docs/reviews/2026-10-13/README.md),
and [active implementation sequence](docs/superpowers/plans/portfolio-mvp/README.md).

## Documentation tree

```text
handoff.md                         Current status and next action
README.md                          Project entry point
docs/
  README.md                        Documentation map
  handoff/                         Preserved Claude background
  reviews/2026-10-13/               Findings, structure, evaluation
  superpowers/
    specs/                         Original design index and modules
    plans/
      core-practice-loop/          Original task modules
      portfolio-mvp/              Proposed smaller delivery sequence
```

Every Markdown file must remain at most 100 lines. Split by responsibility and link
from a parent index; keep results and proposed work visibly distinct.

The working stack proposal is FastAPI, Jinja/HTMX, MathLive, SymPy, SQLite and Docker.
RAG, evaluation and a public deployment are the intended portfolio deliverables.
Installation instructions and measured results will be added when software exists.

## Acknowledgments

[^ai]: Planning and technical review were assisted by Anthropic Claude and OpenAI Codex.
