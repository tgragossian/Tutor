"""Memory-sizing burst (milestone B task 16, spec 09): N users submit one answer at once.

Registers ``--users`` accounts, opens a session on each at the dev case's problem, then
fires every submit at the same moment and reports outcomes and latency. Watch the host's
memory while it runs (docs/ops/runbook.md, "Measure memory"). Standard library only, so it
runs on the host's system Python:

    python3 tools/load/submit_burst.py --base-url https://tutor.thomasgragossian.dev

``--mode help`` adds ``--help-users`` hint requests released with the grading submits
(the help generator runs for real, or scripted in a test container) and reports grading and
help latency separately. Keep ``--users`` within the grading queue (8) so any grading
``verifier_busy`` means help traffic starved grading.

Expected replies: 200 with a verdict, or 503 verifier_busy when the burst exceeds the
queue. Anything else (database_busy, format replies, a verifier internal_error even under
200, other errors, transport failures) is unexpected, and so is a run with no graded answer;
either makes the exit status 1.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE = "d-181-07"  # slowest dev case on a live problem (median of 3 runs, 2026-10-22)
PASSWORD = "load-test-password-1"
MAX_SKIPS = 12
VERDICTS = frozenset({"correct", "incorrect", "unable_to_verify"})


@dataclass(frozen=True)
class Target:
    problem_id: str
    topic: str
    section: str
    exercise: int | None
    answer: dict[str, Any]


def find_target(root: Path, case_id: str) -> Target:
    """The dev case's answer (decimals kept exact) and where its problem sits."""
    dev = root / "evals" / "verifier" / "human" / "dev.jsonl"
    for line in dev.read_text(encoding="utf-8").splitlines():
        case = json.loads(line, parse_float=lambda s: {"num": s})
        if case["id"] == case_id:
            break
    else:
        raise SystemExit(f"no dev case {case_id!r} in {dev}")
    bundle = json.loads((root / "content" / "compiled" / "problems.json").read_text("utf-8"))
    problem = next(p for p in bundle["problems"] if p["id"] == case["problem_id"])
    answer = {"kind": problem["answer"]["kind"], **case["answer"]}
    src = problem["source"]
    return Target(problem["id"], problem["topic"], src["section"], src.get("exercise"), answer)


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * pct // 100))
    return ordered[int(rank) - 1]


def session_cookie(set_cookie_headers: list[str]) -> str | None:
    for header in set_cookie_headers:
        name, _, rest = header.partition("=")
        if name.strip() == "mt_session":
            return rest.split(";", 1)[0]
    return None


def _expected(status: int, label: str) -> bool:
    return (status == 200 and label in VERDICTS) or (status == 503 and label == "verifier_busy")


def graded(results: list[tuple[int, str, float]]) -> int:
    """Answers the verifier actually graded (a sizing run needs at least one)."""
    return sum(1 for status, label, _ in results if status == 200 and label in VERDICTS)


def summarize(results: list[tuple[int, str, float]]) -> tuple[str, int]:
    """Text report plus the number of unexpected replies (review B-R4)."""
    counts = Counter(f"{status} {label}" for status, label, _ in results)
    ms = [m for _, _, m in results]
    lines = [f"  {key}: {n}" for key, n in sorted(counts.items())]
    lines.append(
        f"  latency p50 {percentile(ms, 50):.0f} ms, p95 {percentile(ms, 95):.0f} ms, "
        f"max {max(ms):.0f} ms"
    )
    unexpected = sum(1 for status, label, _ in results if not _expected(status, label))
    return "\n".join(lines), unexpected


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.cookie: str | None = None
        self.csrf: str | None = None

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any, list[str]]:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("content-type", "application/json")
        if self.cookie:  # passed by hand: the Secure cookie is never resent over plain http
            req.add_header("Cookie", f"mt_session={self.cookie}")
        if self.csrf:
            req.add_header("X-CSRF-Token", self.csrf)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, json.loads(resp.read() or b"null"), _cookies(resp)
        except urllib.error.HTTPError as err:
            text = err.read()
            payload = json.loads(text) if text.startswith(b"{") else None
            return err.code, payload, _cookies(err)


def _cookies(resp: Any) -> list[str]:
    return list(resp.headers.get_all("Set-Cookie") or [])


