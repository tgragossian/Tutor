# Milestone B — File map

[Milestone B plan](README.md) · [Structure review](../../../../reviews/2026-10-13/structure.md)

Updated 2026-10-20: tasks 1–9 and R24 complete; reviewed gate and CI pass; merge next.
Tasks 10–16 are planned. [R24 ownership and debugging](r24/01-precheck.md).
Task numbers in the right column identify ownership, not proof of completion.

```text
src/mathtutor/
  jsonio.py                     as_num, loads_exact                                   1
  domain.py                     + VerdictReason, Method enums                         2
  content/schema.py, loader.py  + statement_html, schema_version 2; edge cases       1, 6
  verify/
    types.py                    SubmittedAnswer, Verdict, FormatIssue, CheckRequest,
                                CheckResult, VerifierBusy (no sympy), version         2,7
    structure.py                check_structure (pure Python; web may import)         2
    precheck.py                 precheck (empty / incomplete / exact_required)        2
    translate.py                Constraint, Translated, Rejected, translate           3
    equivalence.py              prove_equal, check_domain, equivalent                 4
    refute.py                   refute (mpmath interval arithmetic)                    5
    numeric.py                  round_matches                                         5
    check.py                    check (dispatcher)                                    5
    content_check.py            CLI: expected answers translate, self-equal, domain   6
    pool.py                     VerifierPool                                          7
    evaluate.py                 CLI: metrics, Wilson intervals, gates                 8
    mutate.py                   deterministic generated regressions                   8
  store/
    db.py                       make_engine (WAL, busy_timeout), make_sessionmaker   10
    models.py                   User, WebSession, StudySession, SessionItem,
                                Submission, AttemptResult, ItemEvent                  10
  application/
    errors.py                   NotFound, Forbidden, StaleItem, InvalidAction, ...  11–12
    auth.py                     AuthService                                          11
    selection.py                next_item_id                                         12
    practice.py                 PracticeService, ItemView, SubmitView                12
  web/
    app.py                      + lifespan, services, routers, error handlers   11, 13
    security.py                 cookies, CSRF dependency, RateLimiter                11
    api.py                      JSON routes                                          13
    pages.py                    HTML routes                                          14
    logging.py                  JSON request logging middleware                      13
    schemas.py                  + auth DTOs, SubmitResponse                          13
    templates/                  login, register, index, practice                     14
    static/practice.js          MathLive field, fetch submit, render feedback        14
    static/app.css              minimal responsive styles                            14
    static/vendor/              mathlive + compute-engine files, SRI in manifest     14
alembic.ini, migrations/         alembic env + 0001_initial                           10
tools/
  compile_content/compile.mjs   + statement_html (markdown-it)                        6
  capture/eval.mjs              capture MathJSON for eval sources                     9
  capture/eval.test.mjs         authoring/serialization tests                         9
  capture/serve.mjs             shared capture server and browser helpers             9
  vendor.mjs                    copy pinned vendor files, write SRI manifest         14
  e2e/smoke.mjs                 Playwright browser smoke                             15
evals/verifier/
  README.md                     how cases are written, captured and reviewed        8
  human/dev.src.yaml            136 reviewed cases (latex, label, rationale)             9
  human/dev.jsonl               136 reviewed captures; matches source exactly         9
  human/REVIEW.md, REVIEW-*.md   linked human-review sheets                            9
  generated/mutations.jsonl     SymPy-generated regression cases                     8
  results/                      README, historical dev-draft.json, dev-b.json   8,9,16
content/problems/*.yaml         14–24 new problems (20–30 total)                    15
docs/ops/security.md            CSP and cookie decisions                              14
docs/verifier/README.md         verifier documentation parent                        16
docs/verifier/supported.md      supported expressions and limitations                16
tools/load/submit_burst.py      named-host 16-user load measurements                 16
tests/unit/                     verify, store, application tests                  1–12
tests/integration/              API, pages, pool, concurrency                     7–14
```

## Dependency checks (tests, task 2 and task 13)

- `test_verify_imports`: importing `mathtutor.verify` modules never imports `mathtutor.web`, `.store` or `.application`.
- `test_web_process_has_no_sympy`: a subprocess builds the app with `create_app` and asserts `"sympy" not in sys.modules`.
