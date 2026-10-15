# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-13 after selecting option B.

## Current state

- Independent review of Claude's handoff, specification and all 20 tasks is complete.
- Documentation only: no application implementation, deployment or experiments yet.
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

## Remaining findings Claude must address

1. Bound input bytes, tree shape, numeric sizes, expression construction and worker queue.
2. Resolve decimal precision, +C, multiple-choice dispatch and semantic answer payloads.
3. Use durable item-presentation IDs, atomic/idempotent submissions and explicit retry,
   reveal and advance states. Refresh must not reset timing; uncertain grading is not wrong.
4. Pin patched MathLive/Compute Engine versions and capture actual browser output.
   The reviewed MathLive version removed getValue('math-json'); do not copy that old call.
5. Add human-reviewed adversarial cases and problem-family evaluation splits.
   Generated SymPy cases alone are not independent validation; gate useful coverage too.
6. MathDial dialogue labels do not establish calculus correctness or hint-leakage quality.
7. Share application services between HTML/JSON routes; test restore/rollback and measure
   host memory, queue-inclusive latency and LLM usage. Budget alerts are not spending caps.

Details: [review](docs/reviews/2026-10-13/README.md),
[verifier](docs/reviews/2026-10-13/verifier.md),
[contracts](docs/reviews/2026-10-13/contracts.md),
[evaluation](docs/reviews/2026-10-13/evaluation.md), and
[structure](docs/reviews/2026-10-13/structure.md).

## Attribution decision

Do not add assistant coauthor trailers to commits. Acknowledge Claude and OpenAI Codex
in the [README footnote](README.md#acknowledgments). Existing commits are not rewritten.

## Claude update (2026-10-15)

Spec approved; milestone A runs on branch `milestone-a` (worktree `.claude/worktrees/milestone-a`).
Tasks 1–6 done: ADR 0002 accepted, six seed problems human-verified by Thomas, app factory
with `/healthz`, `/readyz` and placeholder page (85 tests pass). Task 7 (Dockerfile, Caddy,
compose, CI smoke job) passes in CI. Remote: https://github.com/tgragossian/Tutor (main, milestone-a).
Progress ledger: `.superpowers/sdd/README/progress.md` (git-ignored; rulings recorded there).

## Next action for Claude

Follow option B; do not reopen the A/B/C choice.
Task 8 (Lightsail deploy) next; it needs Thomas's AWS account, domain and DNS.
No co-author trailers.

## Reference documents

- [Original handoff](docs/handoff/README.md).
- [Original design](docs/superpowers/specs/2026-10-13-core-practice-loop-design.md).
- [Original tasks](docs/superpowers/plans/2026-10-13-core-practice-loop.md).
- Reference wording is preserved except the explicitly replaced commit-attribution rule;
  the preservation manifest records that amendment.