def register(client: Client, username: str) -> None:
    while True:
        status, body, cookies = client.call(
            "POST", "/api/auth/register", {"username": username, "password": PASSWORD}
        )
        if status == 429:  # 10 sign-ups per minute per IP
            print(f"  rate limited registering {username}; waiting 15 s", flush=True)
            time.sleep(15)
            continue
        if status != 200:
            raise SystemExit(f"register {username}: HTTP {status} {body}")
        client.cookie, client.csrf = session_cookie(cookies), body["csrf_token"]
        if client.cookie is None:
            raise SystemExit(f"register {username}: no mt_session cookie")
        return


def open_at_target(client: Client, target: Target) -> dict[str, Any]:
    """Start a session on the topic and skip until the target problem is current."""
    status, body, _ = client.call("POST", "/api/sessions", {"topics": [target.topic]})
    if status != 201:
        raise SystemExit(f"start session: HTTP {status} {body}")
    sid = body["session_id"]
    _, current, _ = client.call("GET", f"/api/sessions/{sid}/current")
    for _ in range(MAX_SKIPS):
        item = current["item"]
        if item["source"]["section"] == target.section and (
            item["source"].get("exercise") == target.exercise
        ):
            return {"session_id": sid, "item": item}
        ref = {"session_item_id": item["session_item_id"], "item_revision": item["revision"]}
        _, current, _ = client.call("POST", f"/api/sessions/{sid}/skip", ref)
    raise SystemExit(f"never reached {target.problem_id} in session {sid}")


def _submit_one(client: Client, at: dict[str, Any], target: Target) -> tuple[int, str, float]:
    body = {
        "submission_id": str(uuid.uuid4()),
        "session_item_id": at["item"]["session_item_id"],
        "item_revision": at["item"]["revision"],
        "answer": target.answer,
    }
    t0 = time.perf_counter()
    try:
        status, reply, _ = client.call("POST", f"/api/sessions/{at['session_id']}/submit", body)
    except (OSError, ValueError) as exc:  # URLError, timeouts, a non-JSON body
        return 0, f"transport:{exc}"[:80], (time.perf_counter() - t0) * 1000
    ms = (time.perf_counter() - t0) * 1000
    if status == 200:
        out = reply["outcome"]
        label = out.get("status") or f"format:{out.get('code')}"
        # A crashed verifier answers 200 unable_to_verify/internal_error: keep the reason
        # so it is not counted as graded work (review recheck B-R4). Ordinary abstentions
        # (not_proven, a timeout) stay plain verdicts.
        if out.get("reason") == "internal_error":
            label = f"{label}:internal_error"
    else:
        label = (reply or {}).get("error", "no_body")
    return status, label, ms


def _help_one(client: Client, at: dict[str, Any]) -> tuple[int, str, float]:
    """One hint request on the user's own open item (no student text is sent)."""
    body = {
        "help_request_id": str(uuid.uuid4()),
        "session_item_id": at["item"]["session_item_id"],
        "item_revision": at["item"]["revision"],
        "help_type": "hint",
    }
    t0 = time.perf_counter()
    try:
        status, reply, _ = client.call("POST", "/api/help", body)
    except (OSError, ValueError) as exc:
        return 0, f"transport:{exc}"[:80], (time.perf_counter() - t0) * 1000
    ms = (time.perf_counter() - t0) * 1000
    if status == 200:
        label = (reply or {}).get("status", "no_status")
    else:
        label = (reply or {}).get("error", "no_body")
    return status, label, ms


