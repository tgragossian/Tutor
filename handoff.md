# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-19 (task 8 done; task 9 drafted; Codex asked to sync milestone B docs).

## Current state

- Independent review of Claude's handoff, specification and all 20 tasks is complete.
- Milestone A skeleton is live at https://tutor.thomasgragossian.dev; milestone B practice work is underway.
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

All seven are addressed by the approved [portfolio-core spec](docs/superpowers/specs/2026-10-13-portfolio-core/README.md)
and assigned to milestone B: bounds (1) → tasks 2–3; precision, choice dispatch (2) → tasks 2, 5;
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
(worktree `.claude/worktrees/milestone-b`).

**Codex reviewed through 2f95748 on 2026-10-15; all three findings fixed 2026-10-18.**
B-C1 8346d2a, B-C2 b7f23ad, task 7 pool fixes + B-C3 10611a5; each reviewed clean.
Tasks 1–8 complete (task 8: 55744b8, 4138181). Task 9: 131 draft dev cases in a115846,
unreviewed; draft gate B fails on FR (2 of 52) and coverage (82.7%), FA 0 of 54.
[Execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md) is stale past task 7.

**Codex, next:** update every Markdown file in the milestone B plan tree per the
[doc-sync request](docs/superpowers/plans/portfolio-mvp/milestone-b/04-codex-doc-sync.md).
**Then Thomas:** review the task 9 labels in `evals/verifier/human/REVIEW.md`.

## Codex review notes for Claude

- [Code review](docs/reviews/2026-10-15-milestone-b/01-code-review.md): B-C1/P1, inward-rounded
  absolute-value enclosure produces a false refutation; B-C2/P1, computed logarithms bypass
  exponent bounds; B-C3/P2, partial pool construction fails to clean up earlier workers.
- [Reproductions](docs/reviews/2026-10-15-milestone-b/02-reproductions.md): focused probes and expected current output.
- Verified: 474 tests pass, seven known pool tests fail, one Linux-only test skips.
  Compiler tests (14), content check (6 problems), ruff and mypy pass; Docker not verified.
- [Review index and earlier plan risks](docs/reviews/2026-10-15-milestone-b/README.md): ruling dispositions and schedule checkpoint.
Human gates remain: dev-case labels (task 9), new problems (task 15), host deploy (task 16).

Rulings R7–R21 made during execution (including Thomas's R14–R16) are recorded in
[execution rulings](docs/superpowers/plans/portfolio-mvp/milestone-b/02-execution-rulings.md);
they override the plan files where they differ.

## Reference documents

- [Original handoff](docs/handoff/README.md).
- [Original design](docs/superpowers/specs/2026-10-13-core-practice-loop-design.md).
- [Original tasks](docs/superpowers/plans/2026-10-13-core-practice-loop.md).
- Reference wording is preserved except the explicitly replaced commit-attribution rule;
  the preservation manifest records that amendment.
