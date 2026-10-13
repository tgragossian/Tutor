[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 189–243. Review findings remain unresolved.

### 4.3 Answer Verification

Use deterministic verification whenever practical.

Candidate technologies:

- SymPy
- NumPy
- Python numerical methods
- Validated answer keys

Support multiple answer types:

**Numerical answers**

Compare student and expected values using combined absolute and relative tolerances:

|student - expected| ≤ absolute_tolerance + relative_tolerance × |expected|

Tolerances should account for the problem's requested precision and mathematical context.

**Symbolic expressions**

Use SymPy to evaluate symbolic equivalence where supported.

**Derivatives**

Check symbolic equivalence between the submitted derivative and a validated expected derivative.

**Indefinite integrals**

Differentiate the student's proposed antiderivative and compare it to the integrand, accounting for domains and constants as appropriate.

**Linear algebra**

Support matrix operations, systems of linear equations, and other computational tasks.

**Differential equations**

Verify proposed solutions by substitution, including initial conditions where applicable.

The verifier should return at least:

- Correct
- Incorrect
- Unable to verify

Do not automatically classify unsupported or inconclusive checks as incorrect.

Important security requirement:

Student expressions are untrusted input. Avoid unrestricted Python evaluation or unsafe symbolic parsing. Use constrained parsing, resource limits, and isolation where appropriate.

Correct answers also do not necessarily imply correct reasoning.

<!-- End preserved source. -->