def _run_gated(jobs: list[Any]) -> list[Any]:
    """Run every job in its own thread, released together by a barrier."""
    gate = threading.Barrier(len(jobs))
    results: list[Any] = [None] * len(jobs)

    def run(i: int, job: Any) -> None:
        gate.wait()
        results[i] = job()

    threads = [threading.Thread(target=run, args=(i, j)) for i, j in enumerate(jobs)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    return results


def burst(clients: list[tuple[Client, dict[str, Any]]], target: Target) -> list[Any]:
    return _run_gated([lambda c=c, at=at: _submit_one(c, at, target) for c, at in clients])


def burst_mixed(
    grading: list[tuple[Client, dict[str, Any]]],
    helpers: list[tuple[Client, dict[str, Any]]],
    target: Target,
) -> tuple[list[Any], list[Any]]:
    """Grading submits and help requests released at the same moment."""
    jobs = [lambda c=c, at=at: _submit_one(c, at, target) for c, at in grading]
    jobs += [lambda c=c, at=at: _help_one(c, at) for c, at in helpers]
    results = _run_gated(jobs)
    return results[: len(grading)], results[len(grading) :]


HELP_OK = frozenset({"delivered", "abstained", "fallback", "unavailable"})


def summarize_mixed(
    grading: list[tuple[int, str, float]], helps: list[tuple[int, str, float]]
) -> tuple[str, int]:
    """Grading and help reported separately; returns the number of failures.

    A failure is any grading reply other than a verdict (``verifier_busy`` included: the
    grading pool must not be starved by help traffic) or any help reply other than 200 with
    a finished status (a 429 or 202 under this load means the run did not measure help).
    """
    lines = ["grading:"]
    counts = Counter(f"{s} {lab}" for s, lab, _ in grading)
    lines += [f"  {k}: {n}" for k, n in sorted(counts.items())]
    g_ms = [m for _, _, m in grading]
    lines.append(
        f"  grading latency p50 {percentile(g_ms, 50):.0f} ms, p95 {percentile(g_ms, 95):.0f} ms"
    )
    lines.append("help:")
    counts = Counter(f"{s} {lab}" for s, lab, _ in helps)
    lines += [f"  {k}: {n}" for k, n in sorted(counts.items())]
    h_ms = [m for _, _, m in helps]
    lines.append(
        f"  help latency p50 {percentile(h_ms, 50):.0f} ms, p95 {percentile(h_ms, 95):.0f} ms"
    )
    bad_grading = sum(1 for s, lab, _ in grading if not (s == 200 and lab in VERDICTS))
    bad_help = sum(1 for s, lab, _ in helps if not (s == 200 and lab in HELP_OK))
    return "\n".join(lines), bad_grading + bad_help


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--users", type=int, default=16)
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument(
        "--mode",
        choices=("grading", "help"),
        default="grading",
        help="help: also fire --help-users hint requests at the same moment and report "
        "grading and help latency separately (any grading verifier_busy fails the run)",
    )
    parser.add_argument("--help-users", type=int, default=20)
    args = parser.parse_args(argv)

    target = find_target(ROOT, args.case)
    run = secrets.token_hex(3)
    print(f"case {args.case} on {target.problem_id}; registering {args.users} users", flush=True)
    clients = []
    for i in range(args.users):
        client = Client(args.base_url)
        register(client, f"load_{run}_{i:02d}")
        clients.append((client, open_at_target(client, target)))
    if args.mode == "help":
        return _main_help(args, target, run, clients)
    print(f"all {args.users} at {target.problem_id}; submitting at once", flush=True)
    t0 = time.perf_counter()
    results = burst(clients, target)
    print(f"burst finished in {(time.perf_counter() - t0) * 1000:.0f} ms")
    text, unexpected = summarize(results)
    print(text)
    ok = graded(results)
    if unexpected:
        print(f"FAIL: {unexpected} unexpected replies", file=sys.stderr)
    if ok == 0:
        print("FAIL: no answer was graded; not usable for sizing", file=sys.stderr)
    return 1 if unexpected or ok == 0 else 0


def _main_help(
    args: argparse.Namespace,
    target: Target,
    run: str,
    clients: list[tuple[Client, dict[str, Any]]],
) -> int:
    helpers = []
    for i in range(args.help_users):
        client = Client(args.base_url)
        register(client, f"loadh_{run}_{i:02d}")
        helpers.append((client, open_at_target(client, target)))
    print(f"{len(clients)} grading + {len(helpers)} help users ready; firing at once", flush=True)
    t0 = time.perf_counter()
    grading, helps = burst_mixed(clients, helpers, target)
    print(f"mixed burst finished in {(time.perf_counter() - t0) * 1000:.0f} ms")
    text, failures = summarize_mixed(grading, helps)
    print(text)
    if failures:
        print(f"FAIL: {failures} grading or help replies were not as expected", file=sys.stderr)
    if graded(grading) == 0:
        print("FAIL: no answer was graded; not usable for sizing", file=sys.stderr)
    return 1 if failures or graded(grading) == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
