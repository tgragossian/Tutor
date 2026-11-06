# C1: startup, generation and guard

[C1 debugging](README.md) · [State/cost](02-state-cost.md) · [Evaluation](03-evaluation.md)

## Trace the request

`web/api.py` -> `help/service.py` -> `help/context.py` -> `retrieval/query.py` ->
`retrieval/bm25.py` -> `help/pipeline.py` -> `help/prompts.py` / `help/generator.py` ->
`help/latex_parse.py` / `help/leak_guard.py` -> `help/render.py` -> `web/static/practice.js`.

| Symptom | Owning files and check |
|---|---|
| No help buttons | `web/app.py::_load_help`, `settings.py`, Dockerfile: generator enabled, key configured, corpus and confusion data available |
| Readiness succeeds but help is absent | Help can disable independently of grading/readiness; inspect the safe disable reason and the item's `help` field |
| Irrelevant feedback passages | `help/context.py`, `retrieval/query.py`: attempts are newest first; query must use the latest wrong answer (C1-R6) |
| Retrieval misses | `retrieval/corpus.py`, `retrieval/bm25.py`: corpus hash, roles, tokenization, section boost and top-k IDs |
| Empty/refused/truncated output | `help/generator.py`, `help/pipeline.py`: stop reason, schema validation, bounded repair and fallback |
| Citation rejected | `help/pipeline.py`: cited IDs must belong to the retrieved context; membership alone does not prove semantic support |
| Formula leaks or safe hint blocks | `help/latex_parse.py`, `help/leak_guard.py`: extraction, parsed tree, foreign atoms, checker classification and deadline |
| Display differs from checked text | `help/render.py` and page controller: render only the validated result's math spans |

## Focused offline checks

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_dockerfile.py tests/integration/test_help_api.py -q
.venv\Scripts\python.exe -m pytest tests/unit/help/test_context.py tests/unit/help/test_pipeline.py -q
.venv\Scripts\python.exe -m pytest tests/unit/help/test_latex_parse.py tests/unit/help/test_leak_guard.py tests/integration/test_guard_pool.py -q
```

R1's filesystem test is not a container build; production-image smoke is still required.
For R2, use the real-checker integration tests: an always-`NO_MATCH` fake cannot verify that
canceling foreign terms expose the answer. Foreign substitution coverage is bounded;
unsupported/unchecked variants block. No extracted math does not prove safe prose.

Record safe identifiers: problem/version, request ID, corpus hash, retrieved chunk IDs,
prompt fingerprint, model/config versions, guard reason/counts and elapsed time. Use synthetic
text for reproducible examples; do not add raw student/model text to operational logs.
