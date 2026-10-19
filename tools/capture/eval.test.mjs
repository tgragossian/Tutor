import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatRow, serializeRows, validateEntries } from './eval.mjs';

const base = {
  id: 'd-1',
  family: 'openstax-c1-3.6-221',
  category: 'tricky',
  problem_id: 'openstax-c1-3.6-221',
  latex: '18x(3x^2+1)^2',
  label: 'correct',
  rationale: 'as stored',
  reviewer: 'pending',
};

test('validateEntries rejects unknown fields, blanks, bad labels and duplicates', () => {
  assert.throws(() => validateEntries([{ ...base, strict_domian: true }]), /d-1.*strict_domian/);
  assert.throws(() => validateEntries([{ ...base, rationale: ' ' }]), /d-1.*rationale/);
  assert.throws(() => validateEntries([{ ...base, label: 'maybe' }]), /label/);
  assert.throws(() => validateEntries([base, base]), /duplicate/);
  assert.throws(() => validateEntries([{ ...base, keys: ['x'] }]), /exactly one of latex/);
  const { problem_id, ...noProblem } = base;
  assert.throws(() => validateEntries([noProblem]), /problem_id or inline_spec/);
  assert.deepEqual(validateEntries([base]), [base]);
});

test('formatRow splices the captured MathJSON text verbatim and keeps the raw input', () => {
  const big = '{"num":"1234567890123456789012345678901234567890"}';
  const line = formatRow(base, { latex: '18x\\left(3x^2+1\\right)^2', mathjson: `["Add",${big},0.1]` });
  assert.ok(line.includes(`"mathjson":["Add",${big},0.1]`));
  const row = JSON.parse(line);
  assert.equal(row.raw_latex, '18x(3x^2+1)^2');
  assert.equal(row.answer.latex, '18x\\left(3x^2+1\\right)^2');
  assert.equal('latex' in row, false);
  assert.equal(row.category, 'tricky'); // CI checks spec 08 coverage from the JSONL
  assert.deepEqual(Object.keys(row), [...Object.keys(row)].sort());
});

test('formatRow records keys and choices, and compiles inline specs', () => {
  const { latex, problem_id, ...rest } = base;
  const keyed = JSON.parse(
    formatRow({ ...rest, problem_id, keys: ['x', '^'] }, { latex: 'x^{}', mathjson: '"x"' }),
  );
  assert.deepEqual(keyed.raw_keys, ['x', '^']);
  assert.equal(keyed.answer.mathjson, 'x');
  const choice = JSON.parse(formatRow({ ...rest, problem_id, choice_id: 'a' }, null));
  assert.deepEqual(choice.answer, { choice_id: 'a' });
  const inline = JSON.parse(
    formatRow({ ...rest, latex: 'x', inline_spec: { kind: 'expression', latex: 'x+1' } }, {
      latex: 'x',
      mathjson: '"x"',
    }),
  );
  assert.deepEqual(inline.inline_spec.mathjson, ['Add', 'x', 1]);
});

test('formatRow rejects captured text that is not JSON', () => {
  assert.throws(() => formatRow(base, { latex: 'x', mathjson: '[' }));
});

test('serializeRows ends with one LF and no CR', () => {
  assert.equal(serializeRows(['{"a":1}', '{"b":2}']), '{"a":1}\n{"b":2}\n');
});
