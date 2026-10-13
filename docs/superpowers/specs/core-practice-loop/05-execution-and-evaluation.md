[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 221–255. Review findings remain unresolved.

### 4.4 Sandbox

- Every check runs in a dedicated worker process: `multiprocessing` with spawn, one task at a time.
- The caller waits up to **3 s**, then kills and respawns the worker → `unable_to_verify`, reason `timeout`.
- Any worker exception → `unable_to_verify`, reason `internal_error` (logged).
- On Linux, `resource.setrlimit(RLIMIT_AS, 512 MB)` is applied in the worker. On Windows it is skipped.

### 4.5 Output

```python
@dataclass(frozen=True)
class Verdict:
    status: Literal["correct", "incorrect", "unable_to_verify"]
    reason: str          # machine-readable code, e.g. "symbolic_equal", "counterexample", "timeout"
    method: Literal["symbolic", "numeric", "exact", "rounding", "none"]
    latency_ms: int
```

Student-facing text:
- "Correct"
- "Not quite"
- "We couldn't check this answer automatically. It's saved; try a simpler form."

### 4.6 Verifier evaluation

- `eval/verifier_cases.yaml` holds **≥ 300** labelled cases `{problem_ref, student_mathjson, label}`.
- The cases cover:
  - tricky equivalents: trig identities, log rules, unsimplified forms, differing constants, decimals
  - typical errors: sign errors, a missing chain-rule factor, off-by-constant, wrong power
  - unsupported input
- `run_verifier_eval.py` reports the false-accept rate, false-reject rate, inconclusive rate and p50/p95 latency, broken down by answer type and method.
- CI fails on any false accept.

---

<!-- End preserved source. -->
