"""The evaluation runner: the production pipeline per case, raw vs delivered, spend cap, freeze."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from support.evalkit import make_case, make_env
from support.helpkit import CFG, CORRECT, FakePool, output

from mathtutor.help.config import worst_case_micros
from mathtutor.help.eval.judge import Judgment
from mathtutor.help.eval.run import (
    RunnerError,
    SpendCounter,
    check_freeze,
    main,
    parse_usd,
    run_case,
    run_eval,
)
from mathtutor.help.generator import GenerationResult, GeneratorError, ScriptedGenerator
from mathtutor.help.pipeline import HelpStatus

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"


def test_run_case_keeps_raw_outputs_and_delivered_result() -> None:
    gen = ScriptedGenerator([output(ids=("nope",)), output()])
    record = run_case(make_case(), gen, SONNET, make_env())
    assert record.status == HelpStatus.DELIVERED.value and record.model == SONNET
    assert [r.outcome for r in record.raws] == ["invalid_citation", "ok"]
    assert (
        all(r.text for r in record.raws) and record.text == json.loads(record.raws[1].text)["text"]
    )
    assert [c["outcome"] for c in record.calls] == ["invalid_citation", "ok"]
    assert record.cited_ids == ["c1-3.6-rule1"] and record.retrieved_ids
    assert all(req.model == SONNET for req in gen.requests)  # the model under evaluation
    assert "3(3x^2+1)^2" in gen.requests[0].user  # the case's attempt reached the prompt
    assert record.category == "mistaken_reasoning" and record.known_error


def test_run_case_records_generator_error_without_raw_text() -> None:
    gen = ScriptedGenerator([GeneratorError("timeout", billed_unknown=True)])
    record = run_case(make_case(), gen, HAIKU, make_env())
    assert record.status == HelpStatus.UNAVAILABLE.value and record.raws == []
    assert record.calls[0]["billed_unknown"] is True


def _uncited(text: str = "Find the outer function first.") -> GenerationResult:
    body = json.dumps({"text": text, "source_ids": [], "abstain": False})
    return GenerationResult(body, "end_turn", 1_000, 100, HAIKU, None, 1)


def test_no_retrieval_baseline_calls_the_same_generator_without_passages() -> None:
    """Review C1-R7: the ablation samples the model; it is not an always-abstaining control."""
    gen = ScriptedGenerator([_uncited()])
    record = run_case(make_case(), gen, HAIKU, make_env(retrieval=False))
    assert record.status == HelpStatus.DELIVERED.value
    assert record.retrieved_ids == [] and record.cited_ids == []
    (req,) = gen.requests
    assert req.model == HAIKU and "none are provided" in req.user and "<passage" not in req.user
    assert "no passages" in req.system.lower()


def test_no_retrieval_baseline_rejects_invented_citations_and_still_guards() -> None:
    cited = output(ids=("c1-3.6-rule1",))  # no passage exists to cite
    leaking = _uncited("It is $18x(3x^2+1)^2$.")
    gen = ScriptedGenerator([cited, leaking])
    env = make_env(retrieval=False, guard=FakePool(CORRECT))
    record = run_case(make_case(), gen, HAIKU, env)
    assert [c["outcome"] for c in record.calls][0] == "invalid_schema"
    assert record.status == HelpStatus.UNAVAILABLE.value  # no section to nudge toward
    assert record.text is None


def test_production_prompt_has_no_baseline_addendum() -> None:
    gen = ScriptedGenerator([output()])
    run_case(make_case(), gen, HAIKU, make_env())
    assert "no passages" not in gen.requests[0].system.lower()


def test_withheld_sections_leave_no_evidence() -> None:
    case = make_case(
        tags=["out_of_scope"], expect_abstain=True, attempts=[], withhold_sections=["3"]
    )
    record = run_case(case, ScriptedGenerator([]), HAIKU, make_env())
    assert record.status == HelpStatus.ABSTAINED.value and record.expect_abstain


def test_choice_attempts_are_shown_as_the_chosen_option() -> None:
    case = make_case(problem_id="adapted-c1-3.6-sinx2", attempts=["b"])
    gen = ScriptedGenerator([output()])
    record = run_case(case, gen, HAIKU, make_env())
    user = gen.requests[0].user
    assert r"\cos(x^2)" in user and "missing inner derivative" in user
    assert record.misconception_matched


def _big(tokens: tuple[int, int]) -> GenerationResult:
    return output(tokens=tokens)


def test_spend_cap() -> None:
    # 400k in + 100k out on Sonnet's tariff: worst case and actual cost 1.8 USD per call.
    cfg = CFG.model_copy(update={"max_input_tokens": 400_000, "max_output_tokens": 100_000})
    per_call = worst_case_micros(cfg, SONNET)
    assert per_call == 1_800_000
    cases = [make_case(case_id=f"dev-{i:03d}") for i in range(10)]
    gen = ScriptedGenerator([_big((400_000, 100_000)) for _ in range(10)])
    spend = SpendCounter(cfg, parse_usd("8"))
    log: list[str] = []
    result = run_eval(cases, [SONNET], gen, make_env(cfg=cfg), spend, judge=None, log=log.append)
    # Four calls (7.2 USD); a fifth would reserve 1.8 more and pass 8, so it is never made.
    assert len(gen.requests) == 4 and len(result.records) == 4
    assert spend.spent_micros == 7_200_000 <= 8_000_000
    assert result.stopped and "cap" in result.stopped
    assert any("7.200000" in line for line in log)  # spend so far is printed after each case


def test_spend_cap_refuses_a_repair_call() -> None:
    cfg = CFG.model_copy(update={"max_input_tokens": 400_000, "max_output_tokens": 100_000})
    bad = output(ids=("nope",), tokens=(400_000, 100_000))
    gen = ScriptedGenerator([bad, _big((400_000, 100_000))])
    spend = SpendCounter(cfg, parse_usd("3"))
    result = run_eval([make_case()], [SONNET], gen, make_env(cfg=cfg), spend, judge=None)
    assert len(gen.requests) == 1 and spend.spent_micros == 1_800_000
    assert result.records[0].budget_stopped and result.stopped


def test_unknown_usage_is_charged_at_worst_case() -> None:
    spend = SpendCounter(CFG, parse_usd("4"))
    assert spend.charge(spend.help_cfg, HAIKU, None, None, billed_unknown=True) == 1_300
    assert spend.charge(spend.help_cfg, HAIKU, None, None, billed_unknown=False) == 0
    assert spend.charge(spend.help_cfg, HAIKU, 2_000, 300) == 350
    assert spend.spent_micros == 1_650


def test_parse_usd_is_exact_integer_micros() -> None:
    assert parse_usd("4") == 4_000_000 and parse_usd("0.000001") == 1
    for bad in ("-1", "0", "abc", "1.0000001"):
        with pytest.raises(ValueError):
            parse_usd(bad)


def test_judge_reply_without_usage_is_charged_at_judge_worst_case() -> None:
    spend = SpendCounter(CFG, parse_usd("4"))

    def judge(case: object, recs: object) -> Judgment:
        return Judgment("dev-001", "s", [], {}, "invalid", (None, 400))

    run_eval([make_case()], [HAIKU], ScriptedGenerator([output()]), make_env(), spend, judge=judge)
    # Haiku help call (2,000 in / 300 out = 350) + the judge's worst case (64,000).
    assert spend.worst_judge() == 64_000 and spend.spent_micros == 350 + 64_000


def test_help_reply_without_usage_is_charged_at_worst_case() -> None:
    spend = SpendCounter(CFG, parse_usd("4"))
    reply = GenerationResult(output().text, "end_turn", None, None, HAIKU, None, 1)
    result = run_eval(
        [make_case()], [HAIKU], ScriptedGenerator([reply]), make_env(), spend, judge=None
    )
    assert spend.spent_micros == 1_300 and result.records[0].cost_micros == 1_300


def test_default_git_targets_the_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    class Done:
        stdout = "abc123\n"

    def fake_run(cmd: list[str], **_kw: object) -> Done:
        seen.append(cmd)
        Done.stdout = "" if "status" in cmd else "abc123\n"
        return Done()

    monkeypatch.setattr("mathtutor.help.eval.run.subprocess.run", fake_run)
    check_freeze("holdout", "abc123", tmp_path)
    assert seen and all(cmd[:3] == ["git", "-C", str(tmp_path)] for cmd in seen)


@pytest.mark.parametrize("marker", ["run.json", "started.json"])
def test_unclaimed_holdout_marker_blocks_every_commit(tmp_path: Path, marker: str) -> None:
    """Review C1-R4: a holdout marker from before claims means that holdout was used; a new
    commit does not make it fresh."""
    prior = tmp_path / "evals" / "help" / "results" / "prior"
    prior.mkdir(parents=True)
    (prior / marker).write_text(json.dumps({"split": "holdout", "head": "old"}), "utf-8")
    with pytest.raises(RunnerError, match="without a claim"):
        check_freeze("holdout", "abc", tmp_path, git=_git())
    check_freeze("dev", None, tmp_path, git=_git())  # development runs are unaffected


def test_holdout_claim_written_before_the_first_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from mathtutor.help.eval import cases as eval_cases
    from mathtutor.help.eval import run as eval_run

    root = Path(__file__).resolve().parents[3]
    for part in ("content/compiled", "content/help", "content/corpus", "evals/help"):
        shutil.copytree(root / part, tmp_path / part)
    shutil.rmtree(tmp_path / "evals/help/results", ignore_errors=True)
    shutil.rmtree(tmp_path / "evals/help/holdout-claims", ignore_errors=True)
    monkeypatch.setattr(eval_cases, "unreviewed", lambda _rows: [])
    monkeypatch.setattr(eval_run, "_try_git", lambda _root, _args: "abc123")
    monkeypatch.setenv("MATHTUTOR_ANTHROPIC_API_KEY", "sk-test")

    class NoPool:
        def __init__(self, **_kw: object) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr("mathtutor.verify.pool.VerifierPool", NoPool)
    monkeypatch.setattr("mathtutor.help.generator.ClaudeGenerator", lambda _key: None)
    seen: list[bool] = []

    def first_call(*_args: object, **_kw: object) -> None:
        seen.append(any((tmp_path / "evals/help/holdout-claims").glob("*.json")))
        raise RunnerError("stop before any provider call")

    monkeypatch.setattr(eval_run, "run_eval", first_call)
    args = argparse.Namespace(
        split="holdout", models=None, max_usd="1", no_retrieval=False, no_judge=True,
        freeze="abc", seed=None, run_id="r1-holdout", retrieval_only=False, draft=False,
    )  # fmt: skip
    with pytest.raises(RunnerError, match="stop"):
        eval_run._execute(args, tmp_path)
    assert seen == [True]
    claim = tmp_path / "evals/help/holdout-claims/r1-holdout.json"
    data = json.loads(claim.read_text(encoding="utf-8"))
    assert data["head"] == "abc123" and data["partition"]["problem_ids"]
    # The same holdout again, under a new run id and a new commit: refused before any call.
    monkeypatch.setattr(eval_run, "_try_git", lambda _root, _args: "def456")
    args.run_id = "r2-holdout"
    with pytest.raises(RunnerError, match="overlaps"):
        eval_run._execute(args, tmp_path)
    assert seen == [True]


def _git(dirty: str = "", head: str = "abc123") -> object:
    def run(args: list[str]) -> str:
        if args[:2] == ["status", "--porcelain"]:
            return dirty
        if args[0] == "rev-parse":
            if args[-1] == "HEAD":
                return head
            return {"abc": "abc123", "abc123": "abc123"}.get(args[-1], "other")
        raise AssertionError(args)

    return run


def test_runner_refuses_holdout_without_freeze() -> None:
    check_freeze("dev", None, git=_git(dirty=" M x"))  # development runs need no freeze
    with pytest.raises(RunnerError, match="--freeze"):
        check_freeze("holdout", None, git=_git())
    with pytest.raises(RunnerError, match="clean"):
        check_freeze("holdout", "abc123", git=_git(dirty=" M src/x.py"))
    with pytest.raises(RunnerError, match="HEAD"):
        check_freeze("holdout", "abc123", git=_git(head="def456"))
    check_freeze("holdout", "abc", git=_git())


def test_main_refuses_holdout_without_freeze(tmp_path: Path) -> None:
    code = main(["--split", "holdout", "--max-usd", "4", "--root", str(tmp_path)])
    assert code == 2


def test_main_rejects_final_split(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["--split", "final", "--max-usd", "4", "--root", str(tmp_path)])


def test_main_refuses_unreviewed_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MATHTUTOR_ANTHROPIC_API_KEY", raising=False)
    case = make_case(reviewed_by="needs_review").model_dump(mode="json")
    for kind, row in (("cases", case), ("retrieval", None)):
        path = tmp_path / "evals" / "help" / kind / "dev.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("" if row is None else json.dumps(row) + "\n", encoding="utf-8")
    code = main(["--split", "dev", "--max-usd", "4", "--root", str(tmp_path)])
    assert code == 2 and "needs_review" in capsys.readouterr().err
