# 0001 — delivery order, verifier defaults and attribution

[Decision index](README.md) · [Handoff](../../handoff.md)

Status: option B and attribution selected by Thomas on 2026-10-13.
Verifier refinements incorporate the supplied Claude review; safeguards below make the
proposed algebraic check precise. No application code has been implemented.

## Delivery order

Deploy a skeleton early, complete three-topic practice, add RAG hints, then finish
operations and release evaluation. Testing and measurement begin with the first feature.
Keep the broader roadmap in order: diagnostic -> exam conditions/recap ->
all 15 topics -> extraction pipeline -> LoRA. (Amended by [0005](0005-tutoring-datasets-and-fine-tuning.md) §6:
LoRA runs directly after milestone C.)
Each stage requires the previous stage's exit evidence; do not drop queued features.
The eight-week estimate covers the initial core, not a guarantee for the full queue.

## One domain default

Each problem stores a real domain, with intervals/exclusions and curve constraints as needed.
Default equivalence: equal on that domain, ignoring provably removable holes.
Use an optional strict_domain override for problems assessing exact definedness.
Authors need not select a policy separately for every ordinary exercise.

Keep restrictions from the original AST before cancellation.
Under the default, (x² - 1)/(x - 1) and x + 1 agree across the removable hole.
Under strict_domain on an interval containing 1, they do not.
Do not erase genuine poles, complex/branch mismatches or missing domain intervals.
For example, 2 ln(x) does not equal ln(x²) across negative real x.
A hole is ignored only when its real extension is established in the supported family.
No proof of removability or domain coverage -> unable_to_verify.

## Retain exact polynomial implicit checking

Define the contract early; implement it with implicit-topic content during topic expansion.
Initially support reviewed, square-free polynomial curves F(x,y) with rational
coefficients and rational submitted expressions P(x,y)/Q(x,y).
Apply bounds on degree, terms and coefficient sizes, plus the worker deadline.
Reviewed content declares real regions/branches and excludes points where F_y = 0
from ordinary finite dy/dx grading; vertical tangents need separate questions.

Compute N = F_x * Q + F_y * P exactly.
Reduce N modulo F (or the declared component ideal) using polynomial reduction.
A zero remainder establishes the identity on that algebraic locus.
SymPy exposes quotient/remainder reduction through its
[polynomial API](https://docs.sympy.org/latest/modules/polys/reference.html#sympy.polys.polytools.GroebnerBasis.reduce).
The grading rule here is our design, not a completeness guarantee supplied by that API.

Before accepting, establish Q != 0 on the required regular domain, except proven
removable holes under the shared default. Never clear denominators and forget them.
Reject an invalid content template with no assessed real regular arc.
Do not accept vacuous identities where Q vanishes on the entire assessed curve/component.
Check every included component; for reducible curves, use reviewed component templates.
If branch/domain coverage cannot be established, return unable_to_verify.
A nonzero remainder alone is not a universal proof of incorrectness on an arbitrary
real restricted domain; require a certified counterexample or abstain.
Radical submissions and transcendental curves need additional methods and may abstain.

Required later cases: circle -x/y accepted; wrong sign rejected at a certified point;
curve-equivalent rational form accepted on its declared regular domain; a denominator
that vanishes on the curve not accepted; singular points/branches handled explicitly.
Include removable-hole default versus strict override and resource-limit cases.
Numeric sampling may diagnose a failure; it never certifies an implicit answer.

## Commit attribution

Do not add automatic Claude or Codex coauthor trailers.
Use a README footnote acknowledging actual AI assistance.
Do not rewrite existing Git history for this change.
