"""Exact-decimal JSON reading: a decimal literal never becomes a Python float."""

from __future__ import annotations

import json
from typing import Any


def as_num(literal: str) -> dict[str, str]:
    return {"num": literal}


def loads_exact(data: str | bytes) -> Any:
    return json.loads(data, parse_float=as_num)
