[Index](../2026-10-13-core-practice-loop.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 1–16. Review findings remain unresolved.

# Core Practice Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy sub-project 1 of the adaptive Calculus tutor. Students sign up, run diagnostic, practice or recap sessions on 15 Calc I topics, enter answers with MathLive, and get verdicts from a sandboxed, measured SymPy verifier.

**Architecture:** One FastAPI app that serves both server-rendered pages (Jinja + HTMX) and a JSON API.
- **Pure core:** `verify`, `mastery` and `recommend` touch neither the database nor the web.
- **Content:** version-controlled YAML, validated at startup.
- **User data:** SQLite (SQLAlchemy + Alembic).
- **Hosting:** Docker on Lightsail behind Caddy, with nightly backups to S3.

**Tech Stack:** Python 3.12, uv, FastAPI, Jinja2, HTMX, MathLive, pydantic v2, pydantic-settings, SymPy, mpmath, SQLAlchemy 2.0, Alembic, argon2-cffi, structlog, pytest, Hypothesis, pytest-playwright, ruff, mypy, Docker, Caddy, GitHub Actions, AWS Lightsail + S3.

**Spec:** `docs/superpowers/specs/2026-10-13-core-practice-loop-design.md`. Read it first. Section numbers below (§) refer to it.

<!-- End preserved source. -->
