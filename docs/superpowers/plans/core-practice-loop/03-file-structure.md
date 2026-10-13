[Index](../2026-10-13-core-practice-loop.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 64–102. Review findings remain unresolved.

## File Structure

```
pyproject.toml, uv.lock, .python-version, .gitignore, README.md
.github/workflows/ci.yml, deploy.yml
docs/decisions/0001-mathlive-mathjson.md          # Task 2 result
tools/mathlive_capture/index.html, capture.py      # Task 2
src/mathtutor/
  __init__.py
  domain.py               # AttemptRecord, SessionPlan, shared Literals (Task 11)
  verify/
    types.py              # AnswerSpec, Verdict, FormatIssue, DNE (Task 3)
    translate.py          # MathJSON→SymPy allowlist (Task 3)
    expected.py           # parse_expected for trusted answers (Task 4)
    equivalence.py        # symbolic + numeric comparison (Task 4)
    checkers.py           # pre-checks + per-type check() (Task 5)
    implicit.py           # implicit_derivative (Task 6)
    sandbox.py            # VerifierPool (Task 7)
  content/
    models.py, loader.py  # Task 8
  mastery/scores.py       # Task 11
  recommend/
    base.py, budget.py, diagnostic.py, recap.py, baseline.py   # Task 13
    practice.py           # Task 14
  store/
    models.py, db.py, repo.py      # Task 12
  web/
    settings.py, app.py, auth.py, security.py, errors.py, logging.py  # Task 15
    api.py, flow.py       # Task 16
    pages.py, templates/*.html, static/{app.js, app.css, vendor/}     # Task 17
migrations/               # Alembic (Task 12)
content/topics.yaml, problems/*.yaml, formulas/*.yaml   # Tasks 8–9
eval/verifier_cases.yaml, generated_cases.yaml, generate_cases.py, run_verifier_eval.py, sympy_to_mathjson.py  # Task 10
tests/ (mirrors src), tests/fixtures/mathjson/captured.json, tests/e2e/
deploy/Dockerfile, docker-compose.yml, Caddyfile, backup.sh   # Task 19
```

---

<!-- End preserved source. -->
