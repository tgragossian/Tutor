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

## 2. Architecture

A single Python package. Components are pure where possible and are connected only in `web`.

```
src/mathtutor/
  content/     # pydantic schemas + loader/validator for topics, problems, formula/concept items
  verify/      # MathJSON→SymPy translator, per-answer-type checkers, sandboxed runner
  mastery/     # per-topic recall & application scores from attempt history (pure)
  recommend/   # selection policies: diagnostic, practice, recap, textbook-order baseline (pure)
  store/       # SQLAlchemy models, Alembic migrations, repository functions
  web/         # FastAPI app: JSON API, auth, Jinja/HTMX pages, static assets
content/
  topics.yaml
  problems/*.yaml
  formulas/*.yaml
eval/
  verifier_cases.yaml
  run_verifier_eval.py
tests/
```

**Boundary rules**
- `verify` has no database or web imports. Its input is an answer spec plus MathJSON; its output is a `Verdict`.
- `mastery` and `recommend` are pure functions of (content, attempt history, session plan). Randomness comes in through an injected `random.Random`.
- `web` contains no math or selection logic.
- Content lives in version-controlled YAML and is loaded and validated at startup. The database holds only user-generated data.

**Submit-answer flow**
1. The browser posts MathJSON + LaTeX.
2. `web` checks that the problem is the session's current item.
3. The sandboxed verifier is called (3 s timeout).
4. The attempt is stored.
5. Mastery is recomputed.
6. The response carries the verdict and, in practice mode, the next item with its reason.

---

## 3. Content model

### 3.1 Topics (`content/topics.yaml`)

Fields: `id`, `name`, `area`, `order` (textbook order), `openstax_sections`, `prerequisites`.

| order | id | area | OpenStax § | prerequisites |
|---|---|---|---|---|
| 1 | `limits.intuitive` | Limits | 2.2 | — |
| 2 | `limits.laws` | Limits | 2.3 | limits.intuitive |
| 3 | `continuity` | Continuity | 2.4 | limits.laws |
| 4 | `theorems.ivt` | Theorems | 2.4 | continuity |
| 5 | `derivatives.definition` | Derivatives | 3.1–3.2 | limits.laws |
| 6 | `derivatives.basic_rules` | Derivatives | 3.3 | derivatives.definition |
| 7 | `derivatives.trig` | Derivatives | 3.5 | derivatives.basic_rules |
| 8 | `derivatives.chain_rule` | Derivatives | 3.6 | derivatives.basic_rules, derivatives.trig |
| 9 | `derivatives.implicit` | Derivatives | 3.8 | derivatives.chain_rule |
| 10 | `derivatives.exp_log` | Derivatives | 3.9 | derivatives.chain_rule |
| 11 | `theorems.mvt` | Theorems | 4.4 | continuity, derivatives.basic_rules |
| 12 | `limits.infinity` | Limits | 2.2, 4.6 | limits.laws |
| 13 | `integrals.antiderivatives` | Integrals | 4.10 | derivatives.basic_rules, derivatives.trig, derivatives.exp_log |
| 14 | `integrals.ftc` | Integrals | 5.3 | integrals.antiderivatives |
| 15 | `integrals.substitution` | Integrals | 5.5 | integrals.ftc, derivatives.chain_rule |

The prerequisite graph must be acyclic. This is enforced at load time.

### 3.2 Problems (`content/problems/*.yaml`)

```yaml
id: openstax-c1-3.6-221            # unique, stable
topic: derivatives.chain_rule
difficulty: 2                       # 1–5, rubric §4.3
source: {book: "OpenStax Calculus Volume 1", section: "3.6", exercise: 221,
         url: "https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule",
         license: "CC BY-NC-SA 4.0"}
statement: "Find $\\frac{dy}{dx}$ for $y = \\sin(3x^2)$."   # Markdown + $LaTeX$
answer_type: expression
answer: "6*x*cos(3*x**2)"           # SymPy syntax; trusted content
variable: x
sample_domain: [-5, 5]              # where numeric spot-checks are valid
decimals: 3                         # numeric/limit/point_set only; null = exact only
choices: null                       # multiple_choice only: list of {id, text}
relation: null                      # implicit_derivative only, e.g. "x**2 + y**2 - 25"
status: human_verified              # human_verified | auto_verified | computed_only | needs_review
```

