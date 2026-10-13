[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 1–41. Review findings remain unresolved.

# Core Practice Loop — Design Spec (Sub-project 1)

**Date:** 2026-10-13
**Status:** Draft for review
**Source:** `handoff.md` plus the brainstorming decisions recorded here. Where this spec and the handoff disagree, this spec wins.

---

## 1. Context and goals

The project is an adaptive Calculus tutor. It is also the developer's centerpiece portfolio project for entry-level ML Engineer applications. It is meant to fill gaps the developer's existing work does not show: shipped and deployed software, LLM/RAG systems, and deep-learning fine-tuning. Rigorous, measured evaluation stays a theme throughout.

Budget: about 20 h/week for about 8 weeks (~160 h).

### 1.1 Roadmap (each sub-project gets its own spec → plan → build cycle)

| Weeks | Sub-project | Delivers |
|---|---|---|
| 1–2 | **1. Core practice loop (this spec)** | Verifier, accounts, study sessions, recommender, MathLive UI, deployed |
| 3–4 | 2. Problem extraction pipeline | OpenStax Calculus Vol. 1 HTML → structured problems (odd and even exercises). An LLM extracts a structured task, SymPy computes the answer, and odd exercises are cross-checked against the book's answer key. Error rates are estimated from random hand-checked samples. |
| 5–6 | 3. RAG tutor | Vol. 1 + Vol. 2 indexed with citations, progressive hints, retrieval metrics, hint-leakage evaluation using MathDial's teacher-move labels |
| 7–8 | 4. MathDial LoRA fine-tune + polish | Fine-tuned vs. prompted tutor on held-out data. This is the item that slips if the schedule runs over. |

Later, outside the 8 weeks: a multi-day exam planner, empirical item difficulty (IRT), Calc II graded practice (rerun the pipeline and add series/interval answer types), and knowledge-tracing experiments.

### 1.2 Decisions taken during brainstorming

- No Mathpix or OCR. OpenStax *Calculus Vol. 1* (CC BY-NC-SA 4.0) HTML is the source for problems and, later, for RAG.
- The MVP is portfolio-first, but supports a small real pilot. That means real accounts and a clean per-user attempt log.
- The app is one FastAPI monolith with server-rendered pages (Jinja + HTMX). No React.
- Proofs are never verified. Theorem content is limited to computational questions and multiple choice.
- Difficulty is 1–5, assigned by the author using a rubric (§4.3). Empirical difficulty from IRT comes later.
- "Time available" means minutes in the current sitting. The multi-day exam planner is deferred.
- The math input is MathLive with a calculus button row plus MathLive's built-in virtual keyboard.

### 1.3 Out of scope for sub-project 1

LLM calls of any kind, hints, RAG, Ask mode, the extraction pipeline, Calc II, the exam planner, password reset or email, OAuth, admin UI, Postgres.

---

<!-- End preserved source. -->
