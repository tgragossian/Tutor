# Verifier

[Documentation](../README.md)

The verifier grades typed calculus answers: an allowlist translator turns the browser's
MathJSON into SymPy, then a proof-based checker returns `correct`, `incorrect` or
`unable_to_verify`. It runs in separate worker processes, never in the web process.

- [What it accepts](supported.md): notation, size limits, how it decides, when it abstains,
  known limitations and the "resource containment, not a sandbox" wording.
- [Milestone B results](../../evals/verifier/results/dev-b.md): reviewed dev-set metrics by
  kind, reason and method, with latency.
- [Evaluation guide](../../evals/verifier/README.md): case format, gates and commands.
- Contracts: [spec 03 (input bounds)](../superpowers/specs/2026-10-13-portfolio-core/03-input-bounds.md),
  [spec 04 (equivalence)](../superpowers/specs/2026-10-13-portfolio-core/04-equivalence.md),
  [spec 05 (execution)](../superpowers/specs/2026-10-13-portfolio-core/05-verifier-execution.md).
- Code: `src/mathtutor/verify/` (`translate.py`, `equivalence.py`, `refute.py`, `pool.py`).
