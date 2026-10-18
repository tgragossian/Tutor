# Milestone B reviews — 2026-10-15

[Reviews](../README.md) · [Plan](../../superpowers/plans/portfolio-mvp/milestone-b/README.md) · [Spec](../../superpowers/specs/2026-10-13-portfolio-core/README.md)

## Read next

- [Code review at 2f95748](01-code-review.md): three new code defects, known pool failures, verification and fix order.
- [Reproductions](02-reproductions.md): small probes for B-C1 through B-C3.
- [Execution rulings](../../superpowers/plans/portfolio-mvp/milestone-b/02-execution-rulings.md): R10–R13 resolve plan findings 1–4; implementation is still pending.
- Plan findings 5–6 are implemented: logarithm-base constraints and worker-only default imports.
  Code finding B-C2 concerns magnitude bounds, a separate issue from logarithm domains.
- Plan finding 7 remains a schedule checkpoint; retain the timebox and human gates.

## Earlier plan review

Plan review while execution was underway. These are risks in the written tasks, not
claims that the implementation has these bugs. Check code and tests before applying fixes.
Do not weaken proof, resource, or evaluation gates to recover the 30-hour timebox.

## Findings for Claude

1. **P1 — Generated gate cannot pass as written.** [Task 8:18,39,42](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/08-eval-runner.md) uses `--gate B` with `min_cases: 80` on the generated set. Four seed problems have expression answers; six listed mutations per problem yield at most 24 cases. Give generated cases a separate gate for observed false accepts and require 80 only for the human dev set. Test each CLI mode against its intended denominator.
2. **P1 — Unsupported false accepts are outside the release gate.** [Task 8:27,37–38](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/08-eval-runner.md) records agreement for `unsupported` labels, but the FA denominator includes only `incorrect` labels and no gate rejects an unsupported case graded `correct`. Count that outcome explicitly as a false accept or add a zero-accept gate for unsupported cases, with a failing test.
3. **P1 — Racing writes need an atomic winner.** [Task 12:23–25,44–50](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/12-practice-service.md) says two submissions can reserve the same revision and exactly one wins in transaction B, but only describes a read, insert and state update. A concurrent SQLite transaction can raise a lock/snapshot error or overwrite a stale revision. Use a conditional `UPDATE ... WHERE revision = :expected AND state = 'active'`, check one affected row, and map a lost race to 409. Test overlap on a real SQLite file.
4. **P1 — Duplicate replay during grading has no response.** [Spec 06:38–45](../../superpowers/specs/2026-10-13-portfolio-core/06-session-state.md) replays stored results; [Task 12:23–25,43](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/12-practice-service.md) regrades reservations older than 10 seconds. Neither defines what a duplicate gets while the first grading is still in flight. Return a bounded retryable response, avoid a second grade before the stale threshold, and test a duplicate arriving during a slow check.
5. **P1 — Explicit logarithm bases need domain constraints.** [Task 3:48,52](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/03-translator.md) supports `Log(a,b)` but lists only argument positivity. The base must be positive and unequal to 1; retain those restrictions from the raw tree before any simplification. Add `Log(x,1)`, zero and negative base cases to domain/content tests, abstaining when coverage cannot be proved.
6. **P2 — The pool signature contradicts the process ruling.** [Task 7:13–18](../../superpowers/plans/portfolio-mvp/milestone-b/tasks/07-pool.md) still uses `check_fn=check`, which can import SymPy in the web process. The current handoff's R8 resolves the default inside the worker. Implement R8 and keep `test_web_process_has_no_sympy` as a gate.
7. **P2 — The schedule needs an explicit replan point.** [Plan:48–66](../../superpowers/plans/portfolio-mvp/milestone-b/README.md) estimates 43.5 hours against 30 and suggests cutting scope at a task boundary, but the exit gate still requires the full practice loop and evaluation. Record actual hours and agree a revised date or contingency use before dropping any exit evidence.

The plan's human review gates for dev labels and new problems remain necessary.
