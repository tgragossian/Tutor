[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 385–399. Review findings remain unresolved.

## 9. Testing

| Layer | Content |
|---|---|
| Unit | translator allowlist and rejections, each checker, pre-checks, mastery formula, each policy (seeded RNG) |
| Property-based (Hypothesis) | random MathJSON trees → the translator returns SymPy or a clean rejection; it never raises otherwise |
| Content | all YAML validates; every expected answer parses; every seed problem's expected answer is judged `correct` against itself |
| Integration | FastAPI TestClient + temp SQLite: register → diagnostic → report → practice with warm-up → reveal → recap; authorization and 409 cases |
| Verifier evaluation | `run_verifier_eval.py` in CI; build fails on any false accept |
| End-to-end | one Playwright smoke test: log in, start practice, type into MathLive, see a verdict |

Tooling: Python 3.12, `uv`, `ruff`, `mypy` (strict on `verify`, `mastery`, `recommend`, `content`), `pytest`.

---

<!-- End preserved source. -->
