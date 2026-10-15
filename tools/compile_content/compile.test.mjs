import { test } from "node:test";
import assert from "node:assert/strict";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { compile, serialize } from "./compile.mjs";

const FIX = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "tests", "fixtures", "content");
const GOOD = join(FIX, "good");

test("good fixture compiles with mathjson on every answer and choice", () => {
  const b = compile(GOOD);
  assert.equal(b.schema_version, 1);
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
