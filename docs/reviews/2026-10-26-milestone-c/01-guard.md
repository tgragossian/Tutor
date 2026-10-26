# C-R1: a grading check is not a leakage check

[Review](README.md) · [Amended guard](../../superpowers/specs/2026-10-26-milestone-c/03-guard-and-limits.md)

## Evidence

- [CheckRequest](../../../src/mathtutor/verify/types.py) contains an answer specification and
  a `SubmittedAnswer` with MathJSON. It is not a general LaTeX or task-solving interface.
- [precheck](../../../src/mathtutor/verify/precheck.py) rejects missing MathJSON. Existing
  [LaTeX compilation](../../../tools/compile_content/compile.mjs) runs offline in Node.
- [check](../../../src/mathtutor/verify/check.py) can return `FormatIssue`, `incorrect`,
  `unable_to_verify` or `correct`; domain rejection is distinct from formula inequality.
- [equivalent](../../../src/mathtutor/verify/equivalence.py) proves the formula and then
  checks domain admissibility. `incorrect` does not universally mean the formula is hidden.

## Why it matters

For reference `2x`, the expression `2x + (x-1)/(x-1) - 1` discloses the answer formula even
if a strict-domain grading rule rejects its hole. A timeout, unsupported function or
format rejection also does not establish absence of leakage. Never map “not correct” to safe.
The original delimiter scan misses `\(...\)`, malformed math, bare `2x`, prose, successive
hints assembling an answer, and elimination of all wrong choices. Listing the correct
choice's exact LaTeX does not catch an algebraically equivalent rendering.

## Required design changes

1. Add a bounded runtime parser adapter; preserve raw MathJSON and use the existing
   allowlist translator in a killable worker. Never parse untrusted model text with `eval`
   or unrestricted `sympify`/`parse_expr`. Model-supplied ASTs cannot attest to displayed text.
2. Use a dedicated `leak | no_match | unchecked` result. Formula equality blocks before
   domain grading; only certified inequality clears a supported candidate. Unknown blocks.
3. Validate full output before delivery, including after retry; never stream unguarded text.
   The guard covers all supported candidates, not just a model-selected expression list.
4. Validate schema, math rendering and citation membership before display. A citation to a
   retrieved chunk is not evidence that the chunk supports the generated claim.
5. Keep Reveal as the sole intentional answer action; replace “never leaks” with a measured
   limitation. Hints-only C3 responses cannot claim guard coverage.

## Verification needed

Pin vectors for factored equivalents, numeric answers/rounding, RHS extraction, all supported
delimiters, unsupported syntax, malformed math, domain holes, choice paraphrases/elimination,
empty extraction, mixed prose/math and L1→L3 cumulative leakage. Include prose attacks in
human evaluation; deterministic checks cannot establish their absence.

Proving every intermediate formula unequal may block useful hints (`f'(x)`, general rules).
Measure this false-block cost and delivered helpfulness together. Do not improve coverage
by silently treating unparsed candidates as safe. Prompt examples should use notation the
bounded adapter supports; templates/section nudges are the fallback for unsupported forms.
