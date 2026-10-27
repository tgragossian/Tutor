"""Provider-neutral text generation for help, its Claude implementation and a scripted fake.

``ClaudeGenerator`` makes exactly one Messages API call per ``generate`` (SDK retries off) with
structured output against ``HELP_OUTPUT_SCHEMA``. It never parses or judges the text: a stop
reason other than ``end_turn`` yields ``text=None`` and the service treats that as invalid.
Errors become ``GeneratorError`` with only a kind and a billing flag: no provider message,
no chained exception, so nothing the provider echoed (or the API key) can reach a log.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import anthropic
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_TEXT_CHARS = 2000
MAX_SOURCE_IDS = 6

GeneratorErrorKind = Literal["timeout", "connection", "rate_limited", "api_error", "bad_response"]


@dataclass(frozen=True)
class GenerationRequest:
    model: str
    effort: str
    system: str
    user: str
    schema: dict[str, Any]
    max_output_tokens: int
    timeout_s: float


@dataclass(frozen=True)
class GenerationResult:
    text: str | None
    stop_reason: str
    input_tokens: int | None
    output_tokens: int | None
    model: str
    provider_request_id: str | None
    latency_ms: int


class GeneratorError(Exception):
    """A failed call. ``billed_unknown``: the request may have reached the provider and been
    billed (timeouts and dropped connections); the caller must not resend it."""

    def __init__(
        self, kind: GeneratorErrorKind, billed_unknown: bool = False, status_code: int | None = None
    ) -> None:
        super().__init__(kind)
        self.kind: GeneratorErrorKind = kind
        self.billed_unknown = billed_unknown
        self.status_code = status_code

    def __repr__(self) -> str:
        return (
            f"GeneratorError(kind={self.kind!r}, billed_unknown={self.billed_unknown}, "
            f"status_code={self.status_code})"
        )


class Generator(Protocol):
    def generate(self, req: GenerationRequest) -> GenerationResult: ...


class HelpOutput(BaseModel):
    """The model's JSON reply. Shape only; membership of ``source_ids`` in the passages the
    prompt provided is the service's check."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    text: str = Field(max_length=MAX_TEXT_CHARS)
    source_ids: list[str] = Field(max_length=MAX_SOURCE_IDS)
    abstain: bool

    @model_validator(mode="after")
    def _citations(self) -> HelpOutput:
        if any(not s.strip() for s in self.source_ids):
            raise ValueError("source ids must be non-empty")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source ids must be unique")
        if not self.abstain:
            if not self.source_ids:
                raise ValueError("non-abstaining help needs at least one source id")
            if not self.text.strip():
                raise ValueError("non-abstaining help needs text")
        return self


# Structured outputs accept a subset of JSON Schema: no length or item-count limits, so those
# live in the descriptions (for the model) and in ``HelpOutput`` (enforced).
HELP_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": (
                f"The help for the student, at most {MAX_TEXT_CHARS} characters; all math in "
                "$...$. Empty when abstaining."
            ),
        },
        "source_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                f"Ids of the provided passages the text relies on: 1 to {MAX_SOURCE_IDS} unique "
                "ids, or none when abstaining."
            ),
        },
        "abstain": {
            "type": "boolean",
            "description": "True when the passages do not support helpful, safe help.",
        },
    },
    "required": ["text", "source_ids", "abstain"],
    "additionalProperties": False,
}

_TEXT_STOP_REASONS = frozenset({"end_turn"})


def _default_factory(**kwargs: Any) -> Any:
    return anthropic.Anthropic(**kwargs)


class ClaudeGenerator:
    """``Generator`` over the Anthropic Messages API (anthropic SDK, pinned in pyproject).

    The key is handed to the client at construction and not kept on this object.
    ``client_factory`` and ``clock`` exist for tests (a fake client; no network in pytest).
    """

    def __init__(
        self,
        api_key: str,
        *,
        client_factory: Callable[..., Any] = _default_factory,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # open_telemetry=False: no SDK spans, so an environment switch can never turn on
        # request/response content tracing.
        self._client = client_factory(api_key=api_key, max_retries=0, open_telemetry=False)
        self._clock = clock

    def __repr__(self) -> str:
        return "ClaudeGenerator()"

    def generate(self, req: GenerationRequest) -> GenerationResult:
        started = self._clock()
        error: GeneratorError | None = None
        try:
            message = self._client.messages.create(
                model=req.model,
                max_tokens=req.max_output_tokens,
                system=req.system,
                messages=[{"role": "user", "content": req.user}],
                output_config={
                    "effort": req.effort,
                    "format": {"type": "json_schema", "schema": req.schema},
                },
                timeout=req.timeout_s,
            )
        except anthropic.APITimeoutError:  # subclass of APIConnectionError: test first
            error = GeneratorError("timeout", billed_unknown=True)
        except anthropic.APIConnectionError:
            error = GeneratorError("connection", billed_unknown=True)
        except anthropic.RateLimitError as exc:
            error = GeneratorError("rate_limited", status_code=exc.status_code)
        except anthropic.APIStatusError as exc:
            error = GeneratorError("api_error", status_code=exc.status_code)
        except anthropic.AnthropicError:
            # Unclassified (e.g. a response that fails the SDK's own validation): the request
            # may have been served and billed (review C1-R3).
            error = GeneratorError("api_error", billed_unknown=True)
        if error is not None:  # raised outside the handler: no __context__ to the SDK error
            raise error
        try:
            return self._result(message, started)
        except Exception:  # noqa: BLE001, S110 - a reply we cannot read was still sent and billed
            pass
        # Raised outside the handler: no __context__ carrying provider content.
        raise GeneratorError("bad_response", billed_unknown=True)

    def _result(self, message: Any, started: float) -> GenerationResult:
        latency_ms = round((self._clock() - started) * 1000)
        stop_reason = str(message.stop_reason)
        texts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
        text = "".join(texts) if texts and stop_reason in _TEXT_STOP_REASONS else None
        usage = message.usage
        return GenerationResult(
            text=text,
            stop_reason=stop_reason,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            model=str(message.model),
            provider_request_id=getattr(message, "_request_id", None),
            latency_ms=latency_ms,
        )


class ScriptedGenerator:
    """Replays ``script`` in order (a ``GeneratorError`` entry is raised); records requests.
    Drives every test and the e2e run: no provider call."""

    def __init__(self, script: list[GenerationResult | GeneratorError]) -> None:
        self.script = list(script)
        self.requests: list[GenerationRequest] = []

    def generate(self, req: GenerationRequest) -> GenerationResult:
        self.requests.append(req)
        if not self.script:
            raise RuntimeError("scripted generator exhausted")
        step = self.script.pop(0)
        if isinstance(step, GeneratorError):
            raise step
        return step


class FixedHintGenerator:
    """env=test only: answers every request with one fixed hint citing the first passage in the
    prompt, so the browser e2e needs no provider and no script. Used for
    ``MATHTUTOR_HELP_GENERATOR=scripted`` when no generator is injected."""

    TEXT = "Name the outer function first, then the inner one."
    _PASSAGE = re.compile(r'<passage id="([^"]+)"')

    def generate(self, req: GenerationRequest) -> GenerationResult:
        found = self._PASSAGE.search(req.user)
        ids = [found.group(1)] if found else []
        reply = {"text": self.TEXT, "source_ids": ids, "abstain": False}
        return GenerationResult(json.dumps(reply), "end_turn", 0, 0, "fixed-test", None, 0)
