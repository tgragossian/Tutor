# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22. Work continues in the `milestone-b`
worktree (`.claude/worktrees/milestone-b`). `main` and `milestone-b` are identical at the end of
the day; the host still runs 78bbcd6 (the newer commits add only unserved drafts and checks).

## Live site (https://tutor.thomasgragossian.dev)

- Milestone B practice loop deployed from `main` 78bbcd6: accounts, practice with MathLive,
  history with "Clear history", 6 reviewed problems. `/readyz` ready; migrations 0001–0002.
- First `/readyz` after `up -d` returns 502 for 30–60 s while the SymPy worker starts: normal.
- Idle memory on the 1 GB host: app+worker 135 MiB, Caddy 17 MiB, ~386 MiB available.
- Deploy = the [runbook](docs/ops/runbook.md) "Update to the latest `main`" block (Thomas runs
  it in Lightsail browser SSH). `migrate` must show `Exited (0)`. Never `compose down -v`.

## Done today (2026-10-21)

- Tasks 10–14 built, Codex review B-A1–B-A5 fixed (4eba48f), container storage (e6da0e5).
- Thomas's UI feedback: function names auto-insert parentheses, solid closing ")", session
  ends instead of repeating ("Next features under construction…"), US spelling (6ba982e);
  history shows answered sessions only, Start reuses an untouched session, required OpenStax
  attribution line (5e1d684); Clear history, migration 0002 (78bbcd6). Rulings A19–A21.
- Thomas decided assistant transcription of OpenStax is fine (recorded in the source manifest).
- Task 15: 16 drafts (`needs_review`) + content-check endpoint rule (Thomas: a finite end is
  closed iff the answer is defined there). 235 dropped for 217 (verifier timeout, follow-up).

## Resume here

1. **Deploy the 22 problems** (2026-10-22: Thomas approved all 16 drafts; task 15 done,
   merged to `main`). After Thomas runs the runbook update, `/readyz` should show `"servable":22`.
   Selection/practice tests now pin the original 6 via `tests/support/content.py`.
2. **Rest of task 16:** `tools/load/submit_burst.py` (16 concurrent submits) for memory sizing
   on the host; move the e2e job onto the image; `docs/verifier/` supported-expressions page;
   uvicorn `--no-access-log` (requests are logged twice); record host numbers in `docs/ops/host.md`.
3. Then one fresh whole-branch review (executing-plans skill) before calling milestone B done.
4. Record actual hours with Thomas ([hours](docs/ops/hours.md)); 30-hour checkpoint pending.
5. [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md): verifier is
   slow on wrong answers to nested trig (`sin(cos 7x)`); `content_check` lacks a hard deadline.

## Working notes for Claude

- On this Windows/OneDrive checkout: `UV_LINK_MODE=copy` for `uv add`; Python edit scripts need
  `encoding="utf-8"` and raw strings for LaTeX (backslashes were lost several times today);
  prefer the Edit tool for LaTeX. Playwright must click MathLive with `{delay: 80}`.
- The ledger is `.superpowers/sdd/README/progress.md` (git-ignored); rulings A1–A21 are tracked in
  [06-app-track-rulings](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md).

## Evidence and navigation

- [Documentation tree](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)
  owns task completion and outstanding gates.
- [Verification evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  separates browser/CI evidence from the [review validation](docs/reviews/2026-10-21-milestone-b/03-validation.md).
- [Reviewed verifier result](evals/verifier/results/README.md): FA 0/50 (95% upper bound 7.1%),
  FR 0/49, coverage 49/49, agreement 136/136; no internal errors. This is a dev set.
- [File map](docs/superpowers/plans/portfolio-mvp/milestone-b/01-file-map.md),
  [debugging tree](docs/ops/debugging/README.md), [security](docs/ops/security.md),
  [API contracts](contracts/README.md).
- [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md)
  distinguish release gates from deferred cleanup.

## Working rules

- Every Markdown file stays at most 100 lines, split by responsibility with a parent link.
- Preserve [original references](docs/handoff/README.md) and [dated reviews](docs/reviews/README.md).
- Never relax false-accept or containment gates; describe the verifier as proof-based/SymPy.
- No assistant co-author trailers; assistance is acknowledged in [README](README.md#acknowledgments).
- Actual hours belong in the [hours log](docs/ops/hours.md); do not infer them from agent runtime.
- RAG hints, operations/final evaluation and the [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md)
  follow the deployed practice loop.
