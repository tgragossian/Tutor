# Milestone A — Contracts and Deployed Skeleton: Implementation Plan

[Delivery plan](../README.md) · [Milestone A goals](../01-foundation.md) · [Handoff](../../../../../handoff.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested Python/Node scaffold with real MathLive captures, typed content and API contracts, six human-reviewed seed problems, and an HTTPS skeleton deployed on Lightsail.

**Architecture:**
- Authors write YAML. A pinned Node tool (MathLive's Compute Engine) compiles it to `content/compiled/problems.json`.
- The FastAPI app loads only that compiled file, validates it with pydantic, and serves `/healthz`, `/readyz` and a placeholder page.
- A Docker image runs behind Caddy for HTTPS.
- No grading and no database yet. Those are milestone B.

**Tech Stack:**
- Python 3.12, uv, FastAPI, pydantic v2, pydantic-settings, Jinja2, pytest, ruff, mypy
- Node 24, mathlive ≥ 0.111.1, @cortex-js/compute-engine, yaml, playwright
- Docker, Caddy, AWS Lightsail, GitHub Actions

**Spec:** [portfolio-core contracts](../../../specs/2026-10-13-portfolio-core/README.md) (modules 01, 02, 07 and 09 apply most). Executors read the spec and this plan together.

## Plan files

- [Global constraints and review focus](00-constraints.md): applies to every task
- [File map](01-file-map.md): every file this milestone creates

## Tasks

| # | Task | Owner of human steps |
|---|---|---|
| 1 | [Scaffold, docs check, CI](tasks/01-scaffold-ci.md) | Thomas: install uv, create GitHub repo |
| 2 | [Spike: capture MathLive input, ADR 0002](tasks/02-input-spike.md) | Thomas: approve ADR |
| 3 | [Domain enums, content schema, API contracts](tasks/03-contracts.md) | — |
| 4 | [Content compiler and loader](tasks/04-compiler-loader.md) | — |
| 5 | [Six seed problems](tasks/05-seed-problems.md) | Thomas: review every problem |
| 6 | [Web skeleton: settings, app, health](tasks/06-web-skeleton.md) | — |
| 7 | [Container, Caddy, CI smoke test](tasks/07-container.md) | Thomas: install Docker Desktop (optional) |
| 8 | [Deploy skeleton to Lightsail](tasks/08-deploy.md) | Thomas: AWS, domain, DNS |

Tasks 1 → 2 → 3 → 4 → 5 run in order. Task 6 needs 4; task 7 needs 6; task 8 needs 7.
Task 5's review can happen while 6 and 7 are being built.

## Deferred to milestone B (so A claims nothing it doesn't do)

- Translator, bounds, equivalence and the verifier pool (spec 03–05).
- Loader checks that need the translator: the expected answer translates, is proven equal to itself, and has a provable domain (spec 01, "Loader errors").
- Database, sessions, auth, CSRF, the 16 KB body limit, rate limits and the practice UI (spec 06–07).
- Self-hosting MathLive under `static/vendor/` with SRI hashes.
- Measuring memory and finalising the pool size (spec 09).

Deferred to milestone D: deploying by image digest from CI, rollback by digest, S3 backups.
Until then, task 8 deploys by building from a git checkout on the host.

## Exit evidence (from [01-foundation](../01-foundation.md))

- Six source-attributed problems load; malformed content fails with messages that name the problem and the field (tasks 4–5).
- Captured browser payloads, including malformed and partial ones, are committed with the pinned versions (task 2).
- `contracts/examples/` is validated by the API models (task 3).
- CI runs lint, types, unit tests, the docs check, a content stale-check and a container smoke test (tasks 1, 4, 7).
- `https://<domain>/readyz` returns ready from outside AWS (task 8).
- No credentials in Git (tasks 6–8).

Record the hours spent at the end of each task in `docs/ops/hours.md` (created in task 1).
