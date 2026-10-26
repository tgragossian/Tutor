# C design 9: provider assumptions and execution checks

[C design](README.md) · [Open register](../../plans/portfolio-mvp/milestone-c/03-open-decisions.md)

Public documentation checked 2026-10-26. These are documentation observations, not a paid API
probe or confirmation that Thomas's account has access. Recheck at implementation/evaluation.

## Models and output

- Anthropic lists `claude-haiku-5-5` and `claude-sonnet-5-5`, text/image input and adaptive
  thinking. Record requested and returned model IDs and supported effort settings in each run.
  [Official model overview](https://platform.claude.com/docs/en/models/overview).
- Keep prices in a versioned execution config, not copied estimates across Markdown files.
  Account access, input/output/reasoning costs and feature compatibility remain C-O5/C-P1 checks.
- Structured output can still return refusals or truncated output. Validate the stop reason,
  schema and application constraints; HTTP 200 alone is not a valid hint. Do not raise token
  limits automatically when output truncates. [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
- The Generator adapter must expose usage, request ID, stop reason and retry/timeout outcome;
  test SDK configuration against [the official SDK](https://github.com/anthropics/anthropic-sdk-python).

## Uploads

- Vision lists JPEG, PNG, GIF and WebP; HEIC needs conversion before the model call. Encoded
  request limits differ from the app's raw-file limit. [Vision documentation](https://platform.claude.com/docs/en/build-with-claude/vision).
- PDF is a separate document input path, not an image MIME type. Pin the chosen model/input
  combination, limits and page behavior with fixtures. [PDF support](https://platform.claude.com/docs/en/build-with-claude/pdf-support).
- Prefer direct inline bytes over persistent Files API objects for C3's local-cleanup contract.
  Do not accept user-controlled URLs for server-side downloading in the upload endpoint.

## Retention

Anthropic describes standard API deletion within 30 days, with exceptions including longer
retention services such as Files API, contractual arrangements, policy enforcement and law.
Local cleanup cannot guarantee deletion of provider copies. Do not promise zero retention
without account-specific evidence. [Official retention policy](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data).

The upload/help UI must explain provider processing and local retention in plain language.
No names, account email or unnecessary identifiers go into prompts. Discard unconfirmed
transcriptions locally after confirmation/cancellation; confirmed text remains private and deletable.
