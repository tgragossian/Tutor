# Verifier findings

[Review index](README.md) · [Original rules](../../superpowers/specs/core-practice-loop/04-equivalence.md)

## V1 — P1: finite sampling cannot establish exact equivalence

Spec §4.2 / Task 4 accepts after ten agreeing points at tolerance 1e-8.
Against expected x, student x + 1/1000000000 is mathematically wrong but satisfies
that tolerance at every sampled point. Fifty-digit arithmetic does not fix this rule.
A fixed seed also misses isolated holes and narrow regions consistently.

Proposed policy: prove equality within explicitly supported expression families and
the declared domain; otherwise return unable_to_verify. Numeric probes may find
counterexamples, but sample agreement alone must not award exact correctness.
Keep approximate numerical answers as a separately specified task type.

## V2 — P1: symbolic simplification can erase domain restrictions

The first symbolic success returns before any domain check.
Student (x² - 1)/(x - 1) and expected x + 1 simplify to the same expression, but the
student expression is undefined at x = 1. Whether this matters depends on the prompt.
A sampling interval is not a mathematical domain or an equivalence convention.

Store allowed intervals, endpoint inclusion and excluded points separately.
Preserve domain constraints from the unsimplified input tree before SymPy evaluates it.
Follow-up refinement: use one default, equality on the stored real domain while ignoring
provably removable holes; allow a strict override when domain behavior is assessed.
Poles, missing real intervals and branch differences are not removable holes.
See the [current decision](../../decisions/0001-delivery-verifier-attribution.md).

## V3 — P1: antiderivative and implicit tasks need stronger contracts

Task 5 differentiates the expected antiderivative rather than storing the integrand.
For log(x), differentiation produces 1/x and can lose the real-domain issue on x < 0.
Store the integrand and real interval(s); check the student's function is real,
defined and differentiable there before comparing its derivative.
Specify whether a displayed +C is required; permit C only as an x-independent constant.

Task 6 searches for y using five nsolve starts: that does not enumerate all real branches.
It also says to compare where the student is defined, contradicting the global rule.
Follow-up refinement: retain polynomial implicit differentiation for topic expansion.
Replace sampling with exact reduction of F_x + F_y * submitted_derivative modulo F.
Check denominators, regularity and all included components under the decision's bounded
rational-expression contract. A zero numerator alone is insufficient.
An unresolved algebraic/domain check remains unable_to_verify.

## V4 — P1: bound work before constructing symbolic objects

Tasks 3/7 bound literal exponents, not computed ones: 10^(10^10) passes a literal-only
limit on the two tens. Decimal scientific exponents and oversized request bodies
also need limits. SymPy constructors may evaluate before simplification is called.

Validate raw byte size, JSON shape, arity, names, digit lengths, depth and operation
cost before construction. Bound computed constant powers conservatively; reject
unbudgeted forms. Translation and all math work belong inside the worker deadline.
Bound queue length and queue wait; replace dead workers and reap terminated processes.
A child process plus memory limits is resource containment, not a complete security sandbox.
The proposed two workers also require whole-host memory sizing; see [operations](operations.md).

## V5 — P2: precision and answer-type rules are inconsistent

Task 5 uses a bare-LaTeX decimal regex, but MathJSON is what gets graded.
Two client-controlled representations can disagree; decimals can hide in fractions.
Use one validated semantic representation. Preserve lexical precision separately,
bind it to the numeric value, or avoid enforcing trailing-zero counts in the MVP.
Define a decimal rounding mode and boundary behavior with decimal/rational arithmetic.

Task 5 checks empty LaTeX first, yet its multiple-choice test submits an empty LaTeX
string. Dispatch choice submissions before expression checks. Define typed payloads.
Task 3 does not declare C although Task 5 requires +C; abstract f(x) versus f(2x)
must not collapse to the same symbol. Specify real odd roots explicitly.
Point-set precision is per element; match one-to-one without greedy-order dependence.

Imported/LLM-generated answer strings are untrusted, even inside YAML.
Keep them on the allowlisted structured path. A local_dict does not make parse_expr
a safe parser: [SymPy documents its use of eval](https://docs.sympy.org/latest/modules/parsing.html).
