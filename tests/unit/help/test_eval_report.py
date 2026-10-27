"""Scoring delivered and raw responses, the summary file, the audit sheet and human relabels."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from support.evalkit import PROBLEMS, make_case, make_env, make_query, mix_cases
from support.helpkit import CFG, chunk, output

from mathtutor.help.eval.gates import Measure
from mathtutor.help.eval.judge import JUDGE_MODEL, Judgment, Score, judge_items
from mathtutor.help.eval.report import (
    RetrievalMetrics,
    RunData,
    load_run,
    recompute,
    retrieval_metrics,
    summarize,
    write_run,
)
from mathtutor.help.eval.run import run_case
from mathtutor.help.generator import ScriptedGenerator
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import ChunkRole, Corpus

ROLES = frozenset(ChunkRole)

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
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

    # The audit sheet is blind: no model column or model id; the key file maps items back.
    assert "claude" not in (tmp_path / "audit.csv").read_text(encoding="utf-8")
    with (tmp_path / "audit.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and {"human_leak", "human_useful", "audit", "text"} <= set(rows[0])
    assert "model" not in rows[0]
    with (tmp_path / "audit_key.csv").open(encoding="utf-8", newline="") as fh:
        keys = {k["item"]: k for k in csv.DictReader(fh)}
    assert {r["item"] for r in rows} == set(keys)
    delivered = next(r for r in rows if r["case_id"] == "dev-001" and r["delivered"] == "y")
    assert keys[delivered["item"]]["model"] == HAIKU
    delivered["human_leak"] = "prose"
    with (tmp_path / "audit.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    relabeled = recompute(tmp_path)
    s = relabeled[HAIKU]
    assert s.any_leaks == Measure(1, 3) and s.useful_coverage == Measure(0, 2)
    assert "human labels: 1" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def _two_model_run(cases: list) -> RunData:  # noqa: ANN001
    env = make_env()
    records, judgments = [], {}
    for case in cases:
        recs = [run_case(case, ScriptedGenerator([output()]), m, env) for m in (HAIKU, SONNET)]
        records += recs
        items = judge_items(recs)
        if items:
            scores = {i.key: GOOD for i in items}
            judgments[case.case_id] = Judgment(
                case.case_id, "s", [i.key for i in items], scores, "ok", (100, 10)
            )
    meta = {"run_id": "t2", "split": "dev", "models": [HAIKU, SONNET], "seed": "s"}
    return RunData(meta, records, judgments, RETRIEVAL)


def test_summary_fits_100_lines_on_a_full_dev_run(tmp_path: Path) -> None:
    problems = [(p.id, p.topic) for p in PROBLEMS.values() if p.answer.kind == "expression"]
    run = _two_model_run(mix_cases("dev", problems))
    write_run(tmp_path, run)
    lines = (tmp_path / "summary.md").read_text(encoding="utf-8").splitlines()
    assert len(run.records) == 72 and len(lines) <= 100


def test_paired_table_uses_human_labels(tmp_path: Path) -> None:
    run = _two_model_run([make_case()])
    write_run(tmp_path, run)
    assert "both 1, Haiku only 0" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    with (tmp_path / "audit_key.csv").open(encoding="utf-8", newline="") as fh:
        haiku_item = next(k["item"] for k in csv.DictReader(fh) if k["model"] == HAIKU)
    with (tmp_path / "audit.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        if row["item"] == haiku_item:
            row["human_addresses_error"] = "n"
    with (tmp_path / "audit.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    recompute(tmp_path)
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "both 0, Haiku only 0, Sonnet only 1" in text


def test_judge_model_is_sonnet() -> None:
    assert JUDGE_MODEL == "claude-sonnet-5-5"


def test_retrieval_metrics_boost_the_home_section_like_production() -> None:
    # The 3.5 chunk scores a little higher alone; the home-section boost (x1.3) flips it.
    chunks = [
        chunk("c-other", "slope slope tangent", section="3.5"),
        chunk("c-home", "slope tangent line"),
    ]
    index = Bm25Index.build(Corpus({c.chunk_id: c for c in chunks}, "h", "e"), CFG.retrieval)
    unboosted = index.search("slope tangent", 6, boost_section=None, roles=ROLES)
    assert unboosted[0].chunk_id == "c-other"
    query = make_query(text="slope tangent", section="3.6", relevant_ids=["c-home"])
    assert retrieval_metrics(index, [query], CFG).mrr_at_6 == 1.0
