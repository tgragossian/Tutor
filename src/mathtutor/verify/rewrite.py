"""R23: rewrite a recorded constraint into equivalent constraints on its inner argument.

Each rule is an exact equivalence on the reals wherever the inner argument is defined (the
translator records the argument's own constraints separately). Matching is on the unevaluated
tree; nothing is simplified.
"""

from __future__ import annotations

import sympy

from mathtutor.verify.translate import Constraint


def reduce_constraint(c: Constraint) -> tuple[Constraint, ...]:
    """Equivalent constraints on inner arguments; ``()`` means it always holds.

    A constraint no rule matches is returned unchanged as ``(c,)``.
    """
    if c.kind in ("not_half_pi_odd", "not_pi_multiple"):
        return (c,)  # lattice kinds are exact only for linear arguments: never rewritten
    expr = c.expr
    if expr.func is sympy.exp:
        return ()
    if isinstance(expr, sympy.Abs):
        if c.kind == "nonnegative":
            return ()
        return reduce_constraint(Constraint("nonzero", expr.args[0]))
    if c.kind != "nonzero":
        return (c,)
    if isinstance(expr, sympy.cos):
        return reduce_constraint(Constraint("not_half_pi_odd", expr.args[0]))
    if isinstance(expr, sympy.sin | sympy.tan):
        return reduce_constraint(Constraint("not_pi_multiple", expr.args[0]))
    if expr.is_Mul:
        return tuple(
            part
            for factor in expr.args
            for part in reduce_constraint(Constraint("nonzero", factor))
        )
    if expr.is_Pow and expr.exp.is_Integer and expr.exp.is_positive:
        return reduce_constraint(Constraint("nonzero", expr.base))
    return (c,)
