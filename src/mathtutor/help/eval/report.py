"""Scores, the run files and the summary: ``results/<run_id>/{results.jsonl,run.json,
summary.md,audit.csv,audit_key.csv}`` (``results.jsonl`` is git-ignored; the rest is small and
committable). ``audit.csv`` is model-blind; ``audit_key.csv`` maps its items to models.

Delivered scoring follows what the student saw: a delivered reply carries the judge's score
of that raw output; a fallback nudge, abstention or unavailable reply is never useful help.
Raw scoring covers every raw output that parsed as help. Thomas's labels in ``audit.csv``
override the judge's field by field (``--recompute``); his label wins.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from mathtutor.help.config import HelpConfig
from mathtutor.help.eval.cases import RetrievalQuery
from mathtutor.help.eval.gates import (
    GateResult,
    Measure,
    Summary,
    evaluate,
    select_model,
)
from mathtutor.help.eval.judge import Judgment, Score, judge_items
from mathtutor.help.eval.run import CaseRecord, usd
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import ChunkRole

K = 6
BASELINE = "claude-haiku-5-5"
CHALLENGER = "claude-sonnet-5-5"
AUDIT_SHARE = 0.2
SCORE_FIELDS = (
    "leak",
    "addresses_error",
    "endorses_wrong",
    "citations_supported",
    "math_error",
    "useful",
)
LEAKS = ("none", "expression", "prose")
_YES = {"y", "yes", "true", "1"}
_NO = {"n", "no", "false", "0"}

Overrides = dict[tuple[str, str], dict[str, Any]]


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_6: float | None
    mrr_at_6: float | None
    queries: int
    per_query: list[tuple[str, float, float]] = field(default_factory=list)

    @property
    def hit_at_6(self) -> float | None:
        """Share of queries with at least one relevant chunk in the top 6 (reported only)."""
        if not self.per_query:
            return None
        return round(sum(r[1] > 0 for r in self.per_query) / len(self.per_query), 4)


def retrieval_metrics(
    index: Bm25Index, queries: list[RetrievalQuery], cfg: HelpConfig
) -> RetrievalMetrics:
    """Recall@6 (mean per-query share of labeled chunks in the top 6, the gate measure) and
    MRR@6, searched exactly as production does: configured roles and the own-section boost,
    with the query's home section standing in for the problem's section (R29c)."""
    roles = frozenset(ChunkRole(r) for r in cfg.retrieval.roles)
    rows: list[tuple[str, float, float]] = []
    for q in queries:
        hits = index.search(q.text, K, boost_section=q.section, roles=roles)
        top = [h.chunk_id for h in hits]
        relevant = set(q.relevant_ids)
        recall = len(relevant & set(top)) / len(relevant)
        rank = next((n for n, cid in enumerate(top, 1) if cid in relevant), None)
        rows.append((q.query_id, recall, 1.0 / rank if rank else 0.0))
    if not rows:
        return RetrievalMetrics(None, None, 0)
    recall = round(sum(r[1] for r in rows) / len(rows), 4)
    mrr = round(sum(r[2] for r in rows) / len(rows), 4)
    return RetrievalMetrics(recall, mrr, len(rows), rows)


@dataclass
class RunData:
    meta: dict[str, Any]
    records: list[CaseRecord]
    judgments: dict[str, Judgment]
    retrieval: RetrievalMetrics


def _delivered_key(rec: CaseRecord) -> str | None:
    if rec.status != "delivered":
        return None
    raw = next((r for r in rec.raws if r.outcome == "ok"), None)
    return None if raw is None else f"{rec.model}#{raw.call_no}"


def score_of(run: RunData, case_id: str, key: str, overrides: Overrides) -> Score | None:
    judgment = run.judgments.get(case_id)
    base = judgment.scores.get(key) if judgment else None
    human = overrides.get((case_id, key))
    if not human:
        return base
    if base is None:
        if set(SCORE_FIELDS) - set(human):
            return None  # a partial human label cannot stand alone
        return Score(rationale="human", **human)
    return replace(base, **human)


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def summarize(model: str, run: RunData, overrides: Overrides | None = None) -> Summary:
    over = overrides or {}
    recs = [r for r in run.records if r.model == model]
    in_scope = [r for r in recs if not r.expect_abstain]
    expr = anyl = endorse = math_err = cite = judged = useful = specific = unjudged = 0
    for rec in recs:
        key = _delivered_key(rec)
        score = score_of(run, rec.case_id, key, over) if key else None
        if key and score is None:
            unjudged += 1
        if score is None:
            continue
        judged += 1
        expr += score.leak == "expression"
        anyl += score.leak != "none"
        endorse += rec.category == "mistaken_reasoning" and score.endorses_wrong
        math_err += score.math_error
        cite += score.citations_supported
        clean = score.leak == "none"
        useful += (not rec.expect_abstain) and score.useful and clean
        specific += rec.known_error and score.addresses_error and clean
    checked = blocked = 0
    for rec in in_scope:
        for raw in rec.raws:
            if raw.outcome == "ok" or raw.outcome.startswith("invalid_guard_"):
                checked += 1
                s = score_of(run, rec.case_id, f"{rec.model}#{raw.call_no}", over)
                blocked += raw.outcome != "ok" and s is not None and s.leak == "none"
    total = int(run.meta.get("cases", len(recs)))
    costs = [r.cost_micros for r in recs]
    return Summary(
        model=model,
        split=str(run.meta.get("split", "")),
        cases=len(recs),
        expression_leaks=Measure(expr, len(recs)),
        any_leaks=Measure(anyl, len(recs)),
        endorsements=Measure(endorse, sum(r.category == "mistaken_reasoning" for r in recs)),
        math_errors=Measure(math_err, judged),
        citation_support=Measure(cite, judged),
        useful_coverage=Measure(useful, len(in_scope)),
        abstention=Measure(
            sum(r.status == "abstained" for r in recs if r.expect_abstain),
            sum(r.expect_abstain for r in recs),
        ),
        false_blocks=Measure(blocked, checked),
        error_specific=Measure(specific, sum(r.known_error for r in recs)),
        unjudged=unjudged,
        incomplete=max(0, total - len(recs)) + sum(r.budget_stopped for r in recs),
        recall_at_6=run.retrieval.recall_at_6,
        mrr_at_6=run.retrieval.mrr_at_6,
        latency_p95_ms=_p95([r.elapsed_ms for r in recs]),
        mean_cost_micros=(sum(costs) + len(costs) // 2) // len(costs) if costs else None,
    )


def raw_measures(model: str, run: RunData, overrides: Overrides) -> dict[str, Measure]:
    """Every raw output that parsed as help, before guard/citation checks and repair."""
    scores = []
    for rec in (r for r in run.records if r.model == model):
        for item in judge_items([rec]):
            s = score_of(run, rec.case_id, item.key, overrides)
            if s is not None:
                scores.append(s)
    n = len(scores)
    return {
        "expression_leaks": Measure(sum(s.leak == "expression" for s in scores), n),
        "any_leaks": Measure(sum(s.leak != "none" for s in scores), n),
        "math_errors": Measure(sum(s.math_error for s in scores), n),
        "citation_support": Measure(sum(s.citations_supported for s in scores), n),
        "endorsements": Measure(sum(s.endorses_wrong for s in scores), n),
    }


# ---------------------------------------------------------------- files


def _records_jsonl(run: RunData) -> str:
    lines = [json.dumps({"type": "case", **r.to_json()}, ensure_ascii=False) for r in run.records]
    lines += [
        json.dumps({"type": "judgment", **asdict(j)}, ensure_ascii=False)
        for j in run.judgments.values()
    ]
    return "".join(line + "\n" for line in lines)


def _judgment(data: dict[str, Any]) -> Judgment:
    scores = {k: Score(**v) for k, v in data["scores"].items()}
    usage = tuple(data["usage"]) if data.get("usage") is not None else None
    return Judgment(
        data["case_id"],
        data["seed"],
        list(data["order"]),
        scores,
        data["status"],
        usage,
        bool(data.get("billed_unknown", False)),
        dict(data.get("extra", {})),
    )


def load_run(run_dir: Path) -> RunData:
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    records: list[CaseRecord] = []
    judgments: dict[str, Judgment] = {}
    for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines():
        data = json.loads(line)
        kind = data.pop("type")
        if kind == "case":
            records.append(CaseRecord.from_json(data))
        else:
            j = _judgment(data)
            judgments[j.case_id] = j
    r = meta.get("retrieval", {})
    rows = [tuple(x) for x in r.get("per_query", [])]
    metrics = RetrievalMetrics(r.get("recall_at_6"), r.get("mrr_at_6"), r.get("queries", 0), rows)
    return RunData(meta, records, judgments, metrics)


def _strata_sample(run: RunData) -> set[str]:
    """A stratified random 20% of cases by (help type, topic), at least one per stratum."""
    strata: dict[tuple[str, str], list[str]] = {}
    for rec in run.records:
        ids = strata.setdefault((rec.help_type, rec.topic), [])
        if rec.case_id not in ids:
            ids.append(rec.case_id)
    rng = random.Random(f"{run.meta.get('seed', '')}:audit")
    picked: set[str] = set()
    for key in sorted(strata):
        ids = sorted(strata[key])
        picked.update(rng.sample(ids, max(1, round(AUDIT_SHARE * len(ids)))))
    return picked


def _answer_in(text: str, rec: CaseRecord, answers: dict[str, str]) -> bool:
    secret = "".join(answers.get(rec.problem_id, "").split())
    return len(secret) >= 3 and secret in "".join(text.split())


AUDIT_COLUMNS = [
    "audit",
    "case_id",
    "item",
    "delivered",
    "help_type",
    "topic",
    "category",
    *[f"judge_{f}" for f in SCORE_FIELDS],
    "judge_rationale",
    *[f"human_{f}" for f in SCORE_FIELDS],
    "cited_ids",
    "text",
]


def _yn(value: bool) -> str:
    return "y" if value else "n"


KEY_COLUMNS = ["item", "case_id", "model", "key"]


def _blind_ids(run: RunData) -> dict[tuple[str, str], str]:
    """``<case_id>-r<n>`` per raw output, numbered in a seeded shuffled order per case, so the
    audit sheet never shows which model wrote a row (``audit_key.csv`` maps them back)."""
    by_case: dict[str, list[str]] = {}
    for rec in run.records:
        for item in judge_items([rec]):
            by_case.setdefault(rec.case_id, []).append(item.key)
    ids: dict[tuple[str, str], str] = {}
    for case_id, keys in by_case.items():
        order = sorted(keys)
        random.Random(f"{run.meta.get('seed', '')}:audit:{case_id}").shuffle(order)
        for n, key in enumerate(order, 1):
            ids[(case_id, key)] = f"{case_id}-r{n}"
    return ids


def audit_rows(
    run: RunData, answers: dict[str, str]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """One blinded row per judged (or judge-less) raw output, plus key rows mapping each
    blinded ``item`` to its model. ``audit`` says which rows Thomas must label: the random
    sample and every flagged leak, endorsement, math error, guard miss, judge/heuristic
    disagreement or unjudged item."""
    sample = _strata_sample(run)
    blind = _blind_ids(run)
    rows: list[dict[str, str]] = []
    keys: list[dict[str, str]] = []
    for rec in run.records:
        delivered = _delivered_key(rec)
        for item in judge_items([rec]):
            item_id = blind[(rec.case_id, item.key)]
            keys.append(
                {"item": item_id, "case_id": rec.case_id, "model": rec.model, "key": item.key}
            )
            score = score_of(run, rec.case_id, item.key, {})
            flags = []
            if score is None:
                flags.append("unjudged")
            else:
                if score.leak != "none":
                    flags.append(f"leak_{score.leak}")
                if score.endorses_wrong:
                    flags.append("endorses")
                if score.math_error:
                    flags.append("math_error")
                if item.key == delivered and score.leak == "expression":
                    flags.append("guard_miss")
                if score.leak == "none" and _answer_in(item.text, rec, answers):
                    flags.append("heuristic_leak")
            marks = (["random"] if rec.case_id in sample else []) + (
                ["flagged:" + "+".join(flags)] if flags else []
            )
            row = {
                "audit": ";".join(marks),
                "case_id": rec.case_id,
                "item": item_id,
                "delivered": _yn(item.key == delivered),
                "help_type": rec.help_type,
                "topic": rec.topic,
                "category": rec.category,
                "judge_rationale": score.rationale if score else "",
                "cited_ids": " ".join(item.cited_ids),
                "text": item.text,
            }
            for f in SCORE_FIELDS:
                value = getattr(score, f) if score else ""
                row[f"judge_{f}"] = value if isinstance(value, str) else _yn(bool(value))
                row[f"human_{f}"] = ""
            rows.append(row)
    rows.sort(key=lambda r: (r["audit"] == "", r["case_id"], r["item"]))
    keys.sort(key=lambda k: k["item"])
    return rows, keys


def read_human_labels(path: Path, key_path: Path) -> tuple[Overrides, list[dict[str, str]]]:
    """Thomas's labels from the blinded sheet, joined to models through the key file."""
    overrides: Overrides = {}
    with key_path.open(encoding="utf-8", newline="") as fh:
        key_of = {k["item"]: k["key"] for k in csv.DictReader(fh)}
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        labels: dict[str, Any] = {}
        for f in SCORE_FIELDS:
            raw = (row.get(f"human_{f}") or "").strip().lower()
            if not raw:
                continue
            if f == "leak":
                if raw not in LEAKS:
                    raise ValueError(f"audit.csv {row['case_id']}: leak must be one of {LEAKS}")
                labels[f] = raw
            elif raw in _YES or raw in _NO:
                labels[f] = raw in _YES
            else:
                raise ValueError(f"audit.csv {row['case_id']}: {f} must be y or n")
        if labels:
            if row["item"] not in key_of:
                raise ValueError(f"audit.csv: {row['item']} is not in audit_key.csv")
            overrides[(row["case_id"], key_of[row["item"]])] = labels
    return overrides, rows


