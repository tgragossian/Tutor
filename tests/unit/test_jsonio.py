from __future__ import annotations

from mathtutor.jsonio import loads_exact


def test_decimal_becomes_num_literal() -> None:
    assert loads_exact("[0.1, 2.675, 3]") == [{"num": "0.1"}, {"num": "2.675"}, 3]


def test_long_decimal_kept_verbatim() -> None:
    s = "0." + "1" * 29
    assert loads_exact(f"[{s}]") == [{"num": s}]


def test_exponent_literal_kept() -> None:
    assert loads_exact("1.5e+3") == {"num": "1.5e+3"}


def test_bytes_accepted() -> None:
    assert loads_exact(b'{"x": 0.5}') == {"x": {"num": "0.5"}}
