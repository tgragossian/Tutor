import { test } from "node:test";
import assert from "node:assert/strict";
import { cpSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { compile, serialize, statementHtml } from "./compile.mjs";

const FIX = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "tests", "fixtures", "content");
const GOOD = join(FIX, "good");

test("good fixture compiles with mathjson on every answer and choice", () => {
  const b = compile(GOOD);
  assert.equal(b.schema_version, 2);
  assert.equal(b.topics.length, 3);
  assert.deepEqual(Object.keys(b.tools).sort(), ["compute_engine", "mathlive"]);
  assert.equal(b.problems.length, 2);
  assert.notEqual(b.problems[0].answer.mathjson, undefined);
  for (const c of b.problems[1].answer.choices) assert.notEqual(c.mathjson, undefined);
  assert.equal(b.problems[0].review.date, "2026-01-01");
});

test("duplicate YAML key fails naming the file", () => {
  assert.throws(() => compile(join(FIX, "dup_key")), /bad-001\.yaml.*duplicate|duplicate.*bad-001\.yaml/is);
});

test("double-quoted \\frac fails with single-quote hint", () => {
  assert.throws(
    () => compile(join(FIX, "ff_escape")),
    /bad-001\.yaml.*answer\.latex.*single quotes/,
  );
});

// \n and \P are YAML escapes too, but produce a newline / U+2029 rather than a control
// character: \nu and \Pi would silently become "u" and "i" (review focus 2).
for (const name of ["nu_escape", "pi_escape"]) {
  test(`double-quoted backslash escape fails (${name})`, () => {
    assert.throws(
      () => compile(join(FIX, name)),
      /bad-001\.yaml.*answer\.latex.*single quotes/,
    );
  });
}

test("placeholder answer fails", () => {
  assert.throws(
    () => compile(join(FIX, "placeholder")),
    /bad-001\.yaml.*answer\.latex.*placeholder/,
  );
});

test("output is byte-identical across two runs and keys are sorted", () => {
  const a = serialize(compile(GOOD));
  const b = serialize(compile(GOOD));
  assert.equal(a, b);
  assert.ok(a.endsWith("}\n") && !a.includes("\r"));
  const top = Object.keys(JSON.parse(a));
  assert.deepEqual(top, [...top].sort());
});

test("statement_html renders inline math as read-only math-field", () => {
  assert.equal(statementHtml("$x^2$"), "<math-field read-only>x^2</math-field>");
  assert.equal(
    statementHtml("Find $a<b$ now"),
    "Find <math-field read-only>a&lt;b</math-field> now",
  );
  assert.equal(compile(GOOD).problems[0].statement_html.includes("<math-field read-only>x^3"), true);
});

test("statement raw HTML is escaped", () => {
  const html = statementHtml("<script>alert(1)</script> $x$");
  assert.ok(!html.includes("<script>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("statement links outside openstax.org are dropped", () => {
  const html = statementHtml("[bad](https://evil.example/x) and [ok](https://openstax.org/a)");
  assert.ok(!html.includes("evil.example"));
  assert.ok(html.includes("bad"));
  assert.ok(html.includes('<a href="https://openstax.org/a">ok</a>'));
});

test("misconceptions compile to mathjson in order; unparsable and choice entries are null", () => {
  const dir = mkdtempSync(join(tmpdir(), "mc-"));
  cpSync(GOOD, dir, { recursive: true });
  const f = join(dir, "problems", "pow-001.yaml");
  writeFileSync(
    f,
    readFileSync(f, "utf8") +
      "misconceptions:\n  - '2x  # dropped a factor'\n  - '\\frac{1}{  # broken'\n",
  );
  const p = compile(dir).problems.find((x) => x.id === "pow-001");
  assert.equal(p.misconceptions_mathjson.length, 2);
  assert.notEqual(p.misconceptions_mathjson[0], null);
  assert.equal(p.misconceptions_mathjson[1], null);
});

test("markdown images never render, including nested in a link", () => {
  for (const src of [
    "![x](https://evil.com/t.png)",
    "[![i](https://evil.com/p.png)](https://evil.com)",
    "![x](https://openstax.org/a.png)",
  ]) {
    const html = statementHtml(src);
    assert.ok(!html.includes("<img"), html);
    assert.ok(!html.includes("evil.com/"), html);
  }
});

test("hostile link targets are unwrapped and an unmatched $ stays literal", () => {
  for (const href of [
    "javascript:alert(1)",
    "https://openstax.org.evil.com/",
    "https://openstax.org@evil.com/",
  ]) {
    const html = statementHtml(`[go](${href})`);
    assert.ok(!html.includes("<a"), html);
    assert.ok(!html.includes("href"), html);
  }
  assert.equal(statementHtml("it costs $5"), "it costs $5");
});

test("an escaped dollar is literal and opens no math", () => {
  assert.equal(statementHtml("cost \$5 and \$6"), "cost $5 and $6");
  assert.equal(
    statementHtml("pay \$5 for $x$"),
    "pay $5 for <math-field read-only>x</math-field>",
  );
});