def agreement(rows: list[dict[str, str]]) -> tuple[Measure, Measure]:
    """Judge-human field agreement on the random sample, and on flagged-only rows."""
    counts = {"random": [0, 0], "targeted": [0, 0]}
    for row in rows:
        group = "random" if "random" in row["audit"] else "targeted"
        for f in SCORE_FIELDS:
            human = (row.get(f"human_{f}") or "").strip().lower()
            judge = row.get(f"judge_{f}", "")
            if human and judge:
                norm = human if f == "leak" else _yn(human in _YES)
                counts[group][0] += norm == judge
                counts[group][1] += 1
    return Measure(*counts["random"]), Measure(*counts["targeted"])


def _models(run: RunData) -> list[str]:
    return list(dict.fromkeys(r.model for r in run.records)) or list(run.meta.get("models", []))


def write_run(
    run_dir: Path, run: RunData, overrides: Overrides | None = None, note: str = ""
) -> dict[str, list[GateResult]]:
    run_dir.mkdir(parents=True, exist_ok=True)
    meta = {**run.meta, "retrieval": asdict(run.retrieval)}
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (run_dir / "results.jsonl").write_text(_records_jsonl(run), encoding="utf-8")
    answers = run.meta.get("answers", {})
    if not (run_dir / "audit.csv").exists():  # never overwrite Thomas's labels
        rows, keys = audit_rows(run, answers)
        for name, columns, data in (
            ("audit.csv", AUDIT_COLUMNS, rows),
            ("audit_key.csv", KEY_COLUMNS, keys),
        ):
            with (run_dir / name).open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
    over = overrides or {}
    summaries = {m: summarize(m, run, over) for m in _models(run)}
    gates = {m: evaluate(s) for m, s in summaries.items()}
    text = render_summary(run, summaries, gates, over, note)
    (run_dir / "summary.md").write_text(text, encoding="utf-8")
    return gates


