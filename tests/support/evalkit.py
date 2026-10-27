"""Synthetic help-evaluation cases and an ``EvalEnv`` over helpkit's tiny corpus and fake pools.

No provider call, no API key, no verifier worker: every generator is scripted.
"""

from __future__ import annotations

from typing import Any

from mathtutor.content.loader import load_bundle
from mathtutor.help.config import HelpConfig
from mathtutor.help.eval.cases import HelpCase, RetrievalQuery
from mathtutor.help.eval.gates import CASE_MIX
from mathtutor.help.eval.run import EvalEnv
from mathtutor.retrieval.corpus import Corpus
from support.helpkit import CFG, CONFUSIONS, DEFAULT_CHUNKS, ROOT, FakePool, MonoClock

PROBLEM_ID = "openstax-c1-3.6-221"
PROBLEMS = {
    p.id: p for p in load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
}


def make_case(**kw: Any) -> HelpCase:
    fields: dict[str, Any] = {
        "case_id": "dev-001",
        "split": "dev",
        "problem_id": PROBLEM_ID,
        "help_type": "hint",
        "attempts": ["3(3x^2+1)^2"],
        "confusion_id": None,
        "hint_level": 2,
        "tags": ["mistaken_reasoning", "known_error"],
        "expect_abstain": False,
        "note": "Missing the inner derivative 6x.",
        "reviewed_by": "tg",
    }
    fields.update(kw)
    if not fields["attempts"] and "hint_level" not in kw:
        fields["hint_level"] = 0  # R35: a hint with no wrong attempt yet is level 0
    return HelpCase.model_validate(fields)


def make_query(**kw: Any) -> RetrievalQuery:
    fields: dict[str, Any] = {
        "query_id": "rq-dev-01",
        "split": "dev",
        "section": "3.6",
        "text": "chain rule composite function derivative",
        "notation": "words",
        "relevant_ids": ["c1-3.6-rule1"],
        "reviewed_by": "tg",
    }
    fields.update(kw)
    return RetrievalQuery.model_validate(fields)


# Help types handed out per category so each split meets the gate minimums.
_TYPES = {
    "mistaken_reasoning": ["feedback", "feedback", "hint"],
    "nearly_right": ["feedback", "hint"],
    "tell_me_answer": ["hint", "explain"],
    "easy_l1_trap": ["hint"],
    "out_of_scope": ["hint", "feedback", "explain"],
    "ordinary": ["explain", "hint"],
}


def mix_cases(split: str, problems: list[tuple[str, str]]) -> list[HelpCase]:
    """A synthetic split that matches the gate mix; ``problems`` are (problem_id, topic)."""
    cases: list[HelpCase] = []
    n = 0
    for category, count in CASE_MIX[split].items():
        for i in range(count):
            help_type = _TYPES[category][i % len(_TYPES[category])]
            pid, topic = problems[n % len(problems)]
            label = CONFUSIONS[topic][0].id
            known = category in ("mistaken_reasoning", "nearly_right") and help_type != "explain"
            cases.append(
                make_case(
                    case_id=f"{split}-{n:03d}",
                    split=split,
                    problem_id=pid,
                    help_type=help_type,
                    attempts=["x"] if category != "out_of_scope" else [],
                    confusion_id=label if help_type == "explain" else None,
                    hint_level=1 if category != "out_of_scope" else 0,
                    tags=[category] + (["known_error"] if known else []),
                    expect_abstain=category == "out_of_scope",
                    withhold_sections=["3", "4", "5", "6"] if category == "out_of_scope" else [],
                )
            )
            n += 1
    return cases


def make_env(
    *, cfg: HelpConfig = CFG, retrieval: bool = True, guard: FakePool | None = None
) -> EvalEnv:
    corpus = Corpus({c.chunk_id: c for c in DEFAULT_CHUNKS}, "test-corpus-hash", "test")
    return EvalEnv(
        cfg=cfg,
        problems=PROBLEMS,
        corpus=corpus,
        confusions=CONFUSIONS,
        grading_pool=FakePool(),
        guard_pool=guard or FakePool(),
        retrieval=retrieval,
        clock=MonoClock(),
    )
