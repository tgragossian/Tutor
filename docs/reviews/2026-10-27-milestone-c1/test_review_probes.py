"""Offline desired-behavior probes for C1 review; strict xfails document current bugs.

Run explicitly with pytest; no key, network, real holdout or real verifier workers.
After fixing a finding, remove its xfail marker and retain the regression in tests/.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from support.evalkit import PROBLEM_ID, PROBLEMS, make_case, make_env, make_query
from support.helpkit import CFG, CONFUSIONS, CONTENT, ROOT, FakePool, MonoClock, make_kit, output

from mathtutor.domain import VerdictStatus
from mathtutor.help.context import AttemptLine, assemble_context
from mathtutor.help.eval import run as runner
from mathtutor.help.eval.run import RunnerError, check_freeze, run_case
from mathtutor.help.generator import ClaudeGenerator, FixedHintGenerator, ScriptedGenerator
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.retrieval.query import build_query
from mathtutor.settings import Settings
from mathtutor.web.app import _load_help


@pytest.mark.xfail(strict=True, reason="C1-R1: runtime image lacks content/help")
def test_runtime_image_loads_help(tmp_path: Path) -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    # Model the current COPY instructions without pretending this builds Docker.
    assert "COPY content/corpus/" in dockerfile
    assert "COPY content/help/" not in dockerfile
    settings = Settings(
        env="test",
        help_generator="scripted",
        anthropic_api_key=None,
        corpus_path=ROOT / "content/corpus/chunks.jsonl",
        confusions_path=tmp_path / "app/content/help/confusions.json",
    )
    assert _load_help(settings, CFG, FixedHintGenerator()) is not None


@pytest.mark.xfail(strict=True, reason="C1-R2: foreign composites bypass verification")
@pytest.mark.parametrize("suffix", ["f(x)-f(x)", r"\theta-\theta", "y'-y'"])
def test_answer_plus_canceling_foreign_terms_is_blocked(suffix: str) -> None:
    answer = PROBLEMS[PROBLEM_ID].answer
    pool, clock = FakePool(), MonoClock()
    guard = LeakGuard(pool, CFG.guard, clock)
    result = guard.check(f"${answer.latex}+{suffix}$", answer, clock() + 15)
    assert result.decision == "block", (result, len(pool.requests))


@pytest.mark.xfail(strict=True, reason="C1-R3: post-dispatch decode error settles zero")
def test_reply_decode_error_retains_spend_reservation(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    sent: list[dict] = []

    def create(**kwargs: object) -> SimpleNamespace:
        sent.append(kwargs)
        # A returned response with malformed content; failure is after dispatch.
        return SimpleNamespace(stop_reason="end_turn", content=None)

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    kit.svc._pipeline._generator = ClaudeGenerator(
        "offline-test-key", client_factory=lambda **_: client, clock=kit.clock
    )
    result = kit.help()
    assert result.status.value == "unavailable"
    assert len(sent) == 1
    usage = kit.usage()
    assert len(usage) == 1
    assert usage[0].state == "uncertain", (usage[0].state, usage[0].settled_micros)


@pytest.mark.xfail(strict=True, reason="C1-R4: freeze tracks commit instead of dataset use")
@pytest.mark.parametrize("marker", ["started.json", "run.json"])
def test_used_holdout_stays_used_after_new_commit(tmp_path: Path, marker: str) -> None:
    prior = tmp_path / "evals/help/results/prior"
    prior.mkdir(parents=True)
    (prior / marker).write_text(json.dumps({"split": "holdout", "head": "old"}))

    def git(args: list[str]) -> str:
        return "" if args[0] == "status" else "new"

    # Only the precondition helper on synthetic metadata; never invokes the holdout CLI.
    with pytest.raises(RunnerError):
        check_freeze("holdout", "new", tmp_path, git)


@pytest.mark.xfail(strict=True, reason="C1-R5: last guard verdict can arrive after deadline")
def test_pipeline_does_not_deliver_after_guard_overruns() -> None:
    env = make_env()
    start = env.clock()

    def late_verdict(request: object) -> object:
        env.clock.t += 2
        return FakePool().submit(request).outcome

    env.guard_pool = FakePool(late_verdict)

    class SlowGenerator(ScriptedGenerator):
        def generate(self, req):
            env.clock.t += CFG.deadline_s - 0.1
            return super().generate(req)

    generator = SlowGenerator([output(text="Look for the inner expression $x$.")])
    record = run_case(make_case(), generator, CFG.model, env)
    assert env.clock() - start > CFG.deadline_s
    assert record.status != "delivered", (record.status, record.elapsed_ms)


@pytest.mark.xfail(strict=True, reason="C1-R6: feedback query picks oldest retained attempt")
def test_feedback_query_uses_latest_wrong_attempt() -> None:
    ctx = assemble_context(
        PROBLEMS[PROBLEM_ID],
        [
            AttemptLine("old_attempt", VerdictStatus.INCORRECT),
            AttemptLine("latest_attempt", VerdictStatus.INCORRECT),
        ],
        1,
        None,
    )
    query = build_query(ctx, "feedback", None, CFG.retrieval)
    assert "latest_attempt" in query and "old_attempt" not in query, query


@pytest.mark.xfail(strict=True, reason="C1-R7: no-retrieval baseline never generates")
def test_no_retrieval_ablation_still_samples_model() -> None:
    generator = ScriptedGenerator([output()])
    record = run_case(make_case(), generator, CFG.model, make_env(retrieval=False))
    assert generator.requests, (record.status, record.reason, record.calls)


@pytest.mark.xfail(strict=True, reason="C1-R9: interrupted evaluation loses durable spend")
def test_interrupted_dev_run_preserves_cost(tmp_path: Path, monkeypatch) -> None:
    env = make_env()
    generator = ScriptedGenerator([output()])
    monkeypatch.setattr(
        "mathtutor.help.eval.cases.load_split", lambda *_: ([make_case()], [make_query()])
    )
    monkeypatch.setattr("mathtutor.content.loader.load_bundle", lambda *_: CONTENT)
    monkeypatch.setattr("mathtutor.help.context.load_confusions", lambda *_: CONFUSIONS)
    monkeypatch.setattr("mathtutor.retrieval.corpus.load_corpus", lambda *_: env.corpus)
    monkeypatch.setattr("mathtutor.help.eval.judge.load_rubric", lambda *_: "offline rubric")
    monkeypatch.setattr("mathtutor.help.generator.ClaudeGenerator", lambda *_: generator)

    class OfflinePool(FakePool):
        def close(self) -> None:
            pass

    monkeypatch.setattr("mathtutor.verify.pool.VerifierPool", lambda **_: OfflinePool())
    # Never read or set the real key environment variable.
    monkeypatch.setattr(runner, "API_KEY_ENV", "C1_REVIEW_DUMMY_KEY")
    monkeypatch.setenv("C1_REVIEW_DUMMY_KEY", "offline-placeholder")
    original_run = runner.run_eval
    spent = []

    def interrupted(*args, **kwargs):
        def interrupt_after_case(_):
            spent.append(args[4].spent_micros)
            raise KeyboardInterrupt

        kwargs["log"] = interrupt_after_case
        return original_run(*args, **kwargs)

    monkeypatch.setattr(runner, "run_eval", interrupted)
    args = SimpleNamespace(
        draft=False,
        retrieval_only=False,
        split="dev",
        max_usd="4",
        models=CFG.model,
        run_id="interrupted",
        seed="review",
        no_retrieval=False,
        no_judge=True,
        freeze=None,
    )
    with pytest.raises(KeyboardInterrupt):
        runner._execute(args, tmp_path)
    assert len(generator.requests) == 1 and spent[0] > 0
    # This is the accounting artifact consumed by the documented next-run credit formula.
    assert (tmp_path / "evals/help/results/interrupted/run.json").exists(), spent
