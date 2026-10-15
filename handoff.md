# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-15 (milestone A skeleton live).

## Current state

- Independent review of Claude's handoff, specification and all 20 tasks is complete.
- Milestone A skeleton is live at https://tutor.thomasgragossian.dev; no grading or experiments yet.
- The original design/tasks remain references; use the decisions below when they conflict.
- Keep every Markdown file at most 100 lines, organized under linked parent indexes.

## Accepted direction: option B

Use Codex's delivery order and retain the broader features in a gated queue.
First: deployed skeleton -> full practice loop on three topics -> RAG hints ->
operations and final evaluation. Build meaningful tests/evaluations throughout.
Then: diagnostic -> exam conditions and recap -> all 15 topics ->
extraction pipeline -> LoRA. Start each expansion only after the preceding stage works.
Features are sequenced, not dropped; the full queue is not an eight-week promise.

The first practice release targets basic derivative rules, trig derivatives and
chain rule, with 20–30 reviewed problems, accounts, attempt history and one practice mode.
Keep FastAPI/Jinja/HTMX, MathLive, SQLite and Docker.
The 160-hour budget is a planning target for the initial shipped core, not the full roadmap.
See the [active delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
and [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md).

## Verifier refinements from the Claude/Codex review

- Store a real mathematical domain for each problem.
- Default: equality on that domain, ignoring provably removable holes.
- A strict per-problem override is available when domain behavior is being assessed.
- Preserve original restrictions; do not ignore poles, branch differences or intervals
  where the student expression is undefined. Unknown domain checks must abstain.
- Keep implicit differentiation for polynomial curves with supported rational answers.
  Replace sampled acceptance with exact reduction of F_x + F_y * submitted_derivative.
- A zero reduced numerator certifies the relation only after denominator and regularity
  checks; F_y must be nonzero on the assessed curve region. Cover every included branch.
- General/transcendental implicit curves and unproved domain cases remain unsupported.
- Implement implicit-topic support at the all-15-topics stage; define its contract early.
- Numeric sample agreement alone never proves exact equality.

The [decision record](docs/decisions/0001-delivery-verifier-attribution.md) defines these
defaults and safeguards. It supersedes the review's blanket implicit-deferral suggestion.

## 2026-10-13 review findings: where they now live

All seven are answered by the approved [portfolio-core spec](docs/superpowers/specs/2026-10-13-portfolio-core/README.md)
and implemented in milestone B: bounds (1) → tasks 2–3; precision, choice dispatch (2) → tasks 2, 5;
presentations and idempotent submits (3) → task 12; MathLive pins and captures (4) → milestone A
and task 14; human cases and family splits (5) → tasks 8–9; shared services, memory, latency (7)
→ tasks 12–13, 16. Finding 6 (MathDial) applies to milestone C.
Details: [review](docs/reviews/2026-10-13/README.md).

## Attribution decision

Do not add assistant coauthor trailers to commits. Acknowledge Claude and OpenAI Codex
in the [README footnote](README.md#acknowledgments). Existing commits are not rewritten.

## Claude update (2026-10-15)

Milestone A is merged to `main`, CI green, live at https://tutor.thomasgragossian.dev
(host runs `main`; details in `docs/ops/host.md`). Thomas approved the milestone B plan and
chose subagent-driven execution. Work runs on branch `milestone-b`
(worktree `.claude/worktrees/milestone-b`); task 1 is in progress.

## Review request for Codex: milestone B plan

Please review the [milestone B plan](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md)
(16 task files, constraints, file map) against the [spec](docs/superpowers/specs/2026-10-13-portfolio-core/README.md)
and decision 0001. Write findings to `docs/reviews/2026-10-15-milestone-b/README.md`
(≤ 100 lines per file, severity + file:line + fix); do not edit the plan directly, since
execution has started. Focus on:
1. Verifier soundness (tasks 3–5): any path where a wrong answer could be graded correct.
2. Submit protocol and concurrency (tasks 7, 12): races, orphaned reservations, SQLite locking.
3. Process boundary: rulings R1 (offline content check) and R8 below keep SymPy out of the web process.
4. Whether 80 dev cases (task 9) and the gates in task 8 are a meaningful measurement.
5. Scope vs budget: ~43 h estimated against a 30 h timebox.

Rulings made at execution start (not yet in the plan files):
- R7: `.env.example` leaves `SITE_ADDRESS` empty; `smoke.sh` exports `SITE_ADDRESS=localhost` for the compose check.
- R8: the pool resolves its default `check_fn` inside the worker by import path, so the web
  process never imports `verify.check` (spec 05's `= check` default would pull in SymPy).
- R9: task 6 moves every test fixture bundle to `schema_version` 2.

## Reference documents

- [Original handoff](docs/handoff/README.md).
- [Original design](docs/superpowers/specs/2026-10-13-core-practice-loop-design.md).
- [Original tasks](docs/superpowers/plans/2026-10-13-core-practice-loop.md).
- Reference wording is preserved except the explicitly replaced commit-attribution rule;
  the preservation manifest records that amendment.
