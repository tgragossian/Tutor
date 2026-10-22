# Reservation recovery and stored-result integrity

[Review](README.md) · [Interleaving probe](repro_reservation.py) · [State probes](repro_state.py)

## B-R5 (P1): reservation deletion and row-ID reuse

Owners: [practice.py](../../../src/mathtutor/application/practice.py), lines 344–370,
406–415, 433–477; [models.py](../../../src/mathtutor/store/models.py), lines 140–153.

A reservation older than 10 seconds is regraded without claiming exclusive ownership.
If that duplicate gets `VerifierBusy`, `_release()` deletes the shared submission by its
integer primary key, even while the original caller still holds a `_Reservation` for it.
SQLite can reuse the deleted highest row ID: `Submission` has no AUTOINCREMENT protection.
Transaction B checks the original item's revision/state, but never checks that the submission
row still has the original UUID and presentation before inserting its result.

Deterministic reproduction:

1. Alice reserves submission A at revision 0 and remains inside `pool.submit`.
2. Advance the test clock 11 seconds. A duplicate A enters orphan recovery, receives busy,
   and deletes A's submission row.
3. Bob reserves submission B; SQLite reuses the deleted integer key.
4. Alice's original call returns correct. Her presentation becomes answered, but its result
   is stored against **Bob's UUID/presentation**. The probe asserts Alice's UUID and gets Bob's.

This can corrupt another user's history/selection and replayed feedback without any
cross-user authorization bypass. The probe drives real transactions in a temporary database;
the pool and clock are controlled, and Bob pauses after real transaction A.
It demonstrates the interleaving, not its production frequency.

The 3-second checker deadline does not exclude this schedule: pool acquisition/replacement
can warm a worker synchronously with a 120-second ready timeout
([pool.py](../../../src/mathtutor/verify/pool.py), lines 35, 246–247, 323–350).
An aged reservation is therefore not proof that its owner died.

Fix direction: atomically claim/lease recovery with a generation token; only the current
owner may release or finalize a reservation. Validate UUID, presentation and ownership in
transaction B before changing state or storing a result. Never delete another active owner's
reservation on duplicate backpressure. Prevent row-ID aliasing as defense in depth;
AUTOINCREMENT alone would turn this into failure, not restore correct recovery semantics.

Regressions: aged but live request + busy duplicate; format-result cleanup races; another
user reserving between cleanup and completion; duplicate recoveries storing exactly one result.

## B-R2 (P2): preserve the original reservation revision

Owner: [practice.py](../../../src/mathtutor/application/practice.py), lines 344–370;
[Submission](../../../src/mathtutor/store/models.py) does not persist the reserved revision.

Recovery builds `expected_revision` from the new request, while retaining the old answer.
Reserve A at revision 0, let another incorrect answer win revision 0, age A 11 seconds,
then retry A with the now-current revision 1. A is applied, consuming a second try instead
of returning stale. `test_br2_*` reproduces the missing `StaleItem`.

This is explicitly the behavior of [A14](../../superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md).
Review recommendation: amend A14 because it defeats the original race-loss invariant.
Persist the original revision at reservation time; recovery must use that value, regardless
of a retry's body. Define a conservative policy for pre-migration pending rows whose original
revision cannot be reconstructed. Keep completed-result replay idempotent.

Regression: original-revision retry still recovers after a crash; newer-revision retry cannot
revive a losing answer. Cover this alongside B-R5, using a new forward migration.
