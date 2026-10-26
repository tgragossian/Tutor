# C-R4/C-R5: own problems and upload lifecycle

[Review](README.md) · [Amended intake](../../superpowers/specs/2026-10-26-milestone-c/04-own-problems.md)

## Solver boundary

The current [pool](../../../src/mathtutor/verify/pool.py) dispatches grading requests, and
the [content schema](../../../src/mathtutor/content/schema.py) expects a known reference
answer. “Derivatives supported” describes today's bank, not an arbitrary-word-problem solver.
Natural language, diagrams, implicit relations, parameters and evaluation points require
different tasks. Computing `diff` on a misread expression can be internally consistent and wrong.

The confirmation UI must expose the executable interpretation: operation, source expression,
variable, derivative order and domain. The first gradable subset should be explicit first
derivatives of one real variable with supported syntax and provable domain metadata.
This narrower admission rule does not prevent other problems receiving labeled hints.
Do not default a singular/logarithmic/radical task to all reals just because the current
answer schema has a real-domain default. Unknown differentiability/domain means hints-only.

New bounded solve jobs, deterministic output serialization and content-style validation are
required. References must not rely on an LLM answer. A SymPy-generated reference is not an
independent validation of the confirmed transcription; evaluate both boundaries separately.
Version own problems immutably after use. Changing the statement must not change old attempts.

## Upload boundary

“Deleted immediately” is incomplete: the app, multipart spooling, reverse proxy, image/PDF
conversion, logs, provider and backups are distinct storage surfaces. Memory-only also does
not mean secure erasure from RAM/swap. [Provider evidence](../../superpowers/specs/2026-10-26-milestone-c/09-provider-evidence.md)
records standard API retention and the separate Files API lifecycle.

Provider vision supports JPEG/PNG/GIF/WebP, so HEIC requires an explicit conversion step.
A 10 MB compressed image/PDF can expand well beyond 10 MB; validate decoded dimensions,
pages, extracted problem count, encoded request size and total work before paid inference.
Bound decoder work outside the web process; reject corrupt/password-protected inputs.
The app's [16 KiB request body limit](../../../src/mathtutor/web/logging.py) must be changed
only for intake, not globally relaxed.

Use direct request bytes, avoid persistent provider uploads, and document local cleanup on
success, failure, cancellation and crash. Only confirmed text is durable; names in confirmed
text still need removal or explicit user editing. The UI must describe provider processing,
not imply local deletion also deletes all provider copies.

## Verification needed

Golden typed tasks; unsupported task downgrade; ambiguous variable/domain confirmation;
oversized decoded image; corrupt/encrypted PDF; HEIC conversion; page/count caps; disconnect
cleanup; cross-user access; deletion during a pending solve; no raw upload in logs/backups.
OCR evaluation checks task structure/constraints as well as mathematical equivalence.
