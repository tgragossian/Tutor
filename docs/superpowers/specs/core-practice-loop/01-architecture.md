[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 42–79. Review findings remain unresolved.

## 2. Architecture

A single Python package. Components are pure where possible and are connected only in `web`.

```
src/mathtutor/
  content/     # pydantic schemas + loader/validator for topics, problems, formula/concept items
  verify/      # MathJSON→SymPy translator, per-answer-type checkers, sandboxed runner
  mastery/     # per-topic recall & application scores from attempt history (pure)
  recommend/   # selection policies: diagnostic, practice, recap, textbook-order baseline (pure)
  store/       # SQLAlchemy models, Alembic migrations, repository functions
  web/         # FastAPI app: JSON API, auth, Jinja/HTMX pages, static assets
content/
  topics.yaml
  problems/*.yaml
  formulas/*.yaml
eval/
  verifier_cases.yaml
  run_verifier_eval.py
tests/
```

**Boundary rules**
- `verify` has no database or web imports. Its input is an answer spec plus MathJSON; its output is a `Verdict`.
- `mastery` and `recommend` are pure functions of (content, attempt history, session plan). Randomness comes in through an injected `random.Random`.
- `web` contains no math or selection logic.
- Content lives in version-controlled YAML and is loaded and validated at startup. The database holds only user-generated data.

**Submit-answer flow**
1. The browser posts MathJSON + LaTeX.
2. `web` checks that the problem is the session's current item.
3. The sandboxed verifier is called (3 s timeout).
4. The attempt is stored.
5. Mastery is recomputed.
6. The response carries the verdict and, in practice mode, the next item with its reason.

---

<!-- End preserved source. -->
