[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 21–79. Review findings remain unresolved.

## 0. Brainstorming Outcomes (2026-10-13) — read this first

This section **overrides** later sections wherever they conflict.

**Documents produced**
- Spec: `docs/superpowers/specs/2026-10-13-core-practice-loop-design.md`
- Plan: `docs/superpowers/plans/2026-10-13-core-practice-loop.md` (20 TDD tasks)
- The plan refines the spec in one place: the numeric-point rule. If the expected answer is defined at a point and the student's is not, that point counts as a counterexample. Both files already reflect this.

**Pending before any code is written**
1. **Codex runs an independent review** of the spec and plan. It should challenge:
   - verifier soundness: false-accept paths, the numeric sampling rule, implicit differentiation, decimal rounding
   - task ordering and interface consistency between tasks
   - security of untrusted MathJSON input
   - whether roughly 160 hours is realistic
2. **Codex restructures every Markdown file** (this handoff, the spec, the plan) into a **tree of modular files, each at most 100 lines**, with index/README files linking down the tree. The goal is efficient navigation and debugging. Content must be preserved. Update cross-references, and keep the Superpowers `docs/superpowers/{specs,plans}/` roots.
3. The developer approves the reviewed plan and chooses an execution method. Claude recommended subagent-driven execution, but no choice has been made yet.

**Developer context added.** This is the developer's centerpiece portfolio project for entry-level ML Engineer roles. Their existing projects already show tabular ML and evaluation (LightGBM, conformal prediction, SQL). The gaps this project must fill are **shipped/deployed software, LLM/RAG systems, and PyTorch/Hugging Face fine-tuning**. Budget: about 20 h/week for about 8 weeks (~160 h).

**Revised roadmap (replaces §9–§10 phase order)**

| Weeks | Sub-project |
|---|---|
| 1–2 | **1. Core practice loop** (spec above): verifier, accounts, study sessions, rule-based recommender, MathLive UI, deployed |
| 3–4 | **2. Extraction pipeline** from OpenStax Calculus Vol. 1 **HTML** (odd and even exercises) |
| 5–6 | **3. RAG tutor** over Vol. 1 and Vol. 2, with hints and an evaluation using MathDial teacher-move labels |
| 7–8 | **4. MathDial LoRA fine-tune** vs. prompting, plus polish. This is what slips if the schedule runs over. |

Later: a multi-day exam planner, empirical difficulty via IRT, Calc II graded practice, knowledge tracing.

How the sub-project 2 pipeline works:
- An LLM turns each exercise into a structured task, and SymPy computes the answer.
- Odd exercises are cross-checked against the book's answer key.
- Each problem gets a status: `auto_verified`, `computed_only` or `needs_review`.
- Error rates are estimated from random samples that the developer checks by hand.

**Key decisions**
- **No Mathpix or OCR.** The source is the OpenStax HTML (CC BY-NC-SA 4.0). This supersedes §4.2's preferred extraction service.
- **App structure:** a single FastAPI app with Jinja + HTMX pages; no React. The database is SQLite via SQLAlchemy and Alembic. Hosting is Docker on Lightsail behind Caddy, with nightly backups to S3.
- **Users:** the MVP is portfolio-first but ready for a small pilot, with real accounts and a per-user attempt log.
- **Math input:** MathLive with a calculus button row plus the built-in virtual keyboard. Students never type LaTeX.
- **Study sessions:** the student picks topics, minutes and exam conditions (closed book, formula sheet or open notes). There are three modes:
  - **Diagnostic:** finds gaps
  - **Practice:** opens with a conceptual warm-up
  - **Recap:** formula and concept review

  Two mastery scores are tracked per topic: recall and application.
- **Verifier:**
  - MathJSON is converted to SymPy through an allowlist; student input is never `eval`'d.
  - Checks run in a sandboxed worker process with a 3 s timeout.
  - Equivalence is checked symbolically, then numerically.
  - There are 7 answer types.
  - The verifier has a ≥300-case evaluation set, and CI fails on any false accept.
- **Difficulty:** rated 1–5 by the developer using a rubric. Empirical difficulty from IRT comes later.
- **Formula and concept content** is written by the developer. Online cheat sheets inform which formulas to include, but their wording is not copied.

**Working preference:** keep every Markdown file at most 100 lines, organized as a tree.

<!-- End preserved source. -->
