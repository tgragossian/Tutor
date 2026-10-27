"""Run help cases through the production pipeline, judge them and write the report.

``python -m mathtutor.help.eval.run --split dev --models claude-haiku-5-5,claude-sonnet-5-5
--max-usd 4`` (Thomas runs it with his key; never CI). Each case builds its context with the
pure ``assemble_context``/``match_misconception`` (ruling R3) and calls ``HelpPipeline.run``
directly (ruling R4) with a real one-worker guard pool, so retrieval, prompt, repair and
guard are the production path. Spend is counted here in integer micro-USD with the ledger's
tariff and worst-case formula: a call (help or judge) is made only if the spend so far plus
its worst case stays within ``--max-usd``. The holdout needs ``--freeze <commit>`` on a
clean tree at that commit, and writes ``started.json`` before its first provider call, so a
crashed holdout still counts as run. Unreviewed cases or queries are refused.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from mathtutor.application.practice import Pool
from mathtutor.content.schema import ChoiceAnswer, Problem
from mathtutor.domain import VerdictStatus
from mathtutor.help.config import DEFAULT_CONFIG_PATH, HelpConfig, worst_case_micros
from mathtutor.help.context import AttemptLine, Confusion, assemble_context, match_misconception
from mathtutor.help.eval.cases import HelpCase, confusion_label
from mathtutor.help.eval.judge import (
    JUDGE_MAX_INPUT_TOKENS,
    JUDGE_MAX_OUTPUT_TOKENS,
    JUDGE_MODEL,
    Judgment,
)
from mathtutor.help.generator import GenerationRequest, GenerationResult, Generator
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.help.ledger import micros_for
from mathtutor.help.pipeline import HelpPipeline, answer_latex
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import Corpus

API_KEY_ENV = "MATHTUTOR_ANTHROPIC_API_KEY"
MICROS = 1_000_000
STARTED_MARKER = "started.json"  # holdout only; see ``mark_started``
GUARD_MEMORY_MB = 384  # 01-pinned-values: the guard pool's memory limit


class RunnerError(Exception):
    """A precondition of the run does not hold; the message says which."""


@dataclass
class EvalEnv:
    cfg: HelpConfig
    problems: dict[str, Problem]
    corpus: Corpus
    confusions: dict[str, list[Confusion]]
    grading_pool: Pool
    guard_pool: Pool
    retrieval: bool = True
    clock: Callable[[], float] = time.monotonic
    _indexes: dict[tuple[str, ...], tuple[Corpus, Bm25Index]] = field(default_factory=dict)
    _notes: dict[str, str | None] = field(default_factory=dict)

    def index_for(self, withhold: Sequence[str]) -> tuple[Corpus, Bm25Index]:
        """The case's corpus and index: everything, minus withheld sections/chapters; empty
        with ``retrieval`` off (``--no-retrieval``)."""
        key = ("<none>",) if not self.retrieval else tuple(sorted(withhold))
        if key not in self._indexes:
            if not self.retrieval:
                kept: dict[str, Any] = {}
            else:
                kept = {
                    cid: c
                    for cid, c in self.corpus.chunks.items()
                    if c.section not in key and c.section.split(".")[0] not in key
                }
            corpus = Corpus(kept, self.corpus.corpus_hash, self.corpus.edition)
            self._indexes[key] = (corpus, Bm25Index.build(corpus, self.cfg.retrieval))
        return self._indexes[key]


@dataclass(frozen=True)
class RawOutput:
    call_no: int
    text: str | None
    stop_reason: str
    outcome: str


@dataclass
class CaseRecord:
    """Everything one case produced for one model: each raw call output and the delivered
    result, so raw and delivered scores are reported separately (spec 08)."""

    case_id: str
    split: str
    model: str
    problem_id: str
    topic: str
    help_type: str
    hint_level: int
    category: str
    known_error: bool
    expect_abstain: bool
    status: str
    reason: str
    text: str | None
    cited_ids: list[str]
    retrieved_ids: list[str]
    top_section: str | None
    calls: list[dict[str, Any]]
    raws: list[RawOutput]
    guard: list[dict[str, Any]]
    misconception_matched: bool
    elapsed_ms: int
    cost_micros: int
    budget_stopped: bool = False

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CaseRecord:
        raws = [RawOutput(**r) for r in data["raws"]]
        return cls(**{**data, "raws": raws})


class RecordingGenerator:
    """Passes each request through and keeps every reply, for the raw outputs."""

    def __init__(self, inner: Generator) -> None:
        self.inner = inner
        self.replies: list[GenerationResult] = []

    def generate(self, req: GenerationRequest) -> GenerationResult:
        reply = self.inner.generate(req)
        self.replies.append(reply)
        return reply


def call_micros(
    cfg: HelpConfig,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    billed_unknown: bool = False,
) -> int:
    """What one call cost, as the ledger settles it; unknown usage that may have been billed
    counts at the worst case, a definite failure at 0."""
    if input_tokens is not None and output_tokens is not None:
        return micros_for(cfg, model, input_tokens, output_tokens)
    return worst_case_micros(cfg, model) if billed_unknown else 0


def judge_cfg(cfg: HelpConfig) -> HelpConfig:
    """The help config with the judge's token limits, for the same worst-case formula."""
    return cfg.model_copy(
        update={
            "max_input_tokens": JUDGE_MAX_INPUT_TOKENS,
            "max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
        }
    )


