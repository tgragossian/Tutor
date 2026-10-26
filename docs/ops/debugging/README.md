# Debugging tree

[Operations](../README.md) · [Documentation](../../README.md)

Start with the failing layer; follow one child to the owning file and smallest useful check.
Paths in child pages are relative to the active worktree root.

```text
Debugging
  01-app.md          Accounts → session state → API → MathLive
  02-release.md      Database readiness → container → CI → host
  Milestone B/r24/   Decimal precision → precheck → release capture
  Evaluation guide  Labels → capture → metrics → gates
  Milestone C/      Planned retrieval → help guard → model/fallback → A/B evidence
```

| Symptom | Start here |
|---|---|
| App will not start locally | [Development setup](../development.md) |
| Login, CSRF, stale revisions, tries or feedback | [Application path](01-app.md) |
| Uneditable field, missing assets or CSP errors | [Application path](01-app.md#mathlive-and-pages) |
| `/readyz` 503, Docker smoke or deploy failure | [Release path](02-release.md) |
| Decimal length/value disagreement | [R24 precheck](../../superpowers/plans/portfolio-mvp/milestone-b/r24/01-precheck.md) |
| Wrong mathematical verdict or domain abstention | [Verifier file map](../../superpowers/plans/portfolio-mvp/milestone-b/01-file-map.md) |
| Evaluation gate disagreement | [Evaluation guide](../../../evals/verifier/README.md) and [reviewed result](../../../evals/verifier/results/README.md) |
| Problem does not load or is not served | [Content authoring](../../../content/README.md) |
| Future hints, citations, leakage, fallback or GPU costs | [C/LoRA design checklist](../../superpowers/plans/portfolio-mvp/milestone-c/04-debugging.md) (not implemented) |

[Execution status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)
owns progress. [Evidence](../../superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
owns recorded checks. Debugging pages explain where to look; they do not establish a pass.
