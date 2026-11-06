"""Durable evaluation spend in integer micro-USD (review C1-R9).

Every provider call the runner makes (help or judge) is reserved at its worst case in the run's
``spend.jsonl`` before it is sent, and settled at its actual cost afterwards. Each line is
flushed and fsynced before the call goes out, so a run interrupted at any point (crash, Ctrl-C,
power loss) still leaves its spend on disk: an open reservation counts at its worst case until
reconciled. ``total_spend`` sums every run's journal for the next run's credit.
The journal holds ids, model names and amounts only, never prompt or model text.
"""

from __future__ import annotations

import itertools
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from mathtutor.help.config import HelpConfig, worst_case_micros
from mathtutor.help.eval.judge import JUDGE_MAX_INPUT_TOKENS, JUDGE_MAX_OUTPUT_TOKENS, JUDGE_MODEL
from mathtutor.help.ledger import micros_for

JOURNAL = "spend.jsonl"
CallKind = Literal["help", "judge", "charge"]


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


class SpendJournal:
    """Append-only JSON lines, each flushed and fsynced before the caller continues."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


class SpendCounter:
    """The run's spend against ``cap_micros``: settled costs plus every open reservation at its
    worst case. With a ``journal``, each reservation and settlement is written durably."""

    def __init__(
        self, cfg: HelpConfig, cap_micros: int, journal: SpendJournal | None = None
    ) -> None:
        self.help_cfg = cfg
        self.judge_cfg = judge_cfg(cfg)
        self.cap_micros = cap_micros
        self.settled_micros = 0
        self._open: dict[int, int] = {}
        self._ids = itertools.count(1)
        self._journal = journal

    @property
    def spent_micros(self) -> int:
        return self.settled_micros + sum(self._open.values())

    def worst_call(self, model: str) -> int:
        return worst_case_micros(self.help_cfg, model)

    def worst_judge(self, model: str = JUDGE_MODEL) -> int:
        return worst_case_micros(self.judge_cfg, model)

    def allows(self, worst: int) -> bool:
        return self.spent_micros + worst <= self.cap_micros

    def reserve(self, kind: CallKind, model: str, worst: int) -> int:
        """Record a worst-case reservation before a call is sent; returns its id."""
        rid = next(self._ids)
        if self._journal is not None:
            self._journal.append(
                {"event": "reserve", "id": rid, "kind": kind, "model": model, "worst": worst}
            )
        self._open[rid] = worst
        return rid

    def settle(self, rid: int, micros: int) -> None:
        if self._journal is not None:
            self._journal.append({"event": "settle", "id": rid, "micros": micros})
        del self._open[rid]
        self.settled_micros += micros

    def charge(
        self,
        cfg: HelpConfig,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        billed_unknown: bool = False,
    ) -> int:
        """Reserve and settle one finished call at once. ``cfg`` (``help_cfg`` or ``judge_cfg``)
        gives the token limits of the worst case."""
        micros = call_micros(cfg, model, input_tokens, output_tokens, billed_unknown)
        self.settle(self.reserve("charge", model, worst_case_micros(cfg, model)), micros)
        return micros


@dataclass
class RunSpend:
    run_id: str
    settled_micros: int = 0
    open_micros: int = 0  # reservations never settled: counted at their worst case

    @property
    def total_micros(self) -> int:
        return self.settled_micros + self.open_micros


@dataclass
class SpendTotal:
    runs: list[RunSpend] = field(default_factory=list)

    @property
    def total_micros(self) -> int:
        return sum(r.total_micros for r in self.runs)


def read_journal(path: Path) -> RunSpend:
    run = RunSpend(path.parent.name)
    reserved: dict[int, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # a line torn by a crash mid-write: its reserve, if any, stays open
        if entry.get("event") == "reserve":
            reserved[int(entry["id"])] = int(entry["worst"])
        elif entry.get("event") == "settle" and int(entry["id"]) in reserved:
            del reserved[int(entry["id"])]
            run.settled_micros += int(entry["micros"])
    run.open_micros = sum(reserved.values())
    return run


def total_spend(results: Path) -> SpendTotal:
    """Every run's spend under ``results``: its journal, or ``run.json``'s ``spent_micros``
    for a run written before journals existed."""
    total = SpendTotal()
    for run_dir in sorted(p for p in results.glob("*") if p.is_dir()):
        journal = run_dir / JOURNAL
        if journal.exists():
            total.runs.append(read_journal(journal))
        elif (run_dir / "run.json").exists():
            meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            total.runs.append(RunSpend(run_dir.name, int(meta.get("spent_micros", 0))))
    return total
