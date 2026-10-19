# Content

[Documentation index](../docs/README.md)

Problem content for the tutor: authored YAML in, one compiled JSON bundle out.

- [OpenStax Calculus Volume 1](sources/openstax-calculus-v1.md): the source manifest, licence and attribution.
- [Content and domains contract](../docs/superpowers/specs/2026-10-13-portfolio-core/01-content-and-domains.md): the record shape and domain rules.

## Layout

| Path | What it holds |
|---|---|
| `topics.yaml` | Topic ids, titles, order and OpenStax section |
| `problems/<id>.yaml` | One problem per file, named after its `id` |
| `sources/` | One manifest per source book |
| `compiled/problems.json` | The generated bundle the server loads (committed; never edit by hand) |

## Authoring a problem

1. Create `problems/<id>.yaml`. Transcribed exercises use `openstax-c1-<section>-<exercise>`; author-written items use `adapted-c1-<section>-<slug>`.
2. Fill the fields in `src/mathtutor/content/schema.py`. Unknown fields are rejected, so a typo fails loudly.
3. Put **all LaTeX in single-quoted YAML strings**: `'\frac{1}{x}'`. In double quotes `\f` becomes a form feed and the compiler stops. Inside single quotes, write an apostrophe as `''` (so `f''(x)` in YAML is f'(x)).
4. Declare the expected answer's real domain. Use `exclude` for isolated rational points, for example `exclude: ['0']` for an answer with `1/x`.
5. Transcribed exercises: set `exercise` to the book's number and `url` to the section page. Author-written items: `adapted: true`, `exercise: null`.
6. Start with `review: {status: needs_review, reviewer: '', date: '', notes: '<worked check>'}`. Only a human reviewer sets `human_verified`, with their initials and an ISO date. Only `human_verified` items are served.

### LaTeX that parses differently than it reads

- Compute Engine folds a factor written after `\cos x` into the argument, even with `\,` or `\cdot`: `\cos x\,(x+1)` is cos(x(x+1)).
- Put the trig factor last, `(x+1)\cos x`, or use brackets, `\cos(x)(x+1)`.
- Check the compiled `mathjson` after editing.

## Compiling

```sh
npm run compile --prefix tools   # writes content/compiled/problems.json
uv run python -m mathtutor.verify.content_check  # offline math validation
uv run pytest -q                 # loader and seed-content checks
```

CI recompiles and fails if the committed bundle is out of date. Commit the YAML and the regenerated bundle together.

Milestone B bundles use schema version 2 with compiled `statement_html` and
`misconceptions_mathjson`. CI and Docker builds run the offline mathematical check;
web startup loads the schema without importing SymPy. Six problems exist; expansion is task 15.
