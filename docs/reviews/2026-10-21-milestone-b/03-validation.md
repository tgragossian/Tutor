# Review validation and reproductions

[Review index](README.md) · [State/UI findings](01-state-and-ui.md) · [Input/storage findings](02-input-and-storage.md)

Date: 2026-10-21. Code: `milestone-b` d428bd7. Platform: Windows, repository Python 3.12 env.
The prior documentation edits were preserved. Production code and content were not changed.

## Existing checks rerun

| Command | Observed result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | 839 passed, 1 skipped, 1 warning; 107.97 s |
| `npm test --prefix tools` | 19 passed |
| `.venv/Scripts/python.exe -m ruff check src tests tools migrations` | Passed |
| `.venv/Scripts/python.exe -m mypy src` | Passed, 38 source files |
| `.venv/Scripts/python.exe -m mathtutor.verify.content_check` | Passed, six problems |

The first sandboxed pytest run hit WinError 5 in pytest's temporary/cache directories and
was stopped. The permitted rerun outside the sandbox produced the complete result above.
The warning is the existing Starlette/httpx TestClient deprecation.
These passes do not establish the correctness of the newly identified edge cases.

## Targeted review probes

Run from the milestone B worktree root:

```sh
uv run pytest docs/reviews/2026-10-21-milestone-b/repro_app.py -q --tb=short --show-capture=no
```

[repro_app.py](repro_app.py) uses temporary SQLite files and the existing spy-pool fixture.
It asserts desired safe behavior and is intentionally outside normal `tests/` collection.
Final observed result: **5 failed**, 1 warning, 12.52 s. Each failure confirms one finding:

| Probe | Observation |
|---|---|
| `test_ba1_*` | Repeated original Skip returns 200 twice, presentation IDs 2 then 3 |
| `test_ba2_*` | Raw nested JSON returns 500, no pool calls |
| `test_ba3_*` | Authentication SELECT under writer contention returns 500 |
| `test_ba4_*` | New statement rendered while database retains the old content version |
| `test_ba5_*` | Format result after Skip returns normally instead of StaleItem |

An earlier probe run was 4 failed/1 passed: 1,100 nested Negate expressions reached controlled
validation. The final parser probe uses 5,000 nested arrays below the 16 KB cap.
Convert the probes into normal regression tests as fixes land. B-A4's new policy may require
adjusting its allowed stale response; B-A5 also needs a real browser response-order test.

## Scope and limits

Inspected app/store/auth/routes/DTOs/browser code, migration/CI/container wiring, content
loading/versioning, verifier dispatch and pool boundaries; concentrated on the new app track.
The entire existing Python suite was run, including verifier tests. This is not a new proof
of mathematical soundness or a complete security audit of vendored libraries.
No fresh browser, Docker, Linux memory-limit, remote CI, generated/dev CLI evaluation or
production tests were run. Keep earlier reviewed accuracy results tied to their original SHA.
The known task 16 volume/migration gap remains a release prerequisite, separate from B-A1–B-A5.
