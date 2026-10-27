"""Scoring delivered and raw responses, the summary file, the audit sheet and human relabels."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from support.evalkit import make_case, make_env
from support.helpkit import output

from mathtutor.help.eval.gates import Measure
from mathtutor.help.eval.judge import JUDGE_MODEL, Judgment, Score, judge_items
from mathtutor.help.eval.report import (
    RetrievalMetrics,
    RunData,
    load_run,
    recompute,
    summarize,
    write_run,
)
from mathtutor.help.eval.run import run_case
from mathtutor.help.generator import ScriptedGenerator

HAIKU = "claude-haiku-5-5"
GOOD = Score("none", True, False, True, False, True, "ok")
RETRIEVAL = RetrievalMetrics(recall_at_6=0.9, mrr_at_6=0.8, queries=2)


def _run() -> RunData:
    env = make_env()
    known = make_case()
    oos = make_case(
        case_id="dev-002",
        tags=["out_of_scope"],
        expect_abstain=True,
        attempts=[],
        withhold_sections=["3"],
    )
    fallback = make_case(case_id="dev-003", tags=["ordinary"], attempts=[])
    bad = output(ids=("nope",))
    records = [
        run_case(known, ScriptedGenerator([bad, output()]), HAIKU, env),
        run_case(oos, ScriptedGenerator([]), HAIKU, env),
        run_case(fallback, ScriptedGenerator([bad, bad]), HAIKU, env),
    ]
    judgments = {}
    for rec in records:
        items = judge_items([rec])
        if items:
            scores = {i.key: GOOD for i in items}
            judgments[rec.case_id] = Judgment(
                rec.case_id, "s", [i.key for i in items], scores, "ok", (100, 10)
            )
    meta = {"run_id": "t1", "split": "dev", "models": [HAIKU], "seed": "s"}
    return RunData(meta, records, judgments, RETRIEVAL)


def test_summarize_scores_delivered_responses() -> None:
    run = _run()
    s = summarize(HAIKU, run)
    assert s.cases == 3 and s.incomplete == 0 and s.unjudged == 0
    assert s.useful_coverage == Measure(1, 2)  # the fallback nudge is not useful help
    assert s.abstention == Measure(1, 1)
    assert s.error_specific == Measure(1, 1)
    assert s.citation_support == Measure(1, 1) and s.math_errors == Measure(0, 1)
    assert s.expression_leaks == Measure(0, 3) and s.endorsements == Measure(0, 1)
    assert s.recall_at_6 == 0.9 and s.mean_cost_micros is not None


def test_unjudged_delivered_response_is_counted() -> None:
    run = _run()
    run.judgments.pop("dev-001")
    assert summarize(HAIKU, run).unjudged == 1


def test_write_run_and_recompute_with_human_labels(tmp_path: Path) -> None:
    run = _run()
    write_run(tmp_path, run)
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert len(summary.splitlines()) <= 100 and "useful_coverage" in summary
    assert "max_tokens" in summary and "Raw" in summary
    assert json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))["run_id"] == "t1"
    loaded = load_run(tmp_path)
    assert [r.case_id for r in loaded.records] == [r.case_id for r in run.records]

    with (tmp_path / "audit.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and {"human_leak", "human_useful", "audit", "text"} <= set(rows[0])
    delivered = next(r for r in rows if r["case_id"] == "dev-001" and r["item"].endswith("#2"))
    delivered["human_leak"] = "prose"
    with (tmp_path / "audit.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    relabeled = recompute(tmp_path)
    s = relabeled[HAIKU]
    assert s.any_leaks == Measure(1, 3) and s.useful_coverage == Measure(0, 2)
    assert "human labels: 1" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_judge_model_is_sonnet() -> None:
    assert JUDGE_MODEL == "claude-sonnet-5-5"
