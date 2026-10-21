"""HTTP request/response DTOs. Public items never carry answers or MathJSON."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, JsonValue

from mathtutor.content.schema import ChoiceId, Source
from mathtutor.domain import Action


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


Latex = Annotated[str, Field(max_length=2000)]


class ExpressionAnswerIn(_Model):
    kind: Literal["expression"]
    mathjson: JsonValue
    latex: Latex


class NumericAnswerIn(_Model):
    kind: Literal["numeric"]
    mathjson: JsonValue
    latex: Latex


class ChoiceAnswerIn(_Model):
    kind: Literal["choice"]
    choice_id: ChoiceId


AnswerIn = Annotated[
    ExpressionAnswerIn | NumericAnswerIn | ChoiceAnswerIn, Field(discriminator="kind")
]


class SubmissionRequest(_Model):
    submission_id: UUID4
    session_item_id: Annotated[int, Field(gt=0)]
    item_revision: Annotated[int, Field(ge=0)]
    answer: AnswerIn


class PublicChoice(_Model):
    id: ChoiceId
    label_latex: str


class PublicItem(_Model):
    session_item_id: int
    revision: int
    statement_html: str
    answer_kind: Literal["expression", "numeric", "choice"]
    precision_hint: str | None = None
    choices: list[PublicChoice] | None = None
    source: Source
    allowed_actions: list[Action]
    tries_left: int


class ErrorBody(_Model):
    error: str
    message: str


class Credentials(_Model):
    """Register and login body. Lengths are checked by the service; these caps bound the body."""

    username: Annotated[str, Field(max_length=64)]
    password: Annotated[str, Field(max_length=256)]


class AuthUser(_Model):
    username: str
    csrf_token: str


class StartRequest(_Model):
    topics: Annotated[list[str], Field(min_length=1, max_length=3)]


class StartResponse(_Model):
    session_id: int


class ActionRequest(_Model):
    item_revision: Annotated[int, Field(ge=0)]


class VerdictOut(_Model):
    status: Literal["correct", "incorrect", "unable_to_verify"]
    reason: str
    method: str


class FormatIssueOut(_Model):
    code: str
    message: str


class SubmitResponse(_Model):
    outcome: VerdictOut | FormatIssueOut
    item: PublicItem
    replayed: bool


class CurrentResponse(_Model):
    item: PublicItem | None
    done: bool
    reason: str | None = None
    revealed_latex: str | None = None


class SessionSummaryOut(_Model):
    session_id: int
    topics: list[str]
    started_at: datetime
    answered: int
    correct: int
