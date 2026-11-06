# Task 3: Runs and report (Thomas)

[Plan](README.md) · Spec: all

Paid steps are Thomas's: he sets `MATHTUTOR_ANTHROPIC_API_KEY` in his own terminal (never in
chat or git), checks credit, and runs each arm with a hard cap.

- [ ] **Step 1: Credit (free):** `uv run python -m mathtutor.help.eval.run --spent`.
- [ ] **Step 2: Four runs on the same commit** (Sonnet, dev, each `--max-usd 2`):
  ```
  uv run python -m mathtutor.help.eval.run --split dev --models claude-sonnet-5-5 --arm plain --max-usd 2
  uv run python -m mathtutor.help.eval.run --split dev --models claude-sonnet-5-5 --arm pasted --max-usd 2
  uv run python -m mathtutor.help.eval.run --split dev --models claude-sonnet-5-5 --no-retrieval --max-usd 2
  uv run python -m mathtutor.help.eval.run --split dev --models claude-sonnet-5-5 --max-usd 2
  ```
- [ ] **Step 3: Audit** each run's `audit.csv` with rubric v2 (random 20% plus flagged),
  then `--recompute` each run directory.
- [ ] **Step 4: Comparison:** generate the `compare` table into
  `evals/help/results/<date>-baseline-ladder.md` with the caveats from the design.
- [ ] **Step 5: README:** add the table under Evaluation as "Is any of this needed?", with
  the caveats and the who-pays note. Commit `docs: baseline ladder results`.
