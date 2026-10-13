[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 426–434. Review findings remain unresolved.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| MathLive's MathJSON output differs from what the translator assumes (canonicalization, abstract functions, primes) | The first implementation task is a spike that captures real MathLive output for the 20 seed answers into fixtures; the translator is built against those fixtures. Fallback: parse MathLive's LaTeX with a restricted grammar (lark). |
| `simplify` is slow or hangs | Sandbox timeout. Numeric check as the second path. Latency tracked in the evaluation. |
| Numeric check falsely accepts expressions that agree only on part of the domain | Per-problem `sample_domain`. The evaluation set includes deliberately near-equivalent wrong answers. |
| Scope creep from extra features | Section 1.3 lists what is out of scope. New ideas go to the roadmap, not this spec. |
| Lightsail/HTTPS setup eats time | Deployment is its own plan milestone. The app is fully usable locally before it starts. |
<!-- End preserved source. -->
