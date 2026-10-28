"""Versioned help prompts: ``build_prompt`` turns a ``HelpContext`` and passages into
``(system, user)`` messages.

The prompt text lives in ``prompts/<prompt_version>/*.md``. Student text (attempt LaTeX) is
placed only inside ``<student_text>``; passages inside ``<passage id="...">``; any tag of ours
appearing inside data is neutralized so data cannot close its block. Fields are clipped to the
config's ``field_caps`` and, if the estimate still exceeds ``max_input_tokens``, passage text
is truncated from the lowest-ranked passage up. Every passage id stays in the prompt, so the
set of ids the model may cite is always exactly the ids of ``chunks``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from functools import cache
from pathlib import Path

from mathtutor.domain import AnswerKind
from mathtutor.help.config import DEFAULT_CONFIG_PATH, HelpConfig, load_help_config
from mathtutor.help.context import HelpContext, HelpType
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    HINT_CHOICE_SCHEMA,
    MISTAKE_DESCRIPTIONS,
    MISTAKE_TYPES,
)
from mathtutor.retrieval.corpus import Chunk, estimate_tokens

PROMPTS_DIR = Path(__file__).with_name("prompts")
REPAIR_INSTRUCTION = (
    "Your previous draft revealed or could not be checked; give a smaller next step without "
    "expressions equal to the answer."
)
TRUNCATED = " [passage shortened]"
# Ruling R35 (Thomas, 2026-10-27): level 0 before any wrong answer; after one, each mistake
# type climbs 1 -> 2 -> 3 with the hints it has had on this problem.
LEVEL_RULES = {
    0: "how to start. The student has not submitted a wrong answer yet: name the rule or idea "
    "that applies to this problem and the first move to make, without carrying it out.",
    1: "a gentle nudge about their latest attempt. Say what they got right, say that "
    "something is missing or off without naming it, and ask them to compare their answer with "
    "the original problem.",
    2: "a more direct pointer. Name the specific part of the problem or of their answer to "
    "look at, and the question to ask about it, without writing the corrected step.",
    3: "a fuller explanation. Walk through the method on this problem step by step, still "
    "stopping before the final answer.",
}
# Level 0 has two steps before any wrong answer (Thomas, 2026-10-27); step 2 then repeats.
START_RULES = {
    1: LEVEL_RULES[0],
    2: "a more concrete start. The student asked again before answering: say concretely what "
    "to identify or write down first on this problem, without carrying out any step of the "
    "solution.",
}
_TAGS = (
    "student_text|passages?|problem|attempts?|misconception_note|confusion|task|repair|"
    "system|user|assistant|instructions?"
)
_TAG = re.compile(rf"<(?=\s*/?\s*(?:{_TAGS})\b)", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


@cache
def _default_config() -> HelpConfig:
    return load_help_config(DEFAULT_CONFIG_PATH)


@cache
def prompt_fingerprint(version: str) -> str:
    """12 hex characters identifying the exact instruction text of a prompt set (Q3, Thomas
    2026-10-27): every ``prompts/<version>/*.md`` file, this module's source (the level rules
    and other instruction text kept in code), the output schemas and the mistake-type
    descriptions (``generator.py``). Any wording change gives
    a new fingerprint, so results and help rows prove which text produced them."""
    digest = hashlib.sha256()
    files = sorted((PROMPTS_DIR / version).glob("*.md")) + [Path(__file__)]
    for path in files:
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    for data in (HELP_OUTPUT_SCHEMA, HINT_CHOICE_SCHEMA, MISTAKE_DESCRIPTIONS):
        digest.update(json.dumps(data, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:12]


def prompt_id(version: str) -> str:
    """The prompt set as recorded on help rows and runs: ``v1+<fingerprint>``."""
    return f"{version}+{prompt_fingerprint(version)}"


@cache
def _template(version: str, name: str) -> str:
    return (PROMPTS_DIR / version / f"{name}.md").read_text(encoding="utf-8").strip()


def estimate_prompt_tokens(system: str, user: str) -> int:
    """The budget estimate, ``ceil(utf8_bytes / 3)``, over both messages."""
    return estimate_tokens(system + user)


def _clip(text: str, max_bytes: int) -> str:
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")


def _data(text: str, max_bytes: int | None = None) -> str:
    """Clip, then neutralize our tags (``<`` → ``&lt;``) so data cannot open or close a block."""
    clipped = text if max_bytes is None else _clip(text, max_bytes)
    return _TAG.sub("&lt;", clipped)


def _fill(template: str, values: dict[str, str]) -> str:
    # One pass: inserted values are never rescanned for placeholders.
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def _context_block(ctx: HelpContext, caps: dict[str, int]) -> str:
    lines = [
        "<problem>",
        f"Topic: {_data(ctx.topic, 200)}",
        f"Textbook section: {_data(ctx.section, 50)}",
        f"Answer kind: {ctx.answer_kind.value}",
    ]
    if ctx.answer_kind is AnswerKind.EXPRESSION:  # numeric/choice carry a placeholder variable
        lines.append(f"Variable: ${_data(ctx.variable, 20)}$")
    lines += [f"Statement: {_data(ctx.statement, caps['statement'])}", "</problem>", ""]
    if ctx.attempts:
        lines.append(
            f"<attempts> The student's recent attempts, newest first "
            f"(tries used so far: {ctx.tries_used}):"
        )
        for i, a in enumerate(ctx.attempts, 1):
            latex = _data(a.latex, caps["attempt_latex"])
            lines.append(f"{i}. <student_text>{latex}</student_text> checked: {a.status.value}")
        lines.append("</attempts>")
    else:
        lines.append("The student has not submitted an attempt on this problem yet.")
    if ctx.misconception_note:
        note = _data(ctx.misconception_note, caps["misconception_note"])
        lines += [
            "",
            "<misconception_note> What the student likely did wrong, from a reviewed list of "
            "common mistakes. Use it only to aim your help; never state the corrected "
            f"expression or form. Note: {note}</misconception_note>",
        ]
    return "\n".join(lines)


def _passages_block(chunks: list[Chunk], texts: list[str]) -> str:
    if not chunks:
        return "Textbook passages: none are provided for this request."
    parts = ["Textbook passages:"]
    for c, text in zip(chunks, texts, strict=True):
        title = _data(f"{c.section} {c.section_title}", 200).replace('"', "'")
        parts.append(f'<passage id="{c.chunk_id}" section="{title}">\n{text}\n</passage>')
    return "\n".join(parts)


def _choice_task(levels: Mapping[str, int], cfg: HelpConfig) -> str:
    """The classifying hint (R35): each mistake type with its level, then those levels' rules."""
    if set(levels) != set(MISTAKE_TYPES) or not all(1 <= v <= 3 for v in levels.values()):
        raise ValueError("a classifying hint needs a level 1-3 for every mistake type")
    types = "\n".join(
        f"- `{t}` ({MISTAKE_DESCRIPTIONS[t]}): Level {levels[t]}" for t in MISTAKE_TYPES
    )
    rules = "\n".join(f"- Level {n}: {LEVEL_RULES[n]}" for n in sorted(set(levels.values())))
    return _fill(_template(cfg.prompt_version, "hint_choice"), {"types": types, "rules": rules})


def _task(
    ctx: HelpContext,
    help_type: HelpType,
    label: str | None,
    cfg: HelpConfig,
    hint_levels: Mapping[str, int] | None = None,
) -> str:
    if hint_levels is not None:
        if help_type != "hint":
            raise ValueError("only a hint classifies the mistake")
        return _choice_task(hint_levels, cfg)
    template = _template(cfg.prompt_version, help_type)
    if help_type == "hint":
        level = min(max(ctx.hint_level, 0), 3)
        step = min(max(ctx.start_step, 1), 2)
        rule = START_RULES[step] if level == 0 else LEVEL_RULES[level]
        return _fill(template, {"level": str(level), "level_rule": rule})
    if help_type == "explain":
        if not label:
            raise ValueError("explain help needs a confusion label")
        clipped = _data(label, cfg.field_caps["confusion_text"]).replace('"', "'")
        return _fill(template, {"confusion": clipped})
    return _fill(template, {})


def build_prompt(
    ctx: HelpContext,
    help_type: HelpType,
    chunks: list[Chunk],
    confusion_label: str | None,
    strict: bool,
    *,
    cfg: HelpConfig | None = None,
    no_passages: bool = False,
    hint_levels: Mapping[str, int] | None = None,
) -> tuple[str, str]:
    """``(system, user)`` for one generator call; ``ValueError`` if no trim fits the budget.
    ``no_passages`` is the evaluation-only baseline (review C1-R7): ``chunks`` must be empty
    and ``no_passages.md`` is appended to the system prompt; production never sets it."""
    cfg = cfg or _default_config()
    system = _template(cfg.prompt_version, "system")
    if no_passages:
        if chunks:
            raise ValueError("the no-passage baseline takes no passages")
        system += "\n\n" + _template(cfg.prompt_version, "no_passages")
    head = _context_block(ctx, cfg.field_caps)
    tail = f"<task>\n{_task(ctx, help_type, confusion_label, cfg, hint_levels)}\n</task>"
    if strict:
        tail += f"\n\n<repair>{REPAIR_INSTRUCTION}</repair>"
    texts = [_data(c.text) for c in chunks]

    def user() -> str:
        return f"{head}\n\n{_passages_block(chunks, texts)}\n\n{tail}"

    budget = cfg.max_input_tokens
    for i in reversed(range(len(texts))):
        excess = estimate_prompt_tokens(system, user()) - budget
        if excess <= 0:
            break
        keep = len(texts[i].encode("utf-8")) - 3 * excess - len(TRUNCATED)
        texts[i] = _clip(texts[i], keep) + TRUNCATED if keep > 0 else TRUNCATED.strip()
    message = user()
    if estimate_prompt_tokens(system, message) > budget:
        raise ValueError("prompt does not fit the input token budget")
    return system, message
