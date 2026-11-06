# C1: request state and cost

[C1 debugging](README.md) · [Generation](01-generation.md) · [Evaluation](03-evaluation.md)

## Transaction boundaries

Admission in `help/service.py` binds user, request ID, payload, item/revision and privacy
epoch, and reserves usage. Context/provider/guard work runs outside the write transaction.
Finalization rechecks ownership and state before storing/displaying help and advancing hints.
Usage settlement survives a discarded response; deleting private help must not reset spend.

| Symptom | Owning files and check |
|---|---|
| Retry costs twice or skips a hint | `web/static/practice.js`: retain unresolved UUID/payload; `help/service.py`: replay must not regenerate (R8) |
| Stale hint appears after submit/clear | `help/service.py`, `application/practice.py`: item revision, pending request, privacy epoch and finalize checks |
| Hint ladder looks wrong | `help/service.py::_hint_plan`: latest wrong attempt, `start_hints`, `hint_type`, `hint_attempt_pk`, per-type `hint_counts` |
| New wrong answer reuses old diagnosis | Latest wrong attempt ID must differ before model classification; a repeated hint on the same attempt reuses its type |
| Crash releases possibly billed work | `help/pipeline.py`, `help/generator.py`, `help/service.py`: dispatch recorded before call; uncertain outcome remains reserved (R3) |
| Budget/reset/month discrepancy | `help/ledger.py`, `store/models.py`: reserved + settled + uncertain micro-USD, UTC month and independent usage rows |
| Late result delivered | `help/leak_guard.py`, `help/pipeline.py`: post-worker deadline checks; inspect worker wait separately (R5) |

## Focused offline checks

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/help/test_service.py tests/unit/help/test_ledger.py tests/integration/test_help_races.py -q
.venv\Scripts\python.exe -m pytest tests/unit/help/test_hint_ladder.py tests/unit/help/test_prompt_fingerprint.py -q
npm test --prefix tools
```

Before a wrong answer, level 0 has two start steps; step 2 repeats. Afterward each mistake
type advances only on a delivered hint, up to level 3. Model classification remains fallible.
The prompt fingerprint identifies the instruction set; record corpus/config/model provenance
alongside it. Restart after changing prompt files because templates/hashes are process-cached.

Do not settle uncertain usage to zero merely to clear a quota. Reconcile provider evidence
using the existing ledger workflow. App usage lives in database rows; evaluation usage lives
in a separate per-run journal, described in [evaluation debugging](03-evaluation.md).
