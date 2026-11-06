# Answers table: Codex review findings

[Brief](README.md) · [Owner decisions](02-open-decisions.md) · [Deploy runbook](../../ops/runbook-answers-table.md)

Reviewed branch `f9a9cbc` against `3c3d939`: migrations 0006/0007, answer queries,
grading/recovery, help admission, classifier/ledger, web wiring, and related tests.
Targeted tests: 87 passed (`test_classify`, `test_migrations`, `test_service`). No paid
provider call, Docker run, or live database copy was available in this review. A full
pytest run was started and stopped during its slow early portion; no failure had appeared.

| ID | Priority | Finding and consequence | Disposition |
|---|---|---|---|
| A1 | P1 release gate | Migration 0006 rewrites every saved submission and result; the tests use synthetic DB shapes. The branch has no rehearsal result from a copy of the live DB. A successful unit test does not establish row preservation or downgrade safety for that DB. | Before deploy, run 0006/0007 and downgrade on a fresh backup copy; compare row counts and attempt numbers, inspect carried labels, and run `PRAGMA foreign_key_check`. Keep the backup. |
| A2 | P2 | `MistakeClassifier.submit` drops work when its queue is full or on shutdown, with no startup rescan. Such applied wrong answers remain unlabeled unless a later hint labels them. `mistake_counts` excludes them, so the ladder may be lower than the number of mistakes made. | Either add a bounded durable backfill or describe the ladder as counting labeled mistakes; measure and alert on dropped/unlabeled answers. |
| A3 | P2 owner decision | `HelpService._plan` counts delivered hints even after Clear history nulls their text. A repeat click on an open item can show a lock message referring to a hint the student can no longer read. | Adopt decision 1 in [02](02-open-decisions.md), then test clear/replay behavior. |
| A4 | P2 owner decision | The repeat message refers to another try on an exhausted item, and `latest_wrong` can refer to an earlier answer after `unable_to_verify`. The web panel also replaces the visible hint with that message. | Resolve decisions 2–3 in [02](02-open-decisions.md) before deploy. |
| A5 | P2 provenance | Classifier prompt changes affect stored `mistake_type`, but the label stores no classifier prompt/model fingerprint. The hint `prompt_id` includes the classifier template even when no classifier was used. This limits later label audits and conflates hint prompt versions. | Store classifier provenance with the classification result, or document the label as an unaudited heuristic; split prompt fingerprints by call type. |
| A6 | P2 release gate | Structured output from Haiku 5.5 with `effort=low` and the image/browser path have only fake-provider/local coverage. The deploy runbook asks for container smoke but no result is recorded. | One capped real classifier call and container smoke before the host deploy; record the result here. |

Release fixes address A3, A4, and the classifier cap in [02](02-open-decisions.md).
A2 remains a known accuracy limit: the ladder counts labeled mistakes, so a dropped or
failed classifier call can leave a level lower than the student's wrong-answer count.
A5 remains an audit limit: a stored label is an unaudited heuristic; its exact classifier
prompt is not recorded with the label. Neither limit is claimed as a measured outcome.
A1 and A6 require the live backup rehearsal and provider/container checks before deploy.
Thomas checks the disclosure and student flow in the live browser. The existing C1
evaluation does not apply to the new five-try ladder.
