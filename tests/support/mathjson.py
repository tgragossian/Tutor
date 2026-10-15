"""Access to the real-browser MathJSON fixtures captured by tools/capture."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from mathtutor.jsonio import loads_exact

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "mathjson" / "captured.json"


@cache
def _load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def mj(key: str) -> Any:
    """The non-canonical MathJSON captured for ``key`` (stored as JSON text)."""
    return loads_exact(_load()["cases"][key]["mathjson"])


def keys() -> list[str]:
    """Every captured case key."""
    return list(_load()["cases"])


def latex(key: str) -> str:
    """The LaTeX string MathLive reported for ``key`` (display/logging only)."""
    return str(_load()["cases"][key]["latex_out"])


def meta() -> dict[str, str]:
    return dict(_load()["meta"])
