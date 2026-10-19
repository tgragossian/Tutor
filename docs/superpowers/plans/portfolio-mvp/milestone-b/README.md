# Milestone B — Practice Loop: Implementation Plan

[Delivery plan](../README.md) · [Milestone B goals](../02-practice.md) · [Handoff](../../../../../handoff.md)

**Status (2026-10-19):** tasks 1–8 complete; R22/R23 implemented; task 9 has 136 pending-review draft cases;
tasks 10–16 not started. Draft metrics pass B but no row is reviewed; see [execution status](03-execution-status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A signed-in student picks a topic, answers 20–30 reviewed problems in MathLive, and gets proof-based feedback with retry, skip, reveal and advance, at the deployed URL.

**Architecture:**
- `verify/` translates browser MathJSON through an allowlist into SymPy, proves or refutes equality on the problem's domain, and runs only inside a bounded pool of worker processes.
- `store/` (SQLAlchemy + Alembic, SQLite WAL) persists users, presentations, submissions and results.
- `application/` holds every session rule; HTML and JSON routes in `web/` both call it.
- The problem page is server-rendered HTML that submits through `fetch` to the JSON API.

**Tech Stack:**
- Present: sympy, mpmath; psutil and hypothesis are dev dependencies. Planned: sqlalchemy 2, alembic, argon2-cffi, itsdangerous.
- Present Node tooling: markdown-it, pinned MathLive and Compute Engine. Vendoring under `static/vendor/` is task 14.
- Unchanged: FastAPI, Jinja2, pydantic v2, uv, Docker, Caddy, Lightsail, GitHub Actions

**Spec:** [portfolio-core contracts](../../../specs/2026-10-13-portfolio-core/README.md), modules 01–09. Executors read the spec and this plan together; the spec wins on conflict, decision 0001 wins over the spec.

## Plan files

- [Global constraints, rulings and review focus](00-constraints.md): applies to every task
- [File map](01-file-map.md): every file this milestone creates or changes
- [Execution rulings](02-execution-rulings.md): R7–R23 and in-task rulings (override the plan)
- [Execution status](03-execution-status.md): task progress, pause point, deferred minors
- [Codex doc-sync request](04-codex-doc-sync.md): completed 2026-10-19; original scope retained
- [Follow-ups](05-follow-ups.md): evaluation issues and deferred observations
- [R22/R23 plan](r22-r23/README.md): function parentheses and domain rewrites, before task 10

## Tasks

| # | Task | Est. h | Human step |
|---|---|---:|---|
| 1 | [Milestone A carry-overs and exact decimals](tasks/01-carry-overs.md) | 1.5 | — |
| 2 | [Verify types, structural bounds, pre-checks](tasks/02-bounds-prechecks.md) | 2 | — |
| 3 | [Allowlist translator and cost bound](tasks/03-translator.md) | 3.5 | — |
| 4 | [Equivalence: proof, domain, removable holes](tasks/04-equivalence.md) | 3.5 | — |
| 5 | [Refutation and the `check` dispatcher](tasks/05-refute-check.md) | 3 | — |
| 6 | [Content math check and statement HTML](tasks/06-content-check.md) | 2 | — |
| 7 | [Verifier pool](tasks/07-pool.md) | 2.5 | — |
| 8 | [Evaluation runner, metrics and CI gate](tasks/08-eval-runner.md) | 2 | — |
| 9 | [80 human-reviewed dev cases](tasks/09-dev-cases.md) | 3 | Thomas: review every label |
| 10 | [Store: models, migrations, WAL](tasks/10-store.md) | 2 | — |
| 11 | [Accounts, cookie sessions, CSRF, rate limits](tasks/11-auth.md) | 3 | — |
| 12 | [Practice service and submit protocol](tasks/12-practice-service.md) | 4 | — |
| 13 | [JSON API, errors, logging, readiness](tasks/13-json-api.md) | 2.5 | — |
| 14 | [Pages and MathLive UI](tasks/14-pages-ui.md) | 3.5 | — |
| 15 | [20–30 problems and browser smoke](tasks/15-content-e2e.md) | 3 | Thomas: review new problems |
| 16 | [Release: volume, migrations, memory, deploy](tasks/16-release.md) | 2.5 | Thomas: run host commands |
| | **Total** | **43.5** | Budget target 30 h: see note |

**Order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (verify track), and 10 → 11 → 12 → 13 → 14 (app track).
- The app track may start after task 7. Task 12 needs 7 and 10.
- Task 15 needs 9, 13 and 14. Task 16 needs 15.
- Thomas's reviews in tasks 9 and 15 can run while later tasks are built.

**Budget note:** these estimates total about 43 h against the 30 h timebox in [02-practice](../02-practice.md).
Milestone A finished in about 8 of its 20 h. Record actual hours per task in `docs/ops/hours.md`;
if the running total passes 30 h, stop at the next task boundary and decide with Thomas whether to
cut scope (never accuracy or containment, per the delivery plan) or draw on the 25 h contingency.

## Exit evidence (from [02-practice](../02-practice.md) and spec 08)

- Required: ≥ 80 human-reviewed dev cases; FA 0 observed, FR ≤ 2%, coverage ≥ 85%, generated-set FA 0, enforced in CI (tasks 8–9).
  Current draft: 136 unreviewed cases, FA 0/54, FR 0/52, coverage 52/52 after [R22/R23](r22-r23/README.md); the release gate **fails** until review. Only generated evaluation runs in CI.
- Same-pool recovery after timeout and death, bounded queue, 16-thread concurrency with no zombies (task 7).
- Duplicate submissions, racing submissions, stale revisions, exhausted items and cross-user access tested (task 12).
- No response, JSON or HTML, contains a private answer field (task 13).
- Browser smoke: register, pick a topic, submit, retry, advance, revisit history (task 15).
- Deployed: a reviewer can finish a problem at `https://tutor.thomasgragossian.dev`; API shapes in `contracts/`; supported expressions and limitations published with the evaluation results (task 16).
- Pool size and `RLIMIT_AS` set from measured memory under 16 concurrent submits (task 16).

Deferred to milestone D: digest deploys and rollback by digest, S3 backups and restore drill, the
nightly-reset demo account. Deferred to milestone E: the frozen `final` set and ≥ 300 cases.
