# C1 execution rulings

[C1 plan](README.md) · [Status](20-status.md)

Rulings made while executing the C1 plan with subagents (2026-10-26/27). Each amends the plan
where they differ; the spec stays binding. "Cost" is what it costs if the ruling is wrong.

| # | Ruling | Cost if wrong |
|---|---|---|
| R1 | Parser roundtrip checks choice LaTeX as an `ExpressionAnswer` (choice specs grade ids). | Weaker test on 2 problems. |
| R2 | `create_app(settings, *, pool=None, guard_pool=None)`; the app owns a guard pool only when it owns the grading pool and help is on. | Extra worker in some dev runs. |
| R3 | Pure `assemble_context` and `match_misconception`; `build_context` = DB read + these (eval reuses them). | Small refactor. |
| R4 | `HelpPipeline.run` holds the post-context path; the service wraps it; eval calls it directly. | Eval/production drift. |
| R5 | Owner-only and paid steps (Task 14 steps 6–10, Task 15 steps 5, 7–9) are left for Thomas. | None. |
| R6 | Guard choice rule broadened (keyword + filler + letter, line-start letter, ordinals). | Some over-blocking. |
| R7 | Numeric problems: prose numbers are worker-checked guard candidates. | More candidates. |
| R8 | Foreign single letters also checked as the variable and as 0. | Extra worker checks. |
| R9 | Prose with a LaTeX command, `^` or `_` outside math blocks; renderer renders only guard-extracted delimiters. | Over-blocking odd prose. |
| R10 | A bare letter counts as a choice only as a standalone token (after verbs / "answer is"). | Rare phrasing passes the letter rule. |
| R11 | After `option`/`choice`, the correct letter always blocks. | "option a" as an article over-blocks. |
| R12 | Prose fractions with spaces, ÷ and parentheses; each prose number checked with both signs. | More worker calls. |
| R13 | Glued digit+letter runs block on numeric problems; dedup before the cap; per-letter variants; linear-time regexes; prose `2x` tokens checked. | Some over-blocking. |
| R14 | Foreign letters → 1 variant on numeric problems; thousands separators; ordinal suffixes exempt. | Edge cases. |
| R15 | Appendix tables, intros, preface and index are left out of the corpus. | A few table lookups miss. |
| R16 | Chapter pages use section `N.0`; answer keys keep role `answer_key`; exercise/answer_key never retrievable. | Answer text near the prompt (guard is the backstop). |
| R17 | Task 6 created `help/context.py` types early; Task 9 extended it. | Small move. |
| R18 | Confusion labels ship as JSON (stdlib), not YAML. | Less pleasant hand-editing. |
| R19 | Misconception notes describe the error only; 4 notes reworded; checked at build and at runtime. | Thomas re-words notes. |
| R20 | Choice problems don't show the option list to the model. | Weaker hints on 2 problems. |
| R21 | An in-flight help request older than 120 s is abandoned by the next request. | A very slow result is lost. |
| R22 | `help_seq` advances on every non-stale finalization; hint level only on a delivered hint. | Occasional abstain. |
| R23 | The answer filter uses substring match only for answers ≥ 5 characters; shorter ones match whole math spans. | A short-answer passage reaches the prompt. |
| R24 | Disclaimer says "use Show answer for that"; the source line doesn't repeat the book name. | Copy edit. |
| R25 | Container smoke and compose checks are owner/CI steps (no Docker here). | None. |
| R26 | Paid eval runs use `--max-usd 4` ($5 credit); the runner keeps its own integer spend counter. | None. |
| R27 | Task 15 in-session = burst tool, docs, a labeled preliminary Windows run; container measurement, gate, deploy are Thomas's. | None. |
| R28 | Model selection: Haiku if it passes, else Sonnet if it passes, else none (spec 08). | One line. |
| R29 | Retrieval fixes tuned on dev only: labeling policy, tokenizer `tok-2`, production section boost. A reviewer computed draft holdout BM25 Recall@6 (0.576); no holdout label was edited in response. | Gate may still fail. |
| R30 | Provider/retention disclosure shown with the help UI (spec 09); wording pending Thomas. | Copy edit. |
| R31 | C1-R2: foreign shapes and `f(x)` applications are substituted atoms, every variant checked; > 3 atoms block. | Some over-blocking; a variant set can miss a contrived form. |
| R32 | C1-R4: a holdout claims case, problem, query and chunk ids; any overlap is refused on every commit. | A new holdout needs new problems. |
| R33 | C1-R7: `--no-retrieval` adds the eval-only `no_passages.md`; uncited replies; same guard. | Baseline prompt differs by one paragraph. |
| R34 | C1-R9: per-run `spend.jsonl` (reserve before, settle after) and `--spent`, not an early `run.json`. | None. |
| R35 | Hint ladder per mistake type (Thomas, 2026-10-27): level 0 before a wrong answer; the first hint on each new wrong attempt has the model label it `algebra`, `wrong_rule`, `rule_misapplied` or `incomplete` and write at that type's level (its hint count + 1, cap 3, offered by the server); later hints on the same attempt reuse the type. Migration 0005. Feedback unchanged. | A mislabel gives one hint too gentle or one step too direct (guard still applies). |

Final whole-branch review added: per-user help limits (10 per 60 s, 2 in flight), guard pool
and query caps read from config, runtime note filtering, finalize retry, ledger reconcile in
`settle-uncertain`, a holdout "started" marker.

Codex's subsequent [implementation review](../../../../../reviews/2026-10-27-milestone-c1/README.md)
leaves nine findings open. In particular, R8/R14 do not contain foreign composites (C1-R2),
R26 needs durable interrupted-run accounting (C1-R9), and a per-commit started marker does
not enforce one-shot dataset use (C1-R4). These are required corrections, not completed fixes.
