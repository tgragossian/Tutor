from __future__ import annotations

import json
from typing import Any

import anthropic
import httpx2
import pytest
from anthropic.lib._parse._transform import transform_schema
from anthropic.types import Message
from pydantic import ValidationError

from mathtutor.help.config import DEFAULT_CONFIG_PATH, load_help_config
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    ClaudeGenerator,
    GenerationRequest,
    GenerationResult,
    GeneratorError,
    HelpOutput,
    ScriptedGenerator,
)

CFG = load_help_config(DEFAULT_CONFIG_PATH)
KEY = "sk-ant-test-0123456789-secret"
REQ_URL = "https://api.anthropic.com/v1/messages"


def _req(**over: Any) -> GenerationRequest:
    fields: dict[str, Any] = dict(
        model=CFG.model,
        effort=CFG.effort,
        system="SYS",
        user="USER",
        schema=HELP_OUTPUT_SCHEMA,
        max_output_tokens=CFG.max_output_tokens,
        timeout_s=7.5,
    )
    fields.update(over)
    return GenerationRequest(**fields)


def _message(stop_reason: str = "end_turn", text: str | None = None) -> Message:
    body = (
        text
        if text is not None
        else json.dumps(
            {"text": "Try the chain rule.", "source_ids": ["c1-3.6-ex2"], "abstain": False}
        )
    )
    content: list[dict[str, Any]] = [{"type": "thinking", "thinking": "hm", "signature": "s"}]
    content.append({"type": "text", "text": body})
    msg = Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": CFG.model,
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1234, "output_tokens": 56},
        }
    )
    msg._request_id = "req_abc"
    return msg


class FakeMessages:
    def __init__(self, outcome: Message | Exception) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome: Message | Exception) -> None:
        self.messages = FakeMessages(outcome)


class Factory:
    def __init__(self, outcome: Message | Exception) -> None:
        self.client = FakeClient(outcome)
        self.kwargs: dict[str, Any] = {}

    def __call__(self, **kwargs: Any) -> FakeClient:
        self.kwargs = kwargs
        return self.client


def _gen(outcome: Message | Exception) -> tuple[ClaudeGenerator, Factory]:
    factory = Factory(outcome)
    ticks = iter([10.0, 10.25])
    return ClaudeGenerator(KEY, client_factory=factory, clock=lambda: next(ticks)), factory


def test_claude_request_shape() -> None:
    gen, factory = _gen(_message())
    result = gen.generate(_req())
    assert factory.kwargs["api_key"] == KEY
    assert factory.kwargs["max_retries"] == 0
    [call] = factory.client.messages.calls
    assert call["model"] == CFG.model
    assert call["max_tokens"] == CFG.max_output_tokens
    assert call["system"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
    assert call["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": HELP_OUTPUT_SCHEMA},
    }
    assert call["timeout"] == 7.5
    assert result == GenerationResult(
        text=json.dumps(
            {"text": "Try the chain rule.", "source_ids": ["c1-3.6-ex2"], "abstain": False}
        ),
        stop_reason="end_turn",
        input_tokens=1234,
        output_tokens=56,
        model=CFG.model,
        provider_request_id="req_abc",
        latency_ms=250,
    )


def test_key_not_in_repr() -> None:
    gen, _ = _gen(_message())
    assert KEY not in repr(gen)
    assert KEY not in str(vars(gen))


def _status(code: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", REQ_URL)
    response = httpx2.Response(code, request=request)
    cls = anthropic.RateLimitError if code == 429 else anthropic.APIStatusError
    return cls(f"Error code: {code} - echoed {KEY}", response=response, body=None)


@pytest.mark.parametrize(
    ("exc", "kind", "billed_unknown"),
    [
        (anthropic.APITimeoutError(request=httpx2.Request("POST", REQ_URL)), "timeout", True),
        (anthropic.APIConnectionError(request=httpx2.Request("POST", REQ_URL)), "connection", True),
        (_status(429), "rate_limited", False),
        (_status(500), "api_error", False),
        (_status(529), "api_error", False),
        (_status(400), "api_error", False),
    ],
)
def test_maps_errors(exc: Exception, kind: str, billed_unknown: bool) -> None:
    gen, _ = _gen(exc)
    with pytest.raises(GeneratorError) as info:
        gen.generate(_req())
    err = info.value
    assert err.kind == kind
    assert err.billed_unknown is billed_unknown
    assert err.__cause__ is None and err.__context__ is None
    assert KEY not in str(err) and KEY not in repr(err)


@pytest.mark.parametrize("stop", ["refusal", "max_tokens", "model_context_window_exceeded"])
def test_refusal_and_truncation(stop: str) -> None:
    gen, _ = _gen(_message(stop_reason=stop))
    result = gen.generate(_req())
    assert result.text is None
    assert result.stop_reason == stop
    assert result.input_tokens == 1234 and result.output_tokens == 56
    assert result.provider_request_id == "req_abc"


def test_no_text_block_is_none() -> None:
    msg = _message()
    msg.content = []
    gen, _ = _gen(msg)
    assert gen.generate(_req()).text is None


def _valid(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"text": "Look at $u = 3x$.", "source_ids": ["a"], "abstain": False}
    data.update(over)
    return data


@pytest.mark.parametrize(
    "bad",
    [
        _valid(extra=1),
        _valid(source_ids=[str(i) for i in range(7)]),
        _valid(source_ids=["a", "a"]),
        _valid(text="x" * 2001),
        _valid(source_ids=[]),
        _valid(source_ids=[""]),
        _valid(text="   "),
        {"text": "t", "source_ids": ["a"]},
    ],
)
def test_help_output_validation(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        HelpOutput.model_validate_json(json.dumps(bad))


def test_help_output_accepts() -> None:
    assert HelpOutput.model_validate(_valid()).source_ids == ["a"]
    assert HelpOutput.model_validate(_valid(text="x" * 2000, source_ids=list("abcdef")))
    abstain = HelpOutput.model_validate({"text": "", "source_ids": [], "abstain": True})
    assert abstain.abstain


def test_schema_matches_model_and_api_subset() -> None:
    assert transform_schema(HELP_OUTPUT_SCHEMA) == HELP_OUTPUT_SCHEMA
    assert HELP_OUTPUT_SCHEMA["additionalProperties"] is False
    assert set(HELP_OUTPUT_SCHEMA["required"]) == set(HelpOutput.model_fields)
    assert set(HELP_OUTPUT_SCHEMA["properties"]) == set(HelpOutput.model_fields)


def test_scripted_generator_replays() -> None:
    ok = GenerationResult("{}", "end_turn", 1, 2, "m", None, 0)
    err = GeneratorError("timeout", billed_unknown=True)
    gen = ScriptedGenerator([ok, err])
    assert gen.generate(_req()) is ok
    with pytest.raises(GeneratorError) as info:
        gen.generate(_req(user="second"))
    assert info.value is err
    assert [r.user for r in gen.requests] == ["USER", "second"]
    with pytest.raises(RuntimeError, match="exhausted"):
        gen.generate(_req())
