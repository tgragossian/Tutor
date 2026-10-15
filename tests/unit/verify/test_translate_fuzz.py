from __future__ import annotations

from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mathtutor.verify.translate import Rejected, TranslateContext, Translated, translate

CTX = TranslateContext()

ALLOWED_HEADS = [
    "Add",
    "Subtract",
    "Negate",
    "Multiply",
    "InvisibleOperator",
    "Divide",
    "Power",
    "Sqrt",
    "Root",
    "Rational",
    "Sin",
    "Cos",
    "Tan",
    "Sec",
    "Csc",
    "Cot",
    "Ln",
    "Log",
    "Lb",
    "Exp",
    "Abs",
    "Delimiter",
]
UNKNOWN_HEADS = ["Arcsin", "Apply", "InverseFunction", "Matrix", "List", "Sequence", "Error", "f"]
ATOMS = ["x", "x", "Pi", "e", "ExponentialE", "y", "C", "Nothing", "PositiveInfinity", "'?'"]

leaves = st.one_of(
    st.sampled_from(ATOMS),
    st.integers(min_value=-(10**35), max_value=10**35),
    st.integers(min_value=-3, max_value=1100),
    st.builds(lambda s: {"num": s}, st.from_regex(r"-?[0-9]{0,4}(\.[0-9]{0,4})?(e-?[0-9]{1,3})?")),
    st.text(max_size=5),
    st.none(),
    st.booleans(),
    st.floats(allow_nan=True),
    st.dictionaries(st.text(max_size=3), st.integers(), max_size=2),
)


def trees() -> st.SearchStrategy[Any]:
    return st.recursive(
        leaves,
        lambda children: st.one_of(
            st.builds(
                lambda head, args: [head, *args],
                st.sampled_from(ALLOWED_HEADS + UNKNOWN_HEADS),
                st.lists(children, max_size=4),
            ),
            st.lists(children, max_size=3),
        ),
        max_leaves=40,
    )


@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(trees())
def test_translate_never_raises(tree: Any) -> None:
    assert isinstance(translate(tree, CTX), (Translated, Rejected))
