"""Passing offline reproductions of C1-R4/R7 after the 2026-10-28 fixes.

Only synthetic data and fake generators. No actual holdout or provider credentials.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from support.evalkit import make_case, make_env, make_query
from support.helpkit import CFG, CONFUSIONS, CONTENT, output

from mathtutor.help.eval import run as runner
from mathtutor.help.eval.errors import RunnerError
from mathtutor.help.eval.holdout import claim, partition_of
from mathtutor.help.eval.judge import judge_case, judge_items
from mathtutor.help.generator import GenerationResult, ScriptedGenerator


def test_used_holdout_cannot_be_scored_by_retrieval_only(tmp_path, monkeypatch):
    env = make_env()
    cases = [make_case(case_id="h-001", split="holdout")]
    queries = [make_query(query_id="rq-h-001", split="holdout")]
    monkeypatch.setattr("mathtutor.help.eval.cases.load_split", lambda *_: (cases, queries))
    monkeypatch.setattr("mathtutor.content.loader.load_bundle", lambda *_: CONTENT)
    monkeypatch.setattr("mathtutor.help.context.load_confusions", lambda *_: CONFUSIONS)
    monkeypatch.setattr("mathtutor.retrieval.corpus.load_corpus", lambda *_: env.corpus)
    claim(tmp_path, partition_of(cases, queries), "used", "old", "old")

    def git(args):
        return "" if args[0] == "status" else "new"

    runner.check_freeze("holdout", "new", tmp_path, git)
    args = SimpleNamespace(draft=False, retrieval_only=True, split="holdout")
    with pytest.raises(RunnerError):
        runner._execute(args, tmp_path)


def test_no_passage_generation_reaches_judge_and_audit():
    env, case = make_env(retrieval=False), make_case()
    generator = ScriptedGenerator([output(text="Identify the outer function first.", ids=())])
    record = runner.run_case(case, generator, CFG.model, env)
    assert record.status == "delivered" and len(generator.requests) == 1
    scores = [
        {
            "response": 1,
            "leak": "none",
            "addresses_error": True,
            "endorses_wrong": False,
            "citations_supported": False,
            "math_error": False,
            "useful": True,
            "rationale": "Offline synthetic score.",
        }
    ]
    judge = ScriptedGenerator(
        [GenerationResult(json.dumps({"scores": scores}), "end_turn", 100, 10, CFG.model, None, 1)]
    )
    result = judge_case(case, [record], env, judge, "offline rubric", seed="review")
    assert judge_items([record]), (record.status, result.status, len(judge.requests))
    assert result.status == "ok" and len(judge.requests) == 1
