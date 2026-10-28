"""The committed help cases and retrieval queries meet 02-gates and point at real data."""

from __future__ import annotations

from support.helpkit import CFG, CONFUSIONS, ROOT

from mathtutor.content.loader import load_bundle
from mathtutor.help.eval.cases import (
    NEEDS_REVIEW,
    REVIEWERS,
    check_bank,
    check_grouping,
    check_query_grouping,
    load_split,
)
from mathtutor.help.eval.gates import check_mix
from mathtutor.retrieval.corpus import ChunkRole, load_corpus

BANK = {
    p.id: p for p in load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
}
DEV_CASES, DEV_QUERIES = load_split(ROOT, "dev")
HOLD_CASES, HOLD_QUERIES = load_split(ROOT, "holdout")


def test_drafted_splits_grouped_by_problem() -> None:
    assert len(DEV_CASES) == 42 and len(HOLD_CASES) == 24
    assert check_grouping(DEV_CASES, HOLD_CASES, BANK) == []


def test_drafted_case_mix_matches_gates() -> None:
    assert check_mix(DEV_CASES, "dev") == []
    assert check_mix(HOLD_CASES, "holdout") == []


def test_every_case_problem_and_confusion_exists() -> None:
    assert check_bank(DEV_CASES + HOLD_CASES, BANK, CONFUSIONS) == []


def test_every_relevant_id_exists_and_is_retrievable() -> None:
    corpus = load_corpus(ROOT / "content" / "corpus")
    roles = {ChunkRole(r) for r in CFG.retrieval.roles}
    for q in DEV_QUERIES + HOLD_QUERIES:
        for cid in q.relevant_ids:
            assert cid in corpus.chunks, (q.query_id, cid)
            assert corpus.chunks[cid].role in roles, (q.query_id, cid)


def test_drafted_queries_split_by_section() -> None:
    assert len(DEV_QUERIES) == 28 and len(HOLD_QUERIES) == 12
    assert check_query_grouping(DEV_QUERIES, HOLD_QUERIES) == []
    chapters = {q.section.split(".")[0] for q in HOLD_QUERIES}
    assert chapters == {"1", "2", "3", "4", "5", "6"}


def test_rows_are_awaiting_or_have_review() -> None:
    for row in DEV_CASES + HOLD_CASES + DEV_QUERIES + HOLD_QUERIES:
        assert row.reviewed_by == NEEDS_REVIEW or row.reviewed_by in REVIEWERS


def test_no_evidence_cases_withhold_the_derivative_chapters() -> None:
    for case in DEV_CASES + HOLD_CASES:
        if case.expect_abstain:
            assert {"3", "4", "5", "6"} <= set(case.withhold_sections), case.case_id