def _attempts(case: HelpCase, problem: Problem) -> tuple[list[AttemptLine], str | None]:
    """Case attempts as consumed wrong attempts; a choice attempt shows its option's LaTeX,
    as ``build_context`` does."""
    answer = problem.answer
    if isinstance(answer, ChoiceAnswer):
        latex = {c.id: c.latex for c in answer.choices}
        lines = [AttemptLine(latex[a], VerdictStatus.INCORRECT) for a in case.attempts]
        return lines, case.attempts[-1] if case.attempts else None
    return [AttemptLine(a, VerdictStatus.INCORRECT) for a in case.attempts], None


def run_case(
    case: HelpCase,
    generator: Generator,
    model: str,
    env: EvalEnv,
    *,
    may_call: Callable[[int], bool] | None = None,
) -> CaseRecord:
    """One case through ``HelpPipeline.run`` with ``model``, as production would serve it."""
    problem = env.problems[case.problem_id]
    attempts, chosen = _attempts(case, problem)
    if case.case_id not in env._notes:  # model-independent: match once per case
        latest = attempts[-1] if attempts else None
        env._notes[case.case_id] = match_misconception(problem, latest, chosen, env.grading_pool)
    note = env._notes[case.case_id]
    ctx = assemble_context(problem, attempts, case.hint_level, note)
    label = confusion_label(case, problem, env.confusions)
    cfg = env.cfg.model_copy(update={"model": model})
    corpus, index = env.index_for(case.withhold_sections)
    recorder = RecordingGenerator(generator)
    guard = LeakGuard(env.guard_pool, cfg.guard, env.clock)
    pipeline = HelpPipeline(cfg, corpus, index, recorder, guard, env.clock)
    refused: list[int] = []

    def ask(n: int) -> bool:
        ok = may_call is None or may_call(n)
        if not ok:
            refused.append(n)
        return ok

    started = env.clock()
    result = pipeline.run(
        ctx, case.help_type, label, problem.answer, started + cfg.deadline_s, may_call=ask
    )
    elapsed_ms = round((env.clock() - started) * 1000)
    replies = iter(recorder.replies)
    raws: list[RawOutput] = []
    for call in result.calls:
        if call.outcome.startswith("error_"):
            continue
        reply = next(replies)
        raws.append(RawOutput(call.call_no, reply.text, reply.stop_reason, call.outcome))
    # Charged at the requested model's tariff, as the ledger reserves and settles it.
    cost = sum(
        call_micros(cfg, model, c.input_tokens, c.output_tokens, _unknown_usage(asdict(c)))
        for c in result.calls
    )
    return CaseRecord(
        case_id=case.case_id,
        split=case.split,
        model=model,
        problem_id=case.problem_id,
        topic=problem.topic,
        help_type=case.help_type,
        hint_level=case.hint_level,
        category=case.category,
        known_error=case.known_error,
        expect_abstain=case.expect_abstain,
        status=result.status.value,
        reason=result.reason,
        text=result.text,
        cited_ids=list(result.cited_ids),
        retrieved_ids=list(result.retrieved_ids),
        top_section=result.top_section,
        calls=[asdict(c) for c in result.calls],
        raws=raws,
        guard=[
            {"decision": g.decision, "reason": g.reason, "foreign": g.foreign} for g in result.guard
        ],
        misconception_matched=note is not None,
        elapsed_ms=elapsed_ms,
        cost_micros=cost,
        budget_stopped=bool(refused),
    )


