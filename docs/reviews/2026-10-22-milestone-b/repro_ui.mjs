// Runs the real check() retry controller with DOM, transport and parser stubs.
// This is a controller probe, not a browser/MathLive integration test.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const path = new URL('../../../src/mathtutor/web/static/practice.js', import.meta.url);
const source = readFileSync(path, 'utf8')
  .replace(/^import .*;\r?\n/gm, '')
  .replace(/load\(\);\s*$/, '');

test('B-R1: editing after four verifier_busy replies must submit the visible answer', async () => {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      dataset: { sessionId: '1' }, content: 'csrf', addEventListener() {},
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    MathfieldElement: class {}, ComputeEngine: class {},
    document: { getElementById: element, querySelector: element },
    crypto: { randomUUID: () => 'first-request' },
  });
  vm.runInContext(source, context);
  vm.runInContext(`
    item = { session_item_id: 1, revision: 0, answer_kind: 'expression' };
    field = { value: 'x' };
    globalThis.sent = [];
    globalThis.busyReply = true;
    sleep = async () => {};
    render = () => {};
    buildAnswer = () => ({ kind: 'expression', latex: field.value, mathjson: field.value });
    api = async (_path, body) => {
      sent.push(JSON.parse(JSON.stringify(body)));
      return busyReply
        ? { response: { status: 503, headers: { get: () => '2' } },
            data: { error: 'verifier_busy' } }
        : { response: { status: 200, ok: true },
            data: { item, outcome: { status: 'incorrect' } } };
    };
  `, context);
  await vm.runInContext('check()', context);
  assert.equal(context.sent.length, 4);
  vm.runInContext("field.value = '2x'; busyReply = false;", context);
  await vm.runInContext('check()', context);
  assert.equal(context.sent[4].answer.latex, '2x',
    'the visible answer is 2x, but the controller resends the earlier x');
});
