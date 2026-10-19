# Code-review reproductions

[Findings](01-code-review.md) · [Review index](README.md)

Historical probes against 2f95748; their defect outputs are not expected after the fixes.
B-C1/B-C2/B-C3 were fixed in 8346d2a/b7f23ad/10611a5; see [review disposition](README.md).

Run each Python block with the milestone-B virtual environment from that worktree.
These probes were run against 2f95748. They demonstrate current bugs, not desired assertions.
They do not change application files. C2 deliberately leaves the huge outer power unevaluated.

## C1: false certified counterexample for equal expressions

```python
import time
import sympy as s
from mathtutor.verify.translate import translate, TranslateContext
from mathtutor.verify.refute import enclose, to_fraction, refute
from mathtutor.verify.equivalence import Budget

x = s.Symbol("x", real=True)
eps, big = ["Power", 10, -20], ["Power", 2, 240]
student = ["Abs", ["Divide", ["Add", ["Negate", ["Subtract",
    ["Add", big, ["Subtract", 2**38, eps]], big]], eps], 3]]
expected = ["Subtract", ["Divide", 2**38, 3],
    ["Divide", ["Multiply", 2, eps], 3]]
a = translate(student, TranslateContext())
b = translate(expected, TranslateContext())
box = enclose(a.expr, x, s.S.Zero)
exact = a.expr.doit()
assert s.simplify(a.expr - b.expr) == 0
assert s.Rational(to_fraction(box[1])) < exact  # invalid upper bound
print((s.Rational(to_fraction(box[1])) - exact).evalf())
print(refute(a, b, x, [s.S.Zero], Budget(time.monotonic() + 5)))
# -5.08626302083333e-6; counterexample
```

## C2: exponent bound bypass

```python
from mathtutor.verify.translate import translate, TranslateContext, Translated

for n in (10000, 10**29):
    exponent = ["Log", "e", ["Exp", ["Divide", 1, n]]]
    result = translate(["Power", 2, exponent], TranslateContext())
    assert isinstance(result, Translated)  # should reject as input_too_large
    assert result.expr.exp.doit() == n
    print(n, "accepted; exponent exceeds 1000")
# Never call result.expr.doit(), simplify(), or check() on the huge outer power.
```

## C3: cleanup on partial pool creation

```python
from unittest.mock import patch
from mathtutor.verify.pool import VerifierPool

class Worker:
    stopped = False
    def stop(self):
        self.stopped = True

first = Worker()
with patch.object(VerifierPool, "_new_worker",
                  side_effect=[first, OSError("second start fails")]):
    try:
        VerifierPool(size=2)
    except OSError:
        pass
assert not first.stopped  # should have been stopped by failed construction
```
