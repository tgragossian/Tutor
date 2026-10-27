"""The blind judge: one call per case scores every model's raw help outputs at once.

The prompt never names a model: responses are numbered in an order shuffled by
``random.Random(f"{seed}:{case_id}")``, and the order (item keys) is recorded with the
judgment. The judge alone sees the authoritative answer and the cited passages' text
(spec 08: offline judging only). The rubric is ``evals/help/rubric/v1.md``.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mathtutor.content.schema import ChoiceAnswer
from mathtutor.help.eval.cases import HelpCase, confusion_label
from mathtutor.help.generator import GenerationRequest, Generator, GeneratorError, HelpOutput
from mathtutor.help.pipeline import answer_latex
from mathtutor.retrieval.corpus import Chunk, estimate_tokens

if TYPE_CHECKING:  # avoids an import cycle with run.py
    from mathtutor.help.eval.run import CaseRecord, EvalEnv

JUDGE_MODEL = "claude-sonnet-5-5"
JUDGE_EFFORT = "medium"
JUDGE_MAX_INPUT_TOKENS = 12_000  # estimated as ceil(utf8_bytes / 3), like the help prompt
JUDGE_MAX_OUTPUT_TOKENS = 4_000  # thinking counts inside it
RUBRIC_VERSION = "v1"
LeakKind = Literal["none", "expression", "prose"]


@dataclass(frozen=True)
class JudgeItem:
    """One raw help output to score. ``key`` (``<model>#<call_no>``) never reaches the
    prompt."""

    key: str
    text: str
    cited_ids: list[str]


@dataclass(frozen=True)
class Score:
    leak: LeakKind
    addresses_error: bool
    endorses_wrong: bool
    citations_supported: bool
    math_error: bool
    useful: bool
    rationale: str


@dataclass
class Judgment:
    case_id: str
    seed: str
    order: list[str]
    scores: dict[str, Score]
    status: str  # ok | invalid | error | no_items | max_tokens
    usage: tuple[int | None, int | None] | None = None
    billed_unknown: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudgePrompt:
    system: str
    user: str
    order: list[str]


class _Score(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    response: int
    leak: LeakKind
    addresses_error: bool
    endorses_wrong: bool
    citations_supported: bool
    math_error: bool
    useful: bool
    rationale: str = Field(max_length=1000)


class _Reply(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    scores: list[_Score]


_BOOL = {"type": "boolean"}
JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "response": {"type": "integer"},
                    "leak": {"type": "string", "enum": ["none", "expression", "prose"]},
                    "addresses_error": _BOOL,
                    "endorses_wrong": _BOOL,
                    "citations_supported": _BOOL,
                    "math_error": _BOOL,
                    "useful": _BOOL,
                    "rationale": {"type": "string", "description": "One or two sentences."},
                },
                "required": [
                    "response",
                    "leak",
                    "addresses_error",
                    "endorses_wrong",
                    "citations_supported",
                    "math_error",
                    "useful",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scores"],
    "additionalProperties": False,
}


def load_rubric(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def judge_items(records: list[CaseRecord]) -> list[JudgeItem]:
    """Every raw output that parses as non-abstaining help, from every model's record."""
    items: list[JudgeItem] = []
    for rec in records:
        for raw in rec.raws:
            if raw.text is None:
                continue
            try:
                out = HelpOutput.model_validate_json(raw.text)
            except ValidationError:
                continue
            if not out.abstain:
                items.append(JudgeItem(f"{rec.model}#{raw.call_no}", out.text, out.source_ids))
    return items


def _answer_block(case: HelpCase, problem: Any) -> list[str]:
    answer = problem.answer
    lines = [f"Reference answer (never shown to the student): {answer_latex(answer)}"]
    if isinstance(answer, ChoiceAnswer):
        opts = "; ".join(f"({c.id}) {c.latex}" for c in answer.choices)
        lines.append(f"Options: {opts}. The correct option is ({answer.correct}).")
        lines.append("Attempts below are the options the student chose.")
    return lines


def _level_note(case: HelpCase) -> str:
    """The hint level the response should be written at (ruling R35)."""
    if case.help_type != "hint":
        return ""
    if case.hint_choice:
        written = 1 if case.expect_mistake == "new" else case.hint_level
        return (
            f" (hint level {written}: the latest attempt is a {case.expect_mistake} mistake "
            "compared with the earlier one)"
        )
    return f" (hint level {case.hint_level})"


def build_judge_prompt(
    case: HelpCase,
    problem: Any,
    label: str | None,
    items: list[JudgeItem],
    passages: list[Chunk],
    rubric: str,
    seed: str,
) -> JudgePrompt:
    order = [i.key for i in items]
    random.Random(seed).shuffle(order)
    by_key = {i.key: i for i in items}
    system = (
        "You grade tutoring help for a Calculus I practice app, using the rubric below. "
        "Grade each numbered response on its own; responses come from unnamed systems in "
        "random order.\n\n" + rubric
    )
    lines = [
        "<case>",
        f"Problem statement: {problem.statement}",
        *_answer_block(case, problem),
        f"Help requested: {case.help_type}" + _level_note(case),
    ]
    if label:
        lines.append(f'Confusion the student picked: "{label}"')
    if case.attempts:
        lines.append("Student attempts, oldest first: " + " | ".join(case.attempts))
    else:
        lines.append("The student has not attempted the problem.")
    lines += [f"What the case author says the attempt shows: {case.note}", "</case>", ""]
    lines.append("<passages>")
    for chunk in passages:
        lines.append(f'<passage id="{chunk.chunk_id}">\n{chunk.text}\n</passage>')
    lines += ["</passages>", ""]
    for n, key in enumerate(order, 1):
        item = by_key[key]
        cited = ", ".join(item.cited_ids) or "(none)"
        lines += [f"<response number={n}>", f"Cited passages: {cited}", item.text, "</response>"]
    lines.append(f"\nScore all {len(order)} responses: one entry per response number, as JSON.")
    return JudgePrompt(system, "\n".join(lines), order)


def judge_case(
    case: HelpCase,
    records: list[CaseRecord],
    env: EvalEnv,
    generator: Generator,
    rubric: str,
    *,
    seed: str,
) -> Judgment:
    case_seed = f"{seed}:{case.case_id}"
    items = judge_items(records)
    if not items:
        return Judgment(case.case_id, case_seed, [], {}, "no_items")
    problem = env.problems[case.problem_id]
    cited = list(dict.fromkeys(i for item in items for i in item.cited_ids))
    passages = [env.corpus.chunks[i] for i in cited if i in env.corpus.chunks]
    label = confusion_label(case, problem, env.confusions)
    prompt = build_judge_prompt(case, problem, label, items, passages, rubric, case_seed)
    if estimate_tokens(prompt.system + prompt.user) > JUDGE_MAX_INPUT_TOKENS:
        return Judgment(case.case_id, case_seed, prompt.order, {}, "too_long")
    req = GenerationRequest(
        model=JUDGE_MODEL,
        effort=JUDGE_EFFORT,
        system=prompt.system,
        user=prompt.user,
        schema=JUDGE_SCHEMA,
        max_output_tokens=JUDGE_MAX_OUTPUT_TOKENS,
        timeout_s=120.0,
    )
    try:
        reply = generator.generate(req)
    except GeneratorError as err:
        unknown = err.billed_unknown or err.status_code == 504
        return Judgment(case.case_id, case_seed, prompt.order, {}, "error", None, unknown)
    usage = (reply.input_tokens, reply.output_tokens)
    if reply.text is None:
        status = "max_tokens" if reply.stop_reason == "max_tokens" else "invalid"
        return Judgment(case.case_id, case_seed, prompt.order, {}, status, usage)
    try:
        parsed = _Reply.model_validate(json.loads(reply.text))
    except (ValidationError, ValueError):
        return Judgment(case.case_id, case_seed, prompt.order, {}, "invalid", usage)
    numbers = sorted(s.response for s in parsed.scores)
    if numbers != list(range(1, len(prompt.order) + 1)):
        return Judgment(case.case_id, case_seed, prompt.order, {}, "invalid", usage)
    scores = {
        prompt.order[s.response - 1]: Score(
            s.leak,
            s.addresses_error,
            s.endorses_wrong,
            s.citations_supported,
            s.math_error,
            s.useful,
            s.rationale,
        )
        for s in parsed.scores
    }
    return Judgment(case.case_id, case_seed, prompt.order, scores, "ok", usage)
