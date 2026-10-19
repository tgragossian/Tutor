# Task 15: 20–30 problems and browser smoke

[Milestone B plan](../README.md) · [Spec 01](../../../../specs/2026-10-13-portfolio-core/01-content-and-domains.md) · [Milestone A task 5](../../milestone-a/tasks/05-seed-problems.md)

Start after task 9's human review/gates and tasks 13–14; the draft dev set does not satisfy this dependency.

**Status (2026-10-19):** not started; paths below are planned outputs.
Dependencies checked against the [file map](../01-file-map.md) and [rulings](../02-execution-rulings.md).

**Files:**
- Create: 14–24 new `content/problems/*.yaml`; `tools/e2e/smoke.mjs`
- Modify: `content/compiled/problems.json`, `tests/unit/test_seed_content.py`, `tools/package.json` (script `e2e`), `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the compiler and `content_check` (task 6); the running app (tasks 13–14); the eval runner (task 8).
- Produces: the milestone B problem bundle and a browser smoke that CI runs against the container.

**Content rules (same as milestone A task 5, plus):**
- Total 20–30 problems, at least 6 per topic, at least 2 `numeric` and 2 `choice`, at least 3 expression problems with a domain other than ℝ, at least 5 with `misconceptions`.
- Transcribed problems use real OpenStax exercises from §3.3, §3.5, §3.6 with the exercise number; prefer odd numbers (answer key).
- Each draft's `review.notes` holds the worked check; `status: needs_review` until Thomas reviews.
- `content_check` must pass on every draft before review.

- [ ] **Step 1: Update tests.** `test_seed_content.py`: counts become `20 ≤ total ≤ 30`, `≥ 6` per topic, the kind and domain minimums above; every problem `human_verified` (strict xfail until the gate, as in milestone A).
- [ ] **Step 2: Draft the problems**, compile, run `uv run python -m mathtutor.verify.content_check` and `uv run pytest tests/unit/test_seed_content.py -q`. Expected: everything passes except the human-verified test.
- [ ] **Step 3: Human gate (Thomas).** For each problem: statement matches the book, answer correct, domain right, distractors genuinely wrong. Set `human_verified`, `tg`, date. Remove the xfail marker.
- [ ] **Step 4: Write `tools/e2e/smoke.mjs`** (Playwright, Chromium), taking `BASE_URL`:
  1. Collect console messages and fail on any containing `Content Security Policy` or `Refused to`.
  2. Register a random user; pick "The chain rule"; start.
  3. On the first problem, type a known-wrong answer from a misconception → "Not quite — try again (2 left)".
  4. Type the correct answer → "Correct"; click Next → a different statement appears.
  5. Reload the page → the same item and the same tries count (no reset).
  6. Go to `/` → the session appears in history with 1 correct.
  7. The `math-field` accepted typed keys (its value is non-empty after typing).
  - Answers come from a small map keyed by `source.section` + `source.exercise` (the public item has no problem id). If the current item is not in the map, click Skip until one is, so the script does not depend on content order.
- [ ] **Step 5:** Run locally: start the app, `BASE_URL=http://127.0.0.1:8000 npm run e2e --prefix tools`. Expected: PASS.
- [ ] **Step 6: CI.** A new `e2e` job (needs `python`, `node`): `uv sync`, `alembic upgrade head` on a temp SQLite file, start uvicorn in the background, `npx playwright install --with-deps chromium`, run the script against `http://127.0.0.1:8000`. Task 16 moves it onto the container. Re-run the dev-set gate to confirm the new content changed no results.
- [ ] **Step 7: Commit** `feat: 20–30 reviewed problems; browser smoke in CI` (body lists the new ids).
