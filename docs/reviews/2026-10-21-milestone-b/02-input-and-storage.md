# Input and storage findings

[Review index](README.md) · [Reproduction probes](repro_app.py)

## B-A2 (P2): handle JSON parser depth before structural validation

Owner: [api.py](../../../src/mathtutor/web/api.py), lines 172–175;
[jsonio.py](../../../src/mathtutor/jsonio.py), `loads_exact()`.

The submit route calls Python's JSON parser before Pydantic and `check_structure()`, but
catches only ValueError/ValidationError. A raw request with 5,000 nested arrays in `mathjson`
fits below 16 KB and returns 500 `Internal Server Error`; no verifier request is made.
The parser's recursion failure escapes before the iterative 30-level MathJSON limit runs.
The user receives an infrastructure failure instead of an input rejection, outside the worker.
A shallower 1,100-level Negate input was rejected without 500; that did not establish the limit.

Fix: bound/reject parser depth and handle recursion failures at the raw JSON boundary with a
controlled JSON error. Preserve exact decimals and duplicate-key checks. Do not raise the
process recursion limit as a workaround. Normalize errors before attempting further traversal.
Regression: raw byte requests below the cap with pathological list/object nesting, valid
ordinary input and existing node/depth boundaries. Ensure the pool is never called on rejection.
Probe: `test_ba2_*`; its broad non-500 assertion should become the chosen precise error contract.

## B-A3 (P2): map lock contention outside practice write transactions

Owner: [db.py](../../../src/mathtutor/store/db.py), lines 31–35;
[auth.py](../../../src/mathtutor/application/auth.py), lines 88–101;
[security.py](../../../src/mathtutor/web/security.py), lines 69–79.

Every SQLite transaction, including a SELECT for authentication, starts `BEGIN IMMEDIATE`.
With a competing writer held beyond the 5-second busy timeout, authenticated `GET /api/auth/me`
returns an unstructured 500. `AuthService.resolve()` is outside PracticeService's `_tx()`
handler, as are other reads/replay checks. Therefore the advertised lock-to-Busy conversion
covers only some paths. Existing submission-race tests call the service without HTTP auth.
The probe uses a real SQLite connection holding a write transaction; it changes no user data.

Fix: normalize lock/busy errors consistently at service/dependency boundaries and return 503
with the retry contract. Review whether read-only paths should acquire write locks at all,
and move password verification outside write-lock lifetimes where feasible. Error rendering
must not recursively repeat the same failing database work.
Regression: hold a competing writer through timeout while hitting auth, current/history,
submit and HTML error paths; require controlled responses and recovery once the lock clears.
Probe: `test_ba3_*`; observed auth response was 500 after approximately 5.45 seconds.
