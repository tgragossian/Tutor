"""Memory-sizing burst (milestone B task 16, spec 09): N users submit one answer at once.

Registers ``--users`` accounts, opens a session on each at the dev case's problem, then
fires every submit at the same moment and reports outcomes and latency. Watch the host's
memory while it runs (docs/ops/runbook.md, "Measure memory"). Standard library only, so it
runs on the host's system Python:

    python3 tools/load/submit_burst.py --base-url https://tutor.thomasgragossian.dev

Busy replies (503 verifier_busy) are expected when the burst exceeds the queue; anything
else outside 200/503 counts as unexpected and makes the exit status 1.
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


def summarize(results: list[tuple[int, str, float]]) -> tuple[str, int]:
    """Text report plus the number of unexpected replies (not 200, not 503)."""
    counts = Counter(f"{status} {label}" for status, label, _ in results)
    ms = [m for _, _, m in results]
    lines = [f"  {key}: {n}" for key, n in sorted(counts.items())]
    lines.append(
        f"  latency p50 {percentile(ms, 50):.0f} ms, p95 {percentile(ms, 95):.0f} ms, "
        f"max {max(ms):.0f} ms"
    )
    unexpected = sum(1 for status, _, _ in results if status not in (200, 503))
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


def burst(clients: list[tuple[Client, dict[str, Any]]], target: Target) -> list[Any]:
    gate = threading.Barrier(len(clients))
    results: list[Any] = [None] * len(clients)

    def submit(i: int, client: Client, at: dict[str, Any]) -> None:
        body = {
            "submission_id": str(uuid.uuid4()),
            "session_item_id": at["item"]["session_item_id"],
            "item_revision": at["item"]["revision"],
            "answer": target.answer,
        }
        gate.wait()
        t0 = time.perf_counter()
        status, reply, _ = client.call("POST", f"/api/sessions/{at['session_id']}/submit", body)
        ms = (time.perf_counter() - t0) * 1000
        if status == 200:
            out = reply["outcome"]
            label = out.get("status") or f"format:{out.get('code')}"
        else:
            label = (reply or {}).get("error", "no_body")
        results[i] = (status, label, ms)

    threads = [
        threading.Thread(target=submit, args=(i, c, at)) for i, (c, at) in enumerate(clients)
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--users", type=int, default=16)
    parser.add_argument("--case", default=DEFAULT_CASE)
    args = parser.parse_args(argv)

    target = find_target(ROOT, args.case)
    run = secrets.token_hex(3)
    print(f"case {args.case} on {target.problem_id}; registering {args.users} users", flush=True)
    clients = []
    for i in range(args.users):
        client = Client(args.base_url)
        register(client, f"load_{run}_{i:02d}")
        clients.append((client, open_at_target(client, target)))
    print(f"all {args.users} at {target.problem_id}; submitting at once", flush=True)
    t0 = time.perf_counter()
    results = burst(clients, target)
    print(f"burst finished in {(time.perf_counter() - t0) * 1000:.0f} ms")
    text, unexpected = summarize(results)
    print(text)
    if unexpected:
        print(f"{unexpected} unexpected replies", file=sys.stderr)
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
