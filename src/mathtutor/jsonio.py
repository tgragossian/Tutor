"""Exact-decimal JSON reading: a decimal literal never becomes a Python float."""

from __future__ import annotations

import json
from typing import Any


def as_num(literal: str) -> dict[str, str]:
    return {"num": literal}


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite number {name} is not allowed")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def loads_exact(data: str | bytes) -> Any:
    """Parse JSON with exact decimals, and without NaN/Infinity or duplicate object keys."""
    return json.loads(
        data,
        parse_float=as_num,
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicates,
    )
