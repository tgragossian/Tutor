# API contracts

[Documentation index](../docs/README.md)

Example request and response bodies for the HTTP API. They are validated against the pydantic models in `src/mathtutor/web/schemas.py` by `tests/unit/test_api_contracts.py`.

Milestone B tasks 13–15 will exercise these contracts through API/browser tests.
Those routes and tests are not implemented yet; current tests validate the DTO examples.

## Submissions (`POST` body, `SubmissionRequest`)

- `examples/submit-expression.json`: an `expression` answer. MathJSON is the raw (non-canonical) form captured from MathLive and Compute Engine 0.151.0 for `6x\cos(3x^2)`.
- `examples/submit-numeric.json`: a `numeric` answer. MathJSON is the captured number `0.785`; trailing zeros are lost in MathJSON (ADR 0002).
- `examples/submit-choice.json`: a `choice` answer. It carries only `choice_id` and never MathJSON or LaTeX.

## Public items (`PublicItem`)

- `examples/item-expression.json`: an expression item with no choices and no precision hint.
- `examples/item-choice.json`: a choice item with `choices` and an author-adapted `source`.

Public items never contain `latex`, `mathjson`, `correct`, `misconceptions`, `review` or `answer`.

## Rules

- `submission_id` is a UUID version 4; `session_item_id` is greater than 0; `item_revision` is at least 0.
- `latex` is at most 2000 characters; `choice_id` matches `^[a-z]$`.
- Unknown fields are rejected.
