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


class JsonTooDeep(ValueError):
    """Arrays/objects nested deeper than allowed (checked before parsing)."""


def json_depth(data: str | bytes) -> int:
    """Deepest array/object nesting, found with one iterative pass (no recursion), ignoring
    brackets inside strings. Malformed input is left to the parser to reject."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    depth = deepest = 0
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            deepest = max(deepest, depth)
        elif ch in "]}":
            depth -= 1
    return deepest


def loads_exact(data: str | bytes, max_depth: int | None = None) -> Any:
    """Parse JSON with exact decimals, and without NaN/Infinity or duplicate object keys.

    With ``max_depth``, deeper input raises ``JsonTooDeep`` before the (recursive) parser
    runs; a parser recursion failure is reported the same way, never as a crash.
    """
    if max_depth is not None and json_depth(data) > max_depth:
        raise JsonTooDeep(f"JSON is nested more than {max_depth} levels deep")
    try:
        return _loads(data)
    except RecursionError:
        raise JsonTooDeep("JSON is nested too deeply") from None


def _loads(data: str | bytes) -> Any:
    return json.loads(
        data,
        parse_float=as_num,
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicates,
    )
