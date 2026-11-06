"""One-shot use of a holdout partition, independent of the code commit (review C1-R4).

Before its first provider call, a holdout run writes a claim to ``evals/help/holdout-claims/``
naming everything it uses: case ids, their source problems, retrieval query ids and the
chunks those queries label relevant. A later holdout that shares any of them is refused, on
any commit and from any output directory: a new commit, reordered rows or reworded cases on
the same problems are not a fresh independent set (spec 08). Commits are provenance only.

Claims are taken under an exclusive lock file, so two runners started together cannot both
pass. A holdout marker from before claims existed (``run.json``/``started.json`` with split
``holdout`` and no claim) is refused until reconciled by hand. Claims hold ids only, no text.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from mathtutor.help.eval.cases import HelpCase, RetrievalQuery
from mathtutor.help.eval.errors import RunnerError

CLAIMS_DIR = Path("evals") / "help" / "holdout-claims"
RESULTS_DIR = Path("evals") / "help" / "results"
LOCK = ".lock"
LEGACY_MARKERS = ("run.json", "started.json")


@dataclass(frozen=True)
class Partition:
    case_ids: tuple[str, ...]
    problem_ids: tuple[str, ...]
    query_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]

    def overlap(self, other: Partition) -> dict[str, list[str]]:
        shared = {
            name: sorted(set(getattr(self, name)) & set(getattr(other, name)))
            for name in ("case_ids", "problem_ids", "query_ids", "chunk_ids")
        }
        return {name: ids for name, ids in shared.items() if ids}


def partition_of(cases: Iterable[HelpCase], queries: Iterable[RetrievalQuery]) -> Partition:
    cases, queries = list(cases), list(queries)
    return Partition(
        case_ids=tuple(sorted({c.case_id for c in cases})),
        problem_ids=tuple(sorted({c.problem_id for c in cases})),
        query_ids=tuple(sorted({q.query_id for q in queries})),
        chunk_ids=tuple(sorted({i for q in queries for i in q.relevant_ids})),
    )


def _claims(root: Path) -> list[tuple[str, Partition]]:
    found = []
    for path in sorted((root / CLAIMS_DIR).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found.append((path.stem, Partition(**{k: tuple(v) for k, v in data["partition"].items()})))
    return found


def legacy_markers(root: Path) -> list[str]:
    """Holdout markers written before claims existed: they name no partition."""
    claimed = {name for name, _ in _claims(root)}
    legacy = []
    for marker in LEGACY_MARKERS:
        for path in sorted((root / RESULTS_DIR).glob(f"*/{marker}")):
            meta = json.loads(path.read_text(encoding="utf-8"))
            if meta.get("split") == "holdout" and path.parent.name not in claimed:
                legacy.append(f"{path.parent.name}/{marker}")
    return legacy


def check_unused(root: Path, partition: Partition) -> None:
    """Refuse a partition that overlaps any claim, or any legacy holdout marker."""
    legacy = legacy_markers(root)
    if legacy:
        raise RunnerError(
            f"holdout results without a claim ({', '.join(legacy[:3])}): that holdout counts "
            "as used; reconcile by hand (record its partition in holdout-claims) before another"
        )
    for name, used in _claims(root):
        shared = partition.overlap(used)
        if shared:
            what = "; ".join(f"{k}: {', '.join(v[:3])}" for k, v in shared.items())
            raise RunnerError(
                f"this holdout overlaps the one already used by {name} ({what}); a holdout "
                "runs once, on any commit, and needs fresh problems and queries"
            )


def claim(root: Path, partition: Partition, run_id: str, head: str, freeze: str) -> Path:
    """Atomically check and claim ``partition`` for ``run_id``; returns the claim path."""
    claims = root / CLAIMS_DIR
    claims.mkdir(parents=True, exist_ok=True)
    lock = claims / LOCK
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RunnerError(
            f"another holdout run holds {lock}; if none is running, check the claims and "
            "delete the lock file"
        ) from None
    try:
        os.close(fd)
        check_unused(root, partition)
        path = claims / f"{run_id}.json"
        if path.exists():
            raise RunnerError(f"run id {run_id} already holds a holdout claim; pick another")
        record = {
            "run_id": run_id,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "head": head,
            "freeze": freeze,
            "partition": asdict(partition),
        }
        with path.open("x", encoding="utf-8", newline="\n") as fh:  # never overwrite a claim
            fh.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return path
    finally:
        lock.unlink(missing_ok=True)
