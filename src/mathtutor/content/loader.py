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
from mathtutor.jsonio import loads_exact


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


def _plain(value: Any) -> bool:
    """Hashable scalar worth tracking; pydantic reports any other type."""
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def load_bundle(path: Path) -> LoadedContent:
    # Decimal literals become {"num": "<literal>"}: no float ever holds an answer value.
    try:
        data = loads_exact(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ContentError(f"{path.name}: (file): {e}") from e
    if not isinstance(data, dict):
        raise ContentError(f"{path.name}: (root): bundle must be a JSON object")

    raw_problems = data.get("problems")
    if not isinstance(raw_problems, list):
        raise ContentError(f"{path.name}: (root): problems must be a list")
    raw_topics = data.get("topics")
    if not isinstance(raw_topics, list):
        raise ContentError(f"{path.name}: (root): topics must be a list")
    errors: list[str] = []
    try:
        ContentBundle.model_validate({**data, "problems": []})
    except ValidationError as exc:
        errors += _lines(path.name, exc)

    for key in ("topic_id", "order"):
        seen_values: set[Any] = set()
        for i, t in enumerate(raw_topics):
            if not isinstance(t, dict) or not _plain(t.get(key)):
                continue
            if t[key] in seen_values:
                errors.append(f"topics[{i}]: {key}: duplicate")
            seen_values.add(t[key])

    topic_ids = {
        t["topic_id"] for t in raw_topics if isinstance(t, dict) and _plain(t.get("topic_id"))
    }
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
        if not _plain(topic):
            errors.append(f"{label}: topic: topic must be a string, got {topic!r}")
        elif topic not in topic_ids:
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