def recompute(run_dir: Path) -> dict[str, Summary]:
    """Re-score with Thomas's labels from ``audit.csv`` and rewrite ``summary.md``."""
    run = load_run(run_dir)
    overrides, rows = read_human_labels(run_dir / "audit.csv", run_dir / "audit_key.csv")
    rand, targeted = agreement(rows)
    note = (
        f"human labels: {len(overrides)} items; judge-human field agreement, random sample "
        f"{rand}; targeted {targeted}"
    )
    write_run(run_dir, run, overrides, note)
    return {m: summarize(m, run, overrides) for m in _models(run)}


# ---------------------------------------------------------------- summary.md


def _pct(m: Measure) -> str:
    return "n/a" if m.n == 0 else f"{m.k}/{m.n}"


def _cell(group: list[CaseRecord], run: RunData, overrides: Overrides) -> str:
    useful = leaks = 0
    for r in group:
        key = _delivered_key(r)
        s = score_of(run, r.case_id, key, overrides) if key else None
        useful += bool(s and s.useful and s.leak == "none" and not r.expect_abstain)
        leaks += bool(s and s.leak != "none")
    return f"{useful}/{sum(not r.expect_abstain for r in group)} | {leaks}/{len(group)}"


def _breakdown(run: RunData, models: list[str], overrides: Overrides) -> list[str]:
    """Useful/in-scope and any-leak/all per help type, topic, hint level and category."""
    lines = []
    for attr in ("help_type", "topic", "hint_level", "category"):
        for value in sorted({str(getattr(r, attr)) for r in run.records}):
            cells = []
            for x in models:
                group = [r for r in run.records if r.model == x and str(getattr(r, attr)) == value]
                cells.append(_cell(group, run, overrides))
            lines.append(f"| {attr} {value} | " + " | ".join(cells) + " |")
    return lines


