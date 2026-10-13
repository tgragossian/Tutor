# Task 4: Content compiler and loader

[Milestone A plan](../README.md) · [Spec 01](../../../../specs/2026-10-13-portfolio-core/01-content-and-domains.md)

**Files:**
- Create:
  - `tools/compile_content/compile.mjs`, `tools/compile_content/compile.test.mjs`
  - `content/topics.yaml`
  - `src/mathtutor/content/loader.py`
  - `tests/fixtures/content/` (`good/`, `dup_key/`, `ff_escape/` each holding a `topics.yaml` + `problems/*.yaml`; `bundles/*.json` for the loader cases)
  - `tests/unit/test_content_loader.py`
- Modify:
  - `tools/package.json`: add the script `"compile": "node compile_content/compile.mjs ../content ../content/compiled/problems.json"`
  - `.github/workflows/ci.yml`: add the job `node`

**Interfaces:**
- Consumes: the `ContentBundle` and `Problem` models from task 3, and the parse call from ADR 0002.
- Produces:
  - **Node:**
    - `export function compile(contentDir: string): Bundle`
    - The CLI writes the bundle as JSON with keys sorted recursively, a 2-space indent, LF line endings and a final newline.
  - **Python** (in `mathtutor.content.loader`):
    - `class ContentError(Exception)`, whose message lists **every** problem, each line `"<problem id or file>: <field>: <reason>"`
    - `def content_version(problem: Mapping[str, Any]) -> str`, the 12-hex rule from the constraints
    - `@dataclass(frozen=True) class LoadedContent: bundle: ContentBundle; versions: dict[str, str]; bundle_version: str`
      - `bundle_version` = `content_version` applied to the whole bundle dict
    - `def load_bundle(path: Path) -> LoadedContent`
    - `def servable(content: LoadedContent) -> list[Problem]`: only `human_verified` problems, sorted by (topic order, difficulty, id)

**`content/topics.yaml`:** the three topics from the constraints table. Each has the fields `topic_id`, `title`, `order` and `section`.

**Compiler behaviour:**
- Read `topics.yaml` and `problems/*.yaml`, with files in sorted order.
- Parse with `yaml` and `{uniqueKeys: true}` using the core schema, so dates stay strings.
- Reject any string containing a control character in U+0000–U+001F other than `\n`. The error names the file and field and says: "use single quotes for LaTeX".
- For the answer's `latex` and every choice's `latex`, attach `mathjson` from the non-canonical parse.
  - If the result is `"Nothing"` or contains an `"Error"` head, raise an error naming the file and field.
- `tools` = the installed versions of `mathlive` and `@cortex-js/compute-engine`, read from `node_modules/*/package.json`.
- The compiler does **not** validate the schema. pydantic is the only schema authority.

**Loader checks:**
- Each check below adds one line to the `ContentError`. Problems are collected rather than stopping at the first one.
  - pydantic validation errors, mapped to `id: field: msg`
  - duplicate problem id
  - a `topic` not found in `topics`
  - `bundle.tools` differing from the versions in `tests/fixtures/mathjson/captured.json`
    - This is checked **in a test**, not in `load_bundle`, because the fixture isn't shipped in the image.
- Translator-based checks are milestone B (README, "Deferred").

- [ ] **Step 1: Write the failing tests.**

```js
// compile.test.mjs (node:test)
test("good fixture compiles with mathjson on every answer and choice", ...)
test("duplicate YAML key fails naming the file", () => assert.throws(() => compile(DUP), /dup_key.*duplicate/i))
test("double-quoted \\frac fails with single-quote hint", () => assert.throws(() => compile(FF), /single quotes/))
test("placeholder answer fails", ...)
test("output is byte-identical across two runs and keys are sorted", ...)
```

```python
# test_content_loader.py
def test_good_bundle_loads(): c = load_bundle(GOOD); assert len(c.bundle.problems) == 2
def test_content_version_ignores_key_order_and_changes_on_edit(): ...
def test_crlf_bundle_same_versions(tmp_path):        # review focus 1
    write_bytes(tmp_path / "b.json", GOOD.read_bytes().replace(b"\n", b"\r\n"))
    assert load_bundle(tmp_path / "b.json").versions == load_bundle(GOOD).versions
def test_errors_are_collected(): # bundle with duplicate id AND unknown topic
    msg = str(raises(ContentError, load_bundle, BAD_TWO))
    assert "duplicate" in msg and "unknown topic" in msg
def test_needs_review_loaded_but_not_servable(): ...
def test_servable_order_is_topic_then_difficulty_then_id(): ...
def test_compiled_tools_match_captured_meta(): ...   # review focus 4, runs on content/compiled
```

- [ ] **Step 2:** Run `npm test --prefix tools` and `uv run pytest tests/unit/test_content_loader.py -q`. Expected: both FAIL.
- [ ] **Step 3: Implement** `compile.mjs` and `loader.py` as specified above.
- [ ] **Step 4:** Run `npm run compile --prefix tools`.
  - This writes `content/compiled/problems.json` with three topics and zero problems. Commit that file.
  - Then rerun both test commands. Expected: PASS.
- [ ] **Step 5: CI job `node`.**
  - `actions/setup-node` with Node 24, then `npm ci --prefix tools` → `npm test --prefix tools` → `npm run compile --prefix tools` → `git diff --exit-code content/compiled`.
  - The last step fails CI whenever someone edits YAML without recompiling.
- [ ] **Step 6: Commit** with the message `feat: content compiler (Node) and validated loader`.
