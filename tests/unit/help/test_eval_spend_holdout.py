"""Durable evaluation spend (review C1-R9) and one-shot holdout claims (review C1-R4).

Synthetic cases, a scripted provider and fake pools only: no key, no network, and never the
real holdout files or claims.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from support.evalkit import CONFUSIONS, make_case, make_env, make_query
from support.helpkit import CFG, CONTENT, FakePool, output

from mathtutor.help.eval import run as runner
from mathtutor.help.eval.errors import RunnerError
from mathtutor.help.eval.holdout import CLAIMS_DIR, LOCK, check_unused, claim, partition_of
from mathtutor.help.eval.run import main, parse_usd, run_eval
from mathtutor.help.eval.spend import JOURNAL, SpendCounter, SpendJournal, total_spend
from mathtutor.help.generator import GenerationRequest, ScriptedGenerator

HAIKU = "claude-haiku-5-5"


# -- spend journal ---------------------------------------------------------------------------


def test_journal_keeps_open_reservation_at_worst_case(tmp_path: Path) -> None:
    run = tmp_path / "evals/help/results/r1"
    run.mkdir(parents=True)
    spend = SpendCounter(CFG, parse_usd("4"), SpendJournal(run / JOURNAL))
    spend.settle(spend.reserve("help", HAIKU, 1_300), 350)
    spend.reserve("help", HAIKU, 1_300)  # sent, then the process died
    (total,) = total_spend(tmp_path / "evals/help/results").runs
    assert (total.settled_micros, total.open_micros, total.total_micros) == (350, 1_300, 1_650)


def test_torn_last_line_keeps_the_reservation_open(tmp_path: Path) -> None:
    run = tmp_path / "r1"
    run.mkdir()
    journal = SpendJournal(run / JOURNAL)
    journal.append({"event": "reserve", "id": 1, "kind": "help", "model": HAIKU, "worst": 1_300})
    with (run / JOURNAL).open("a", encoding="utf-8") as fh:
        fh.write('{"event": "settle", "id": 1, "mic')  # crash mid-write
    assert total_spend(tmp_path).total_micros == 1_300


class _Interrupting(ScriptedGenerator):
    """Raises KeyboardInterrupt inside the call (after dispatch), like Ctrl-C mid-request."""

    def generate(self, req: GenerationRequest):  # type: ignore[no-untyped-def]
        self.requests.append(req)
        raise KeyboardInterrupt


def test_interrupt_during_a_call_leaves_its_reservation(tmp_path: Path) -> None:
    run = tmp_path / "r1"
    run.mkdir()
    spend = SpendCounter(CFG, parse_usd("4"), SpendJournal(run / JOURNAL))
    with pytest.raises(KeyboardInterrupt):
        run_eval([make_case()], [HAIKU], _Interrupting([]), make_env(), spend, judge=None)
    assert total_spend(tmp_path).total_micros == 1_300  # Haiku's worst case


def test_interrupt_during_judging_leaves_the_judge_reservation(tmp_path: Path) -> None:
    run = tmp_path / "r1"
    run.mkdir()
    spend = SpendCounter(CFG, parse_usd("4"), SpendJournal(run / JOURNAL))

    def judge(*_args: object) -> object:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_eval(
            [make_case()], [HAIKU], ScriptedGenerator([output()]), make_env(), spend, judge=judge
        )
    assert total_spend(tmp_path).total_micros == 350 + 64_000


def _offline(monkeypatch: pytest.MonkeyPatch, generator: ScriptedGenerator, cases: list) -> None:
    """``_execute`` with synthetic data, a scripted provider and fake pools (review probe)."""
    env = make_env()
    monkeypatch.setattr("mathtutor.help.eval.cases.load_split", lambda *_: (cases, [make_query()]))
    monkeypatch.setattr("mathtutor.content.loader.load_bundle", lambda *_: CONTENT)
    monkeypatch.setattr("mathtutor.help.context.load_confusions", lambda *_: CONFUSIONS)
    monkeypatch.setattr("mathtutor.retrieval.corpus.load_corpus", lambda *_: env.corpus)
    monkeypatch.setattr("mathtutor.help.eval.judge.load_rubric", lambda *_: "offline rubric")
    monkeypatch.setattr("mathtutor.help.generator.ClaudeGenerator", lambda *_: generator)

    class OfflinePool(FakePool):
        def close(self) -> None:
            pass

    monkeypatch.setattr("mathtutor.verify.pool.VerifierPool", lambda **_: OfflinePool())
    monkeypatch.setattr(runner, "API_KEY_ENV", "C1_TEST_DUMMY_KEY")  # never the real key
    monkeypatch.setenv("C1_TEST_DUMMY_KEY", "offline-placeholder")


def _args(run_id: str, split: str = "dev", freeze: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        draft=False, retrieval_only=False, split=split, max_usd="4", models=CFG.model,
        run_id=run_id, seed="t", no_retrieval=False, no_judge=True, freeze=freeze,
    )  # fmt: skip


def test_interrupted_dev_run_keeps_its_spend_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    generator = ScriptedGenerator([output(), output()])
    _offline(monkeypatch, generator, [make_case(), make_case(case_id="dev-002")])
    original = runner.run_eval

    def interrupted(*args: object, **kwargs: object) -> object:
        def stop(_line: str) -> None:
            raise KeyboardInterrupt

        kwargs["log"] = stop
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(runner, "run_eval", interrupted)
    with pytest.raises(KeyboardInterrupt):
        runner._execute(_args("interrupted"), tmp_path)  # noqa: SLF001
    assert len(generator.requests) == 1
    assert not (tmp_path / "evals/help/results/interrupted/run.json").exists()
    assert total_spend(tmp_path / "evals/help/results").total_micros == 350
    assert main(["--spent", "--root", str(tmp_path)]) == 0
    assert "total: 0.000350 USD over 1 runs" in capsys.readouterr().out


def test_run_id_is_never_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    generator = ScriptedGenerator([output()])
    _offline(monkeypatch, generator, [make_case()])
    (tmp_path / "evals/help/results/r1").mkdir(parents=True)
    with pytest.raises(RunnerError, match="already used"):
        runner._execute(_args("r1"), tmp_path)  # noqa: SLF001
    assert generator.requests == []


# -- holdout claims --------------------------------------------------------------------------


def _holdout(problems: list[str], prefix: str = "h", chunks: tuple[str, ...] = ("c1",)) -> object:
    cases = [
        make_case(case_id=f"{prefix}-{i}", split="holdout", problem_id=p)
        for i, p in enumerate(problems)
    ]
    queries = [make_query(query_id=f"rq-{prefix}", split="holdout", relevant_ids=list(chunks))]
    return partition_of(cases, queries)


def test_used_holdout_stays_used_on_a_new_commit(tmp_path: Path) -> None:
    used = _holdout(["p1", "p2"])
    claim(tmp_path, used, "r1", head="old", freeze="old")
    with pytest.raises(RunnerError, match="overlaps"):
        claim(tmp_path, used, "r2", head="new", freeze="new")


def test_reordered_or_reworded_cases_on_used_problems_are_refused(tmp_path: Path) -> None:
    claim(tmp_path, _holdout(["p1", "p2"]), "r1", head="a", freeze="a")
    with pytest.raises(RunnerError, match="problem_ids: p1"):
        check_unused(tmp_path, _holdout(["p2", "p1"], prefix="new", chunks=("c9",)))


def test_shared_query_chunks_are_refused(tmp_path: Path) -> None:
    claim(tmp_path, _holdout(["p1"]), "r1", head="a", freeze="a")
    with pytest.raises(RunnerError, match="chunk_ids: c1"):
        check_unused(tmp_path, _holdout(["p9"], prefix="new", chunks=("c1",)))


def test_disjoint_holdout_may_run(tmp_path: Path) -> None:
    claim(tmp_path, _holdout(["p1"]), "r1", head="a", freeze="a")
    claim(tmp_path, _holdout(["p9"], prefix="new", chunks=("c9",)), "r2", head="a", freeze="a")


def test_claimed_run_results_are_not_legacy(tmp_path: Path) -> None:
    claim(tmp_path, _holdout(["p1"]), "r1", head="a", freeze="a")
    out = tmp_path / "evals/help/results/r1"
    out.mkdir(parents=True)
    (out / "run.json").write_text(json.dumps({"split": "holdout"}), "utf-8")
    check_unused(tmp_path, _holdout(["p9"], prefix="new", chunks=("c9",)))


def test_held_lock_refuses_a_second_runner(tmp_path: Path) -> None:
    (tmp_path / CLAIMS_DIR).mkdir(parents=True)
    (tmp_path / CLAIMS_DIR / LOCK).touch()
    with pytest.raises(RunnerError, match="holds"):
        claim(tmp_path, _holdout(["p1"]), "r1", head="a", freeze="a")
    assert not list((tmp_path / CLAIMS_DIR).glob("*.json"))


def test_simultaneous_claims_admit_exactly_one(tmp_path: Path) -> None:
    used = _holdout(["p1"])
    barrier = threading.Barrier(8)
    won: list[str] = []
    lost: list[str] = []

    def race(i: int) -> None:
        barrier.wait()
        try:
            claim(tmp_path, used, f"r{i}", head="a", freeze="a")
            won.append(f"r{i}")
        except RunnerError:
            lost.append(f"r{i}")

    threads = [threading.Thread(target=race, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(won) == 1 and len(lost) == 7
    assert len(list((tmp_path / CLAIMS_DIR).glob("*.json"))) == 1
