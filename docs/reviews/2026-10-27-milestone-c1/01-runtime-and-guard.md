# C1 review: runtime and answer containment

[Review index](README.md) · [Validation](04-validation-and-next-steps.md)

## C1-R1 (P1): ship the help configuration

- Evidence: `Dockerfile:25-27`, `src/mathtutor/settings.py:28`, `web/app.py:180-183`.
  The runtime image copies compiled problems and corpus data, but never `content/help/`.
  Neither the installed package nor Compose supplies `content/help/confusions.json`.
- `_load_help` catches its `FileNotFoundError` and disables help. This affects the normal
  Claude configuration with a key and the scripted e2e configuration. `/readyz` remains
  healthy, so readiness alone can conceal a C1 deployment with no help buttons.
- Reproduction: `test_runtime_image_loads_help` in [Python probes](test_review_probes.py).
  A valid real corpus plus the image's missing configuration path returns `None` and logs
  `help disabled: FileNotFoundError`. This is a filesystem-layout probe, not a Docker build.
- Fix: copy the help data into the runtime image at the configured path. Verify all other
  runtime data dependencies from a clean production image, not a source-directory mount.
- Acceptance: image-based scripted e2e shows enabled controls and produces a cited hint;
  separately verify the intentional help-off mode. Retain an image-content regression.

## C1-R2 (P1): do not pass unchecked foreign expressions

- Evidence: `src/mathtutor/help/leak_guard.py:391-413,509-521`.
  `_substitutable` rejects function names, Greek names and primed symbols; `_check_foreign`
  then assigns the entire candidate `NO_MATCH` without a verifier call.
- On the real chain-rule problem `openstax-c1-3.6-221`, each of these full answers passes:

  ```text
  $18x(3x^2+1)^2+f(x)-f(x)$
  $18x(3x^2+1)^2+\theta-\theta$
  $18x(3x^2+1)^2+y'-y'$
  ```

- Reproduction: `test_answer_plus_canceling_foreign_terms_is_blocked` (three parameters).
  All return `decision='pass'`, `reason='checked'`, `foreign=1`, with zero pool submissions.
  The added terms cancel; this is extracted answer math, not the disclosed prose limitation.
- Fix: classify unresolved composites as `UNCHECKED` and block them. If permitting isolated
  pedagogical symbols, define and test a narrow exception that cannot certify surrounding
  arithmetic. Any supported normalization must stay bounded and inside the guard boundary.
- Acceptance: these cases block for expression and numeric answers; include zero products,
  subscripted symbols and function applications. Safe derivative notation needs explicit tests.
- Ruling impact: R8/R14's single-letter substitutions do not close the general foreign-symbol
  path. Amend the parser/guard plan and tests that currently codify automatic foreign passes.

## C1-R5 (P2): enforce the deadline after worker return

- Evidence: `src/mathtutor/help/leak_guard.py:531-542`, `help/pipeline.py:333-339`.
  Both check the clock before the expensive operation. Neither checks after the last worker
  returns; a final `NO_MATCH` can become `DELIVERED` after the whole-request deadline.
- Reproduction: `test_pipeline_does_not_deliver_after_guard_overruns`. The fake provider
  consumes 14.9 seconds, then the final guard check consumes 2 seconds. The result is
  `delivered` at 16,900 ms against the configured 15-second deadline.
- Fix: recheck the absolute request/guard deadline after every blocking operation and before
  delivery; propagate remaining time to worker admission/execution or add bounded cancellation.
  A post-check prevents late delivery but alone does not provide a hard response-time bound.
- Acceptance: last-candidate, foreign-variant, queue-wait and repair cases obey the same total
  budget. Preserve known provider usage even when discarding a late result.