def _ops(model: str, recs: list[CaseRecord], s: Summary) -> str:
    status = Counter(r.status for r in recs)
    calls = [c for r in recs for c in r.calls]
    outcomes = Counter(c["outcome"] for c in calls)
    guard = sum(n for o, n in outcomes.items() if o.startswith("invalid_guard_"))
    timeouts = sum(n for o, n in outcomes.items() if o in ("error_timeout", "deadline"))
    total = sum(r.cost_micros for r in recs)
    useful = s.useful_coverage.k
    per_useful = usd(total // useful) if useful else "n/a"
    lat = sorted(r.elapsed_ms for r in recs)
    p50 = lat[len(lat) // 2] if lat else None
    return (
        f"| {model} | {status['delivered']}/{status['abstained']}/{status['fallback']}/"
        f"{status['unavailable']} | {len(calls)} | {outcomes['invalid_max_tokens']} | "
        f"{outcomes['invalid_schema']} | {outcomes['invalid_citation']} | {guard} | {timeouts} | "
        f"{p50}/{s.latency_p95_ms} | {s.mean_cost_micros} | {per_useful} | {usd(total)} |"
    )


def render_summary(
    run: RunData,
    summaries: dict[str, Summary],
    gates: dict[str, list[GateResult]],
    overrides: Overrides,
    note: str = "",
) -> str:
    m = run.meta
    models = list(summaries)
    split = m.get("split", "")
    title = "release gates" if split == "holdout" else "gates on development (selection)"
    out = [
        f"# Help evaluation {m.get('run_id', '')} ({split})",
        "",
        f"- Models: {', '.join(models)}; judge {m.get('judge')} rubric "
        f"{m.get('rubric_version')}, seed `{m.get('seed')}`",
        f"- Config {m.get('config_version')}, prompt {m.get('prompt_version')}, "
        f"versions {m.get('versions')}, tariff {m.get('tariff_version')}",
        f"- Corpus `{m.get('corpus_hash')}`, index `{m.get('index_fingerprint')}`",
        f"- HEAD `{m.get('head')}` dirty={m.get('dirty')} freeze={m.get('freeze')}; "
        f"retrieval {'off' if m.get('no_retrieval') else 'BM25'}",
        f"- Spend {usd(int(m.get('spent_micros', 0)))} of {usd(int(m.get('cap_micros', 0)))} "
        f"USD; stopped: {m.get('stopped')}; cases {m.get('cases')}",
        f"- Mix warnings: {m.get('mix_warnings') or 'none'}",
        f"- {note or 'human labels: none yet (judge labels only)'}",
        "",
        f"## {title.capitalize()} (delivered responses, Wilson 95%)",
        "",
        "| Gate | " + " | ".join(models) + " |",
        "|---|" + "---|" * len(models),
    ]
    names = [g.name for g in next(iter(gates.values()), [])]
    for i, name in enumerate(names):
        cells = [
            f"{'PASS' if gates[x][i].passed else 'FAIL'} {gates[x][i].display}" for x in models
        ]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    out += ["", "Primary (error-specific help, known-error cases): "]
    out[-1] += "; ".join(f"{x} {summaries[x].error_specific}" for x in models)
    if BASELINE in summaries and CHALLENGER in summaries and split == "dev":
        choice = select_model(summaries[BASELINE], summaries[CHALLENGER])
        out += ["", f"**Selection rule:** {choice or 'neither ships'}"]
        out += _paired(run, overrides)
    out += [
        "",
        "## Raw vs delivered",
        "",
        "| Measure | " + " | ".join(f"{x} raw | {x} delivered" for x in models) + " |",
        "|---|" + "---|---|" * len(models),
    ]
    raws = {x: raw_measures(x, run, overrides) for x in models}
    for f in ("expression_leaks", "any_leaks", "endorsements", "math_errors", "citation_support"):
        cells = [f"{raws[x][f]} | {getattr(summaries[x], f)}" for x in models]
        out.append(f"| {f} | " + " | ".join(cells) + " |")
    out += [
        "",
        "## Operational (all requests)",
        "",
        "| Model | deliv/abst/fallb/unav | calls | max_tokens | invalid JSON | invalid cite | "
        "guard blocks | timeouts | p50/p95 ms | mean µ$ | per useful USD | total USD |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for x in models:
        out.append(_ops(x, [r for r in run.records if r.model == x], summaries[x]))
    out += [
        "",
        "## Breakdown (useful/in-scope | any leak/all; hint level is 1 for non-hints)",
        "",
        "| Group | " + " | ".join(f"{x} useful | {x} leaks" for x in models) + " |",
        "|---|" + "---|---|" * len(models),
    ]
    out += _breakdown(run, models, overrides)
    r = run.retrieval
    out += [
        "",
        f"## Retrieval: Recall@6 {r.recall_at_6}, MRR@6 {r.mrr_at_6}, Hit@6 {r.hit_at_6} "
        f"over {r.queries} queries",
        "",
        "Easy level-1 traps are the `category easy_l1_trap` rows above (reported separately).",
        "No learning gains are inferred; intervals are marginal and cases share problems.",
    ]
    return "\n".join(out) + "\n"


def _paired(run: RunData, overrides: Overrides) -> list[str]:
    """Paired primary outcomes on known-error cases (both / Haiku only / Sonnet only / none)."""
    by: dict[str, dict[str, bool]] = {}
    for rec in run.records:
        if not rec.known_error:
            continue
        key = _delivered_key(rec)
        s = score_of(run, rec.case_id, key, overrides) if key else None
        ok = bool(s and s.addresses_error and s.leak == "none")
        by.setdefault(rec.case_id, {})[rec.model] = ok
    pairs = Counter(
        (v.get(BASELINE, False), v.get(CHALLENGER, False))
        for v in by.values()
        if BASELINE in v and CHALLENGER in v
    )
    return [
        f"Paired (known-error cases): both {pairs[(True, True)]}, Haiku only "
        f"{pairs[(True, False)]}, Sonnet only {pairs[(False, True)]}, neither "
        f"{pairs[(False, False)]}"
    ]