class SpendCounter:
    """The run's own spend, in integer micro-USD, against ``cap_micros``."""

    def __init__(self, cfg: HelpConfig, cap_micros: int) -> None:
        self.help_cfg = cfg
        self.judge_cfg = judge_cfg(cfg)
        self.cap_micros = cap_micros
        self.spent_micros = 0

    def worst_call(self, model: str) -> int:
        return worst_case_micros(self.help_cfg, model)

    def worst_judge(self) -> int:
        return worst_case_micros(self.judge_cfg, JUDGE_MODEL)

    def allows(self, worst: int) -> bool:
        return self.spent_micros + worst <= self.cap_micros

    def charge(
        self,
        cfg: HelpConfig,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        billed_unknown: bool = False,
    ) -> int:
        """``cfg`` (``help_cfg`` or ``judge_cfg``) gives the token limits of the worst case."""
        micros = call_micros(cfg, model, input_tokens, output_tokens, billed_unknown)
        self.spent_micros += micros
        return micros


def usd(micros: int) -> str:
    sign = "-" if micros < 0 else ""
    micros = abs(micros)
    return f"{sign}{micros // MICROS}.{micros % MICROS:06d}"


def parse_usd(text: str) -> int:
    """``--max-usd`` as integer micro-USD: positive, at most six decimals."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not an amount: {text!r}") from None
    micros = value * MICROS
    if value <= 0 or micros != micros.to_integral_value():
        raise ValueError(f"amount must be positive with at most 6 decimals: {text!r}")
    return int(micros)


@dataclass
class EvalResult:
    records: list[CaseRecord]
    judgments: dict[str, Judgment]
    stopped: str | None


JudgeFn = Callable[[HelpCase, list[CaseRecord]], Judgment]


def run_eval(
    cases: list[HelpCase],
    models: list[str],
    generator: Generator,
    env: EvalEnv,
    spend: SpendCounter,
    *,
    judge: JudgeFn | None,
    log: Callable[[str], None] = print,
) -> EvalResult:
    """Every case on every model, then its judgment; stops before any call whose worst case
    would take the spend past the cap."""
    records: list[CaseRecord] = []
    judgments: dict[str, Judgment] = {}
    stopped: str | None = None
    for case in cases:
        done: list[CaseRecord] = []
        for model in models:
            worst = spend.worst_call(model)
            if not spend.allows(worst):
                stopped = f"spend cap reached before {case.case_id} on {model}"
                break

            # Before call n, this case's n - 1 earlier calls are still unsettled: they count at
            # their worst case, like the ledger's reservations, plus the new call's worst case.
            def may_call(n: int, w: int = worst) -> bool:
                return spend.allows(n * w)

            rec = run_case(case, generator, model, env, may_call=may_call)
            for call in rec.calls:
                tokens = (call["input_tokens"], call["output_tokens"])
                spend.charge(spend.help_cfg, model, *tokens, _unknown_usage(call))
            done.append(rec)
            if rec.budget_stopped:
                stopped = f"spend cap reached during {case.case_id} on {model}"
                break
        records.extend(done)
        if stopped is None and judge is not None:
            if not spend.allows(spend.worst_judge()):
                stopped = f"spend cap reached before judging {case.case_id}"
            else:
                j = judge(case, done)
                judgments[case.case_id] = j
                if j.usage is not None:  # a reply came back: missing usage counts at worst
                    unknown = None in j.usage or j.billed_unknown
                    spend.charge(spend.judge_cfg, JUDGE_MODEL, *j.usage, unknown)
                elif j.billed_unknown:
                    spend.charge(spend.judge_cfg, JUDGE_MODEL, None, None, True)
        statuses = " ".join(f"{r.model.split('-')[1]}={r.status}" for r in done)
        log(
            f"{case.case_id}: {statuses} | spent {usd(spend.spent_micros)} of "
            f"{usd(spend.cap_micros)} USD"
        )
        if stopped is not None:
            log(f"STOPPED: {stopped}")
            break
    return EvalResult(records, judgments, stopped)


def _unknown_usage(call: dict[str, Any]) -> bool:
    """A reply that came back was billed: missing token counts are charged at worst case."""
    if call["billed_unknown"]:
        return True
    missing = call["input_tokens"] is None or call["output_tokens"] is None
    return missing and not str(call["outcome"]).startswith("error_")


def _git(root: Path, args: list[str]) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def check_freeze(
    split: str,
    freeze: str | None,
    root: Path = Path("."),
    git: Callable[[list[str]], str] | None = None,
) -> None:
    """The holdout runs once, frozen: ``--freeze <commit>``, a clean tree at ``root``, HEAD at
    the commit, and no earlier holdout results for that commit."""
    if split != "holdout":
        return
    if not freeze:
        raise RunnerError("the holdout split needs --freeze <commit>")
    if git is None:

        def git(args: list[str]) -> str:
            return _git(root, args)

    if git(["status", "--porcelain"]):
        raise RunnerError("the holdout needs a clean working tree (commit or drop changes)")
    head = git(["rev-parse", "HEAD"])
    if head != git(["rev-parse", freeze]):
        raise RunnerError(f"HEAD is not the frozen commit {freeze}")
    results = root / "evals" / "help" / "results"
    for path in sorted(results.glob("*/run.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta.get("split") == "holdout" and meta.get("head") == head:
            raise RunnerError(
                f"the holdout already ran at {head[:12]} ({path.parent.name}); it runs once"
            )
    for path in sorted(results.glob(f"*/{STARTED_MARKER}")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta.get("split") == "holdout" and meta.get("head") == head:
            raise RunnerError(
                f"the holdout already started at {head[:12]} ({path.parent.name}); it runs once,"
                " even if it never finished"
            )


def mark_started(out: Path, freeze: str, head: str) -> None:
    """Record that the holdout started at ``head`` (written before the first provider call):
    a run that crashes before ``run.json`` still counts as the one run for that commit."""
    out.mkdir(parents=True, exist_ok=True)
    marker = {"split": "holdout", "freeze": freeze, "head": head}
    (out / STARTED_MARKER).write_text(json.dumps(marker) + "\n", encoding="utf-8")


def _execute(args: argparse.Namespace, root: Path) -> int:
    from mathtutor.content.loader import load_bundle
    from mathtutor.help.config import load_help_config
    from mathtutor.help.context import load_confusions
    from mathtutor.help.eval import report  # report imports this module
    from mathtutor.help.eval.cases import check_bank, load_split, unreviewed
    from mathtutor.help.eval.gates import check_mix
    from mathtutor.help.eval.judge import RUBRIC_VERSION, judge_case, load_rubric
    from mathtutor.help.generator import ClaudeGenerator
    from mathtutor.retrieval.corpus import load_corpus
    from mathtutor.verify.pool import VerifierPool

    if args.draft and not args.retrieval_only:
        raise RunnerError("--draft only works with --retrieval-only")
    cases, queries = load_split(root, args.split)
    pending = unreviewed(cases) + unreviewed(queries)
    if pending and not args.draft:
        raise RunnerError(
            f"{len(pending)} rows are not reviewed (needs_review), e.g. {', '.join(pending[:5])}; "
            "set reviewed_by to tg after review"
        )
    cfg = load_help_config(DEFAULT_CONFIG_PATH)
    bundle = load_bundle(root / "content" / "compiled" / "problems.json").bundle
    problems = {p.id: p for p in bundle.problems}
    confusions = load_confusions(root / "content" / "help" / "confusions.json")
    corpus = load_corpus(root / "content" / "corpus")
    errors = check_bank(cases, problems, confusions)
    errors += [
        f"{q.query_id}: unknown chunk {i}"
        for q in queries
        for i in q.relevant_ids
        if i not in corpus.chunks
    ]
    if errors:
        raise RunnerError("; ".join(errors[:10]))
    warnings = check_mix(cases, args.split)
    for w in warnings:
        print(f"warning: {w}")
    index = Bm25Index.build(corpus, cfg.retrieval)
    metrics = report.retrieval_metrics(index, queries, cfg)
    print(
        f"retrieval {args.split}{' (DRAFT labels)' if pending else ''}: "
        f"Recall@6 {metrics.recall_at_6} MRR@6 {metrics.mrr_at_6} Hit@6 {metrics.hit_at_6} "
        f"over {metrics.queries} queries"
    )
    if args.retrieval_only:
        return 0
    if args.max_usd is None:
        raise RunnerError("--max-usd is required")
    cap = parse_usd(args.max_usd)
    models = (args.models or cfg.model).split(",")
    for model in models:
        if model not in cfg.tariffs:
            raise RunnerError(f"no tariff for model {model}")
    key = os.environ.get(API_KEY_ENV, "")
    if not key:
        raise RunnerError(f"{API_KEY_ENV} is not set")
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + f"-{args.split}"
    seed = args.seed or run_id
    rubric = load_rubric(root / "evals" / "help" / "rubric" / f"{RUBRIC_VERSION}.md")
    generator = ClaudeGenerator(key)
    g = cfg.guard
    grading = VerifierPool(size=1)
    guard = VerifierPool(
        size=1,
        deadline_s=g.pool_deadline_s,
        queue_max=g.queue_max,
        queue_wait_s=g.queue_wait_s,
        memory_mb=GUARD_MEMORY_MB,
    )
    out = root / "evals" / "help" / "results" / run_id
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        if args.split == "holdout":  # before any provider call: the holdout runs once
            mark_started(out, args.freeze, _try_git(root, ["rev-parse", "HEAD"]))
        env = EvalEnv(cfg, problems, corpus, confusions, grading, guard, not args.no_retrieval)
        spend = SpendCounter(cfg, cap)

        def judge(case: HelpCase, recs: list[CaseRecord]) -> Judgment:
            return judge_case(case, recs, env, generator, rubric, seed=seed)

        result = run_eval(
            cases, models, generator, env, spend, judge=None if args.no_judge else judge
        )
    finally:
        grading.close()
        guard.close()
    meta: dict[str, Any] = {
        "run_id": run_id,
        "split": args.split,
        "models": models,
        "seed": seed,
        "started": started,
        "no_retrieval": bool(args.no_retrieval),
        "judge": None if args.no_judge else JUDGE_MODEL,
        "rubric_version": RUBRIC_VERSION,
        "config_version": cfg.version,
        "prompt_version": cfg.prompt_version,
        "versions": {
            "schema": cfg.schema_version,
            "parser": cfg.parser_version,
            "guard": cfg.guard_version,
        },
        "tariff_version": cfg.tariff_version,
        "tariffs": {m: t.model_dump() for m, t in cfg.tariffs.items()},
        "corpus_hash": corpus.corpus_hash,
        "index_fingerprint": index.fingerprint,
        "head": _try_git(root, ["rev-parse", "HEAD"]),
        "dirty": bool(_try_git(root, ["status", "--porcelain"])),
        "freeze": args.freeze,
        "cap_micros": cap,
        "spent_micros": spend.spent_micros,
        "stopped": result.stopped,
        "cases": len(cases),
        "mix_warnings": warnings,
        # bank answers (public in the repo), for the audit's answer-substring heuristic
        "answers": {c.problem_id: answer_latex(problems[c.problem_id].answer) for c in cases},
    }
    run = report.RunData(meta, result.records, result.judgments, metrics)
    gates = report.write_run(out, run)
    print(f"wrote {out}; spent {usd(spend.spent_micros)} USD")
    failed = [f"{m}:{r.name}" for m, results in gates.items() for r in results if not r.passed]
    print("gates: all passed" if not failed else "gates failed: " + ", ".join(failed))
    return 1 if failed and args.split == "holdout" else 0


def _try_git(root: Path, args: list[str]) -> str:
    try:
        return _git(root, args)
    except (OSError, subprocess.CalledProcessError):
        return ""


def main(argv: Sequence[str] | None = None) -> int:
    from mathtutor.help.eval import report  # report imports this module

    parser = argparse.ArgumentParser(prog="python -m mathtutor.help.eval.run")
    parser.add_argument("--split", choices=["dev", "holdout"])
    parser.add_argument("--models", default=None, help="comma-separated model ids")
    parser.add_argument("--max-usd", default=None, help="spend cap for this run (required)")
    parser.add_argument("--no-retrieval", action="store_true", help="no passages (baseline)")
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--freeze", default=None, help="commit the holdout run is frozen at")
    parser.add_argument("--seed", default=None, help="judge order seed (default: run id)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--retrieval-only", action="store_true", help="Recall/MRR only; free")
    parser.add_argument(
        "--draft", action="store_true", help="with --retrieval-only: allow unreviewed"
    )
    parser.add_argument("--recompute", default=None, help="results dir: re-score with audit.csv")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        if args.recompute:
            report.recompute(Path(args.recompute))
            print(f"recomputed {args.recompute}/summary.md")
            return 0
        if args.split is None:
            raise RunnerError("--split is required")
        check_freeze(args.split, args.freeze, root)
        return _execute(args, root)
    except (RunnerError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
