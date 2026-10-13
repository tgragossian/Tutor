"""Load and validate the compiled content bundle. pydantic is the only schema authority."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mathtutor.content.schema import ContentBundle, Problem
from mathtutor.domain import ReviewStatus


class ContentError(Exception):
    """Raised with one line per problem: ``<problem id or file>: <field>: <reason>``."""


def content_version(problem: Mapping[str, Any]) -> str:
    text = json.dumps(problem, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class LoadedContent:
    bundle: ContentBundle
    versions: dict[str, str]
    bundle_version: str


def _lines(label: str, exc: ValidationError) -> list[str]:
    return [
        f"{label}: {'.'.join(str(p) for p in e['loc']) or '(root)'}: {e['msg']}"
        for e in exc.errors()
    ]


def load_bundle(path: Path) -> LoadedContent:
    # Plain json.loads: MathJSON is not interpreted in milestone A, and Decimal would
    # not pass pydantic's JsonValue validation.
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ContentError(f"{path.name}: (file): {e}") from e
    if not isinstance(data, dict):
        raise ContentError(f"{path.name}: (root): bundle must be a JSON object")

    raw_problems = data.get("problems", [])
    errors: list[str] = []
    try:
        ContentBundle.model_validate({**data, "problems": []})
    except ValidationError as exc:
        errors += _lines(path.name, exc)

    topic_ids = {t.get("topic_id") for t in data.get("topics", []) if isinstance(t, dict)}
    seen: set[str] = set()
    for i, raw in enumerate(raw_problems):
        label = str(raw.get("id", f"problems[{i}]")) if isinstance(raw, dict) else f"problems[{i}]"
        try:
            Problem.model_validate(raw)
        except ValidationError as exc:
            errors += _lines(label, exc)
        if not isinstance(raw, dict):
            continue
        if label in seen:
            errors.append(f"{label}: id: duplicate problem id")
        seen.add(label)
        topic = raw.get("topic")
        if topic not in topic_ids:
            errors.append(f"{label}: topic: unknown topic {topic!r}")
    if errors:
        raise ContentError("\n".join(errors))

    bundle = ContentBundle.model_validate(data)
    versions = {p["id"]: content_version(p) for p in raw_problems}
    return LoadedContent(bundle, versions, content_version(data))


def servable(content: LoadedContent) -> list[Problem]:
    order = {t.topic_id: t.order for t in content.bundle.topics}
    ok = [p for p in content.bundle.problems if p.review.status is ReviewStatus.HUMAN_VERIFIED]
    return sorted(ok, key=lambda p: (order[p.topic], p.difficulty, p.id))