- `answer_type` is one of `numeric`, `expression`, `antiderivative`, `limit`, `implicit_derivative`, `point_set`, `multiple_choice`.
  - Under `antiderivative`, `answer` is **one** antiderivative (not the integrand).
  - `limit` answers may be `oo`, `-oo`, or `DNE`.
  - `point_set` answers are a YAML list.
- `decimals` defaults to 3 when absent, for the types where it applies.
- Only `human_verified`, `auto_verified` and `computed_only` problems are served. Sub-project 1 ships only `human_verified` problems; the other statuses exist for sub-project 2.
- **Content version:** `problem_version` = the first 12 hex characters of the SHA-256 of the problem's canonical JSON. Each attempt stores it.

### 3.3 Formula and concept items (`content/formulas/*.yaml`)

```yaml
- id: deriv.product_rule
  topic: derivatives.basic_rules
  kind: recall                      # recall | concept
  prompt: "Product rule: $\\frac{d}{dx}[f(x)g(x)] = $ ?"
  answer_type: expression           # recall → expression; concept → multiple_choice
  answer: "fp*g + f*gp"
  functions: [f, g]                 # abstract functions allowed in the student answer
  memorize: core                    # recall only: core (always memorized) | sheet (commonly provided)
```

- **Recall** items: about 5–10 per topic.
- **Concept** items: about 2 per topic, `multiple_choice`, written by the developer.
- Commonly used professor cheat sheets inform *which* formulas exist and whether each is `core` or `sheet`. The wording is our own; sheets are not copied.
- The per-topic **formula sheet** is rendered from the same recall entries.
- Abstract functions: in the student's MathJSON, `f(x)` maps to symbol `f` and `f'(x)` maps to symbol `fp` (likewise `g`/`gp`). This is allowed only for names listed in `functions`.

### 3.4 Seed content for sub-project 1

- 20 `human_verified` problems covering all 15 topics, with every `answer_type` used at least once.
- Recall and concept items for all 15 topics.

---

## 4. Verifier

### 4.1 Translation (untrusted input)

- The input is MathJSON from MathLive. The translator walks the tree and builds SymPy objects **only** from an allowlist:
  - integers, decimals and rationals
  - the problem's variable(s); `y` for implicit problems
  - declared abstract functions
  - `Add`, `Subtract`, `Negate`, `Multiply`, `Divide`, `Power`, `Sqrt`, `Root`
  - `Sin`, `Cos`, `Tan`, `Sec`, `Csc`, `Cot` and their inverses
  - `Ln`, `Log` (base 10 or given base), `Exp`, `Abs`
  - `Pi`, `ExponentialE`, `PositiveInfinity`, `NegativeInfinity`
  - the `DNE` token
  - `List` / `Set` for `point_set`
- **Limits:**
  - max 200 nodes and depth 30
  - integer literals at most 30 digits
  - exponent literals bounded to |n| ≤ 1000
- **Never** call `sympify`, `parse_expr` or `eval` on student input.
- Expected answers are trusted and parsed with `parse_expr` at load time.
- A rejection yields `unable_to_verify` with reason `unsupported_notation` or `input_too_large`.

### 4.2 Equivalence and per-type rules

Equivalence for expression-like comparisons:
1. **Symbolic:** `simplify(student - expected) == 0` → `correct`, method `symbolic`.
2. **Numeric:**
   - Draw 20 points uniformly from `sample_domain` (seeded) and evaluate both expressions with mpmath at 50 digits.
   - Skip a point if either side is non-finite or non-real.
   - If any valid point has |s − e| > 1e-8 · max(1, |e|) → `incorrect`, method `numeric`.
   - If all valid points agree and there are ≥ 10 of them → `correct`, method `numeric`.
   - Otherwise → `unable_to_verify`, reason `insufficient_sample_points`.

| answer_type | Rule |
|---|---|
| `expression` | Equivalence as above |
| `antiderivative` | Equivalence of d/dx(student) against d/dx(expected) |
| `numeric` | An exact student input is checked symbolically, then numerically at 50 digits. A decimal input with ≥ `decimals` places is `correct` iff round(expected, decimals) == round(student, decimals). |
| `limit` | `oo` / `-oo` / `DNE` must match exactly; otherwise as `numeric` |
| `point_set` | The two sets must have the same size and admit a one-to-one numeric match (as `numeric`), in any order |
| `implicit_derivative` | Pick 20 x-values in `sample_domain`, solve `relation` for real y numerically (`nsolve` from several starts), and compare at (x, y) pairs with the numeric rule. With < 10 valid pairs → `unable_to_verify`. |
| `multiple_choice` | Choice id equality |

**Input-format pre-checks.** These return a format message and **do not create an attempt**:
- empty input
- a decimal with fewer than `decimals` places
- a decimal when `decimals` is `null`

The UI always shows the precision rule under the input: "Enter an exact value, or a decimal rounded to N places" / "Exact answer required".

### 4.3 Difficulty rubric (author-assigned)

| Level | Description |
|---|---|
| 1 | One rule, applied directly |
| 2 | One rule plus light algebra |
| 3 | Two rules combined, or a domain/sign subtlety |
| 4 | Three or more steps, or a nontrivial setup |
| 5 | Multi-concept, or an exam-style trap |

### 4.4 Sandbox

- Every check runs in a dedicated worker process: `multiprocessing` with spawn, one task at a time.
- The caller waits up to **3 s**, then kills and respawns the worker → `unable_to_verify`, reason `timeout`.
- Any worker exception → `unable_to_verify`, reason `internal_error` (logged).
- On Linux, `resource.setrlimit(RLIMIT_AS, 512 MB)` is applied in the worker. On Windows it is skipped.

### 4.5 Output

```python
@dataclass(frozen=True)
class Verdict:
    status: Literal["correct", "incorrect", "unable_to_verify"]
    reason: str          # machine-readable code, e.g. "symbolic_equal", "counterexample", "timeout"
    method: Literal["symbolic", "numeric", "exact", "rounding", "none"]
    latency_ms: int
