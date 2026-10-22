"""The six-problem bank the selection and practice tests were written against.

Pinning it keeps those tests about the rules, not about how many problems the bank holds.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from mathtutor.content.loader import LoadedContent, load_bundle

ROOT = Path(__file__).resolve().parents[2]
CORE_IDS = frozenset(
    {
        "openstax-c1-3.3-115",
        "openstax-c1-3.3-111",
        "adapted-c1-3.5-x2cosx",
        "openstax-c1-3.5-181",
        "openstax-c1-3.6-221",
        "openstax-c1-3.6-253",
    }
)


def core_content() -> LoadedContent:
    real = load_bundle(ROOT / "content" / "compiled" / "problems.json")
    problems = [p for p in real.bundle.problems if p.id in CORE_IDS]
    assert len(problems) == len(CORE_IDS)
    bundle = real.bundle.model_copy(update={"problems": problems})
    return dataclasses.replace(real, bundle=bundle)
