"""Compiled-content schema. MathJSON is typed as ``JsonValue`` and never interpreted here."""

from __future__ import annotations

import datetime
import re
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue, model_validator

from mathtutor.domain import ReviewStatus

_RATIONAL = re.compile(r"^-?\d+(/\d+)?$")
_INF = ("-inf", "inf")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _bound(text: str) -> Fraction | None:
    """A finite bound as a Fraction, or None for an infinite end."""
    if text in _INF:
        return None
    if not _RATIONAL.match(text):
        raise ValueError(f"bound must be -inf, inf or a rational string, got {text!r}")
    try:
        return Fraction(text)
    except ZeroDivisionError:
        raise ValueError(f"bound has a zero denominator: {text!r}") from None


def _check_interval(iv: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
    lo, hi, lo_kind, hi_kind = iv
    if lo == "inf" or hi == "-inf":
        raise ValueError("interval ends are in the wrong order")
    lo_f, hi_f = _bound(lo), _bound(hi)
    if lo_f is None and lo_kind != "open":
        raise ValueError("an infinite end must be open")
    if hi_f is None and hi_kind != "open":
        raise ValueError("an infinite end must be open")
    if lo_f is not None and hi_f is not None and not lo_f < hi_f:
        raise ValueError("interval requires lo < hi")
    return iv


Interval = Annotated[
    tuple[str, str, Literal["open", "closed"], Literal["open", "closed"]],
    AfterValidator(_check_interval),
]


def _inside(point: Fraction, iv: tuple[str, str, str, str]) -> bool:
    lo, hi, lo_kind, hi_kind = iv
    lo_f, hi_f = _bound(lo), _bound(hi)
    if lo_f is not None and (point < lo_f or (point == lo_f and lo_kind == "open")):
        return False
    return not (hi_f is not None and (point > hi_f or (point == hi_f and hi_kind == "open")))


def _all_reals() -> list[Interval]:
    return [("-inf", "inf", "open", "open")]


class Domain(_Model):
    intervals: list[Interval] = Field(default_factory=_all_reals, min_length=1)
    exclude: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _exclusions_inside(self) -> Domain:
        for text in self.exclude:
            if text in _INF:
                raise ValueError(f"excluded point must be a rational, got {text!r}")
            point = _bound(text)
            assert point is not None
            if not any(_inside(point, iv) for iv in self.intervals):
                raise ValueError(f"excluded point {text} is not inside the domain")
        return self


class Source(_Model):
    book: str
    section: str
    exercise: int | None = None
    url: str
    license: Literal["CC BY-NC-SA 4.0"]
    adapted: bool = False

    @model_validator(mode="after")
    def _openstax_url(self) -> Source:
        if not self.url.startswith("https://openstax.org/"):
            raise ValueError("source url must start with https://openstax.org/")
        return self


class Decimals(_Model):
    decimals: Annotated[int, Field(ge=0, le=10)]


Precision = Decimals | Literal["exact"]

ChoiceId = Annotated[str, Field(pattern=r"^[a-z]$")]


class Choice(_Model):
    id: ChoiceId
    latex: str
    mathjson: JsonValue


class Review(_Model):
    status: ReviewStatus
    reviewer: str = ""
    date: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _verified_needs_reviewer_and_date(self) -> Review:
        if self.status is ReviewStatus.HUMAN_VERIFIED:
            if not self.reviewer.strip():
                raise ValueError("human_verified requires a reviewer")
            try:
                datetime.date.fromisoformat(self.date)
            except ValueError:
                raise ValueError("human_verified requires an ISO date (YYYY-MM-DD)") from None
        return self


class ExpressionAnswer(_Model):
    kind: Literal["expression"]
    latex: str
    mathjson: JsonValue
    variable: str = "x"
    domain: Domain = Field(default_factory=Domain)
    strict_domain: bool = False


class NumericAnswer(_Model):
    kind: Literal["numeric"]
    latex: str
    mathjson: JsonValue
    precision: Precision
    variable: str = "x"
    domain: Domain = Field(default_factory=Domain)
    strict_domain: bool = False


class ChoiceAnswer(_Model):
    kind: Literal["choice"]
    choices: Annotated[list[Choice], Field(min_length=2, max_length=6)]
    correct: ChoiceId

    @model_validator(mode="after")
    def _correct_is_a_choice(self) -> ChoiceAnswer:
        ids = [c.id for c in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError("choice ids must be unique")
        if self.correct not in ids:
            raise ValueError(f"correct {self.correct!r} is not one of the choice ids")
        return self


Answer = Annotated[ExpressionAnswer | NumericAnswer | ChoiceAnswer, Field(discriminator="kind")]


class Topic(_Model):
    topic_id: str
    title: str
    order: int
    section: str


NOTE_SEPARATOR = "  # "


def split_misconception(entry: str) -> tuple[str, str | None]:
    """An authored misconception as (answer part, note); the note is None when absent/empty."""
    head, sep, note = entry.partition(NOTE_SEPARATOR)
    note = note.strip()
    return head.strip(), (note if sep and note else None)


class Problem(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.\-]*$")]
    topic: str
    difficulty: Annotated[int, Field(ge=1, le=5)]
    source: Source
    statement: str
    statement_html: str
    answer: Answer
    misconceptions: list[str] = Field(default_factory=list)
    # One entry per misconception, in order; null where the LaTeX did not parse cleanly.
    misconceptions_mathjson: list[JsonValue] | None = None
    review: Review

    @model_validator(mode="after")
    def _mathjson_matches_misconceptions(self) -> Problem:
        if self.misconceptions_mathjson is not None and len(self.misconceptions_mathjson) != len(
            self.misconceptions
        ):
            raise ValueError("misconceptions_mathjson must match misconceptions in length")
        return self


class ToolVersions(_Model):
    mathlive: str
    compute_engine: str


class ContentBundle(_Model):
    schema_version: Literal[2]
    tools: ToolVersions
    topics: list[Topic]
    problems: list[Problem]