```

Student-facing text:
- "Correct"
- "Not quite"
- "We couldn't check this answer automatically. It's saved; try a simpler form."

### 4.6 Verifier evaluation

- `eval/verifier_cases.yaml` holds **≥ 300** labelled cases `{problem_ref, student_mathjson, label}`.
- The cases cover:
  - tricky equivalents: trig identities, log rules, unsimplified forms, differing constants, decimals
  - typical errors: sign errors, a missing chain-rule factor, off-by-constant, wrong power
  - unsupported input
- `run_verifier_eval.py` reports the false-accept rate, false-reject rate, inconclusive rate and p50/p95 latency, broken down by answer type and method.
- CI fails on any false accept.

---

## 5. User data (SQLite via SQLAlchemy 2.0, Alembic migrations)

| Table | Columns |
|---|---|
| `users` | id, username (unique, 3–32 chars `[a-z0-9_]`), password_hash (argon2), created_at |
| `study_sessions` | id, user_id, mode (`diagnostic` \| `practice` \| `recap`), exam_conditions (`closed_book` \| `formula_sheet` \| `open_notes`), topics (JSON list), minutes_budget, warmup_enabled, current_item_id, current_item_served_at, started_at, ended_at |
| `attempts` | id, user_id, study_session_id, item_id, item_kind (`problem` \| `recall` \| `concept`), item_version, answer_latex, answer_mathjson, verdict_status, verdict_reason, verdict_method, attempt_number, is_first_attempt, seconds_spent, hints_used (always 0 in sub-project 1), revealed (bool), created_at |

- `seconds_spent` is computed **server-side** as submit time minus `current_item_served_at`.
- A submission for an item that is not the session's current item is rejected with `409`.
- Mastery is **derived** from `attempts`, never stored.
- The `attempts` table is the future training data for knowledge tracing: user, item, skill, correctness, time.

---

## 6. Mastery and selection policies

### 6.1 Mastery (per topic, two scores)

- **Recall score:** computed from `recall` and `concept` items.
- **Application score:** computed from `problem` items.
- **Which attempts count:** only first attempts. A `multiple_choice` attempt has weight 0.5; others have weight 1.0. Each attempt is further multiplied by recency decay 0.5^(k/10), where k is the number of newer attempts the user has in that topic and score.
- **Formula:** score = (Σ w·correct + 1) / (Σ w + 2).
- **Bands:**
  - fewer than 2 counted attempts → `not_seen`
  - < 0.5 → `weak`
  - 0.5–0.8 → `shaky`
  - ≥ 0.8 → `strong`
- `unable_to_verify` attempts are excluded from mastery.

### 6.2 Time estimate per problem

Difficulty 1/2/3/4/5 → 1.5/2.5/3.5/4.5/6 minutes. Recall and concept items take 0.5 minutes each.

### 6.3 Exam conditions

| Setting | Recall items used | Formula sheet panel |
|---|---|---|
| `closed_book` | all | hidden |
| `formula_sheet` | `memorize: core` only | available |
| `open_notes` | none (concept items only) | available |

### 6.4 Policies

Every selection returns `(item_id | None, reason: str)`. The reason is shown to the student.

**Diagnostic**
- For each selected topic in textbook order:
  - 1 recall or concept item (filtered by exam conditions)
  - 2 unseen problems at difficulty 2–3
- If the time budget cannot fit that, use 1 problem per topic.
- One try per item and no per-item feedback.
- The session ends with a report: per-topic recall and application bands, plus each item with its verdict. The report has a "Practise my weak topics" button that pre-fills a practice session.

**Practice**
- **Warm-up:** if enabled (the default), up to 6 recall and concept items for the selected topics, weakest recall first. Immediate feedback; skippable.
- **Main loop:**
  1. **Topic:** the selected topic with the lowest application score (`not_seen` counts as 0.5). If one of its prerequisites is `weak`, choose one problem from that prerequisite first. Reason example: "Prerequisite check: derivatives.basic_rules is weak".
  2. **Difficulty:** start at the user's current level for that topic (default 2). +1 after 2 consecutive correct first attempts; −1 after an incorrect one; clamped to 1–5. If no problem exists at that level, use the nearest available level.
  3. **Problem:** unseen first. If all have been seen, choose the one whose most recent attempt was incorrect and oldest.
  4. Up to 3 tries per problem. After that, a "Show answer" button sets `revealed` and moves on.
  5. **Stop:** when the elapsed time reaches `minutes_budget`, after the current item finishes, or when no eligible items remain.

**Recap**
- Recall and concept items for the selected topics, filtered by exam conditions, with immediate feedback.
- Ends with the per-topic formula sheet.

**Textbook-order baseline**
- Topics in `order`, problems by difficulty ascending.
- It has the same interface but is not exposed in the UI. It exists for later policy comparison.

---

## 7. Web layer

### 7.1 Pages (Jinja + HTMX; MathLive pinned and self-hosted under `static/vendor/`)

1. Login / register
2. Dashboard: per-topic recall and application bands, "Start session"
3. Session setup: topics grouped by area, minutes (15/30/45/60/custom 5–180), mode, exam conditions, warm-up toggle
4. Item page:
   - statement, MathLive field, calculus button row (a/b, xⁿ, √, sin, cos, tan, ln, eˣ, π, |x|, ∞, +C) and MathLive's virtual keyboard
   - precision hint, Check button, verdict area, reason line
   - formula-sheet panel when exam conditions allow
5. Session report

### 7.2 JSON API

| Method & path | Body / returns |
|---|---|
| `POST /api/auth/register`, `/api/auth/login`, `POST /api/auth/logout` | `{username, password}` (password 8–128 chars) |
| `GET /api/topics` | topic tree |
| `POST /api/sessions` | `{mode, topics, minutes, exam_conditions, warmup}` → session |
| `GET /api/sessions/{id}/next` | `{item, reason}` or `{done: true}` |
| `POST /api/attempts` | `{session_id, item_id, answer_mathjson, answer_latex}` → `{verdict, can_retry, can_reveal}` or a format message |
| `POST /api/sessions/{id}/reveal` | expected answer (practice only, after 3 tries) |
| `GET /api/sessions/{id}/report` | per-topic bands + item list |
| `GET /api/me/mastery` | dashboard data |
| `GET /healthz` | `{status: "ok"}` |

Errors use the format `{error: <code>, message: <text>}`.

| Status | Meaning |
|---|---|
| 401 | unauthenticated |
| 403 | another user's session |
| 404 | not found |
| 409 | not the current item / session ended |
| 422 | validation |
| 429 | rate limited |

---

## 8. Errors, security, operations

- **Content load:** any schema error, unknown topic, unparseable answer, duplicate id or prerequisite cycle aborts startup with a precise message. A test enforces the same in CI.
- **Auth:**
  - argon2 hashes
  - signed session cookie: `HttpOnly`, `Secure` (except local dev), `SameSite=Lax`
  - CSRF token on state-changing form/HTMX requests
- **Rate limits (in-process):**
  - login and register: 10/min per IP
  - attempts: 30/min per user
- **Secrets:** environment variables only (`SECRET_KEY`, `DATABASE_URL`). `.env` is git-ignored.
- **Logging:** structured JSON with request_id, user_id, route, status, latency, and verdict status/method/latency. Passwords are never logged.

---

## 9. Testing

| Layer | Content |
|---|---|
| Unit | translator allowlist and rejections, each checker, pre-checks, mastery formula, each policy (seeded RNG) |
| Property-based (Hypothesis) | random MathJSON trees → the translator returns SymPy or a clean rejection; it never raises otherwise |
| Content | all YAML validates; every expected answer parses; every seed problem's expected answer is judged `correct` against itself |
| Integration | FastAPI TestClient + temp SQLite: register → diagnostic → report → practice with warm-up → reveal → recap; authorization and 409 cases |
| Verifier evaluation | `run_verifier_eval.py` in CI; build fails on any false accept |
| End-to-end | one Playwright smoke test: log in, start practice, type into MathLive, see a verdict |

Tooling: Python 3.12, `uv`, `ruff`, `mypy` (strict on `verify`, `mastery`, `recommend`, `content`), `pytest`.

---

## 10. Deployment

- **Image:** Dockerfile (python:3.12-slim) running uvicorn. Alembic `upgrade head` runs at container start.
- **Host:** an AWS Lightsail instance (~$5/mo) running `docker compose` with the app and **Caddy** (automatic HTTPS). This needs a domain (~$12/yr).
- **Data:** SQLite on a host volume. A nightly `sqlite3 .backup` is uploaded to S3, keeping the last 14 backups.
- **CI (GitHub Actions):**
  - ruff, mypy, pytest, verifier evaluation and image build on every push
  - on `main`: push the image to GHCR and deploy over SSH (`docker compose pull && up -d`)
- **Cost guard:** AWS Budget alert at $10/month.

---

## 11. Success criteria (definition of done for sub-project 1)

1. Live over HTTPS at a public URL; CI passes on `main`.
2. Verifier on ≥ 300 labelled cases:
   - false accepts **0**
   - false rejects **≤ 2%**
   - inconclusive **≤ 5%**
   - p95 latency **< 1 s**
3. 20 `human_verified` seed problems, plus recall and concept items for all 15 topics.
4. Diagnostic, practice (with warm-up and reveal) and recap all work end to end (integration + Playwright).
5. README: architecture diagram, how to run locally, verifier evaluation table, and limitations.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| MathLive's MathJSON output differs from what the translator assumes (canonicalization, abstract functions, primes) | The first implementation task is a spike that captures real MathLive output for the 20 seed answers into fixtures; the translator is built against those fixtures. Fallback: parse MathLive's LaTeX with a restricted grammar (lark). |
| `simplify` is slow or hangs | Sandbox timeout. Numeric check as the second path. Latency tracked in the evaluation. |
| Numeric check falsely accepts expressions that agree only on part of the domain | Per-problem `sample_domain`. The evaluation set includes deliberately near-equivalent wrong answers. |
| Scope creep from extra features | Section 1.3 lists what is out of scope. New ideas go to the roadmap, not this spec. |
| Lightsail/HTTPS setup eats time | Deployment is its own plan milestone. The app is fully usable locally before it starts. |
