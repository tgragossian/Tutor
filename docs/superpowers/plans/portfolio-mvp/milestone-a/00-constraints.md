# Milestone A — Global constraints and review focus

[Milestone A plan](README.md) · [Spec](../../../specs/2026-10-13-portfolio-core/README.md)

Every task's requirements include this page.

## Global constraints

- **Python 3.12** (`.python-version`). Dependencies via `uv`; every command runs as `uv run ...`. `uv.lock` is committed and CI uses `uv sync --locked`.
- **Node 24** for `tools/` only. The server image never contains Node.
- **Exact pins in `tools/package.json`:** no `^`, `~` or ranges. `package-lock.json` is committed and CI uses `npm ci`.
- **MathLive ≥ 0.111.1.** Never call `getValue('math-json')`; it was removed in 0.111.0. Use a fresh `new ComputeEngine().parse(latex, {form: 'raw'}).json` per parse (CE 0.151.0, ADR 0002).
- **No `eval`, `sympify` or `parse_expr` anywhere.** SymPy isn't a dependency in milestone A.
- **Topic ids:**

  | Topic id | OpenStax section | Order |
  |---|---|---|
  | `derivatives.basic_rules` | 3.3 | 1 |
  | `derivatives.trig` | 3.5 | 2 |
  | `derivatives.chain_rule` | 3.6 | 3 |

- **Answer kinds:** `expression | numeric | choice`.
- **Review statuses:** `human_verified | needs_review`. Only `human_verified` is servable.
- **Choice ids** match `^[a-z]$`. **Problem ids** match `^[a-z0-9][a-z0-9.\-]*$`.
- **`content_version`** = the first 12 hex characters of the SHA-256 of `json.dumps(problem, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, encoded as UTF-8.
- **Source URLs** start with `https://openstax.org/`. Licence string: `CC BY-NC-SA 4.0`.
- **pydantic models** use `model_config = ConfigDict(extra="forbid", frozen=True)`.
- **`mypy --strict`** passes on `mathtutor.domain` and `mathtutor.content`. `ruff check` and `ruff format --check` pass everywhere (line length 100).
- **Environment variables** use the prefix `MATHTUTOR_`. `MATHTUTOR_SECRET_KEY` is required in production and must be ≥ 32 characters. `.env` is never committed.
- **Container:** runs as non-root uid **10001**, app port 8000 is **not** published on the host, and only Caddy publishes 80/443.
- **Markdown:** ≤ 100 lines per file, linked from a parent index; enforced by `tools/check_docs.py`.
- **Commits:** conventional prefixes (`feat:`, `chore:`, `docs:`, `test:`, `spike:`). **No `Co-Authored-By` trailers** (README acknowledgments cover attribution).
- **Line endings:** LF everywhere (`.gitattributes`). The repo lives on Windows/OneDrive and CI runs on Linux.

## Review focus

These are the failure modes most likely to bite that no task's main tests target. Each line names the task that pins it with a test.

1. **A Windows CRLF checkout breaks the compiled-content stale check, or changes hashes.**
   Expected: the same content always gives byte-identical output and the same `content_version`.
   Pinned by: `.gitattributes` in task 1; the determinism and CRLF tests in task 4.
2. **Double-quoted YAML silently corrupts LaTeX.** `"\frac{1}{x}"` becomes a form feed followed by `rac`.
   Expected: compilation fails, naming the file and field and suggesting single quotes.
   Pinned by: the control-character test in task 4.
3. **A misspelt optional field (`strict_domian: true`) is silently ignored**, so the problem is graded with the wrong domain rule.
   Expected: a validation error naming the unknown field.
   Pinned by: the `extra="forbid"` tests in task 3.
4. **Version drift.** The compiler, the captured fixtures and (later) the browser could use different Compute Engine versions and parse the same LaTeX differently.
   Expected: CI fails when they differ.
   Pinned by: the pin-match test in task 2, and the bundle's `tools` metadata check in task 4.
5. **Production starts with no secret or with nothing servable**, and looks healthy.
   Expected: startup fails without a secret, and `/readyz` returns 503 when no problem is servable.
   Pinned by: the task 6 tests.
