// The practice page's check() retry controller (review B-R1), run with DOM, transport and
// parser stubs. The browser regression with real MathLive is in tools/e2e/smoke.mjs.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const path = new URL('../../src/mathtutor/web/static/practice.js', import.meta.url);
const source = readFileSync(path, 'utf8')
  .replace(/^import .*;\r?\n/gm, '')
  .replace(/load\(\);\s*$/, '');

const BUSY = { response: { status: 503, headers: { get: () => '2' } }, data: { error: 'verifier_busy' } };
const PENDING = { response: { status: 409, headers: { get: () => null } }, data: { error: 'submission_pending' } };
const DB_BUSY = { response: { status: 503, headers: { get: () => '1' } }, data: { error: 'database_busy' } };
const LOST = 'lost';

function page(kind = 'expression') {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) {
      elements.set(id, { dataset: { sessionId: '1' }, content: 'csrf', addEventListener() {}, hidden: false });
    }
    return elements.get(id);
  };
  const radios = [{ value: 'a', disabled: false }, { value: 'b', disabled: false }];
  let uuid = 0;
  const context = vm.createContext({
    MathfieldElement: class {},
    ComputeEngine: class {},
    document: {
      getElementById: element,
      querySelector: (sel) => (sel.includes(':checked') ? context.checkedRadio : element(sel)),
      querySelectorAll: () => radios,
    },
    crypto: { randomUUID: () => `uuid-${(uuid += 1)}` },
    radios,
    checkedRadio: null,
  });
  vm.runInContext(source, context);
  vm.runInContext(`
    item = { session_item_id: 1, revision: 0, answer_kind: '${kind}', allowed_actions: ['submit', 'skip'],
             tries_left: 3 };
    field = '${kind}' === 'choice' ? null : { value: 'x', readOnly: false };
    globalThis.sent = [];
    globalThis.replies = [];
    sleep = async () => {};
    render = () => {};
    load = async () => {};
    buildAnswer = () => (item.answer_kind === 'choice'
      ? { kind: 'choice', choice_id: selectedChoice() }
      : { kind: 'expression', latex: field.value, mathjson: field.value });
    api = async (_path, body) => {
      sent.push(JSON.parse(JSON.stringify(body)));
      const reply = replies.shift() ?? { response: { status: 200, ok: true },
        data: { item, outcome: { status: 'incorrect' } } };
      if (reply === 'lost') throw new TypeError('network');
      return reply;
    };
  `, context);
  return {
    context,
    reply: (...r) => context.replies.push(...r),
    check: () => vm.runInContext('check()', context),
    run: (code) => vm.runInContext(code, context),
  };
}

test('all verifier_busy, then an edit: the visible answer is sent under a new id', async () => {
  const p = page();
  p.reply(BUSY, BUSY, BUSY, BUSY);
  await p.check();
  assert.equal(p.run('field.readOnly'), false, 'unlocked: the server kept nothing');
  p.run("field.value = '2x'");
  await p.check();
  const last = p.context.sent.at(-1);
  assert.equal(last.answer.latex, '2x');
  assert.notEqual(last.submission_id, p.context.sent[0].submission_id);
});

test('a lost reply keeps the answer locked and resends the same id and answer', async () => {
  const p = page();
  p.reply(LOST, BUSY, BUSY, BUSY);
  await p.check();
  assert.equal(p.run('field.readOnly'), true, 'locked while the server may hold it');
  assert.match(p.run("$('error').textContent"), /still being checked/);
  await p.check();
  const ids = new Set(p.context.sent.map((b) => b.submission_id));
  assert.equal(ids.size, 1);
  assert.equal(p.context.sent.at(-1).answer.latex, 'x');
  assert.equal(p.run('field.readOnly'), false, 'unlocked after a definite reply');
});

test('a lost successful reply is replayed, never submitted twice', async () => {
  const p = page();
  p.reply(LOST); // then the default 200
  await p.check();
  assert.equal(p.context.sent.length, 2);
  assert.equal(p.context.sent[0].submission_id, p.context.sent[1].submission_id);
  assert.equal(p.run('pending'), null);
});

test('submission_pending and database_busy are unresolved, not a free retry', async () => {
  for (const reply of [PENDING, DB_BUSY]) {
    const p = page();
    p.reply(reply, reply, reply, reply);
    await p.check();
    assert.equal(p.run('field.readOnly'), true);
    await p.check();
    assert.equal(new Set(p.context.sent.map((b) => b.submission_id)).size, 1);
  }
});

test('the answer is locked while a check is in flight', async () => {
  const p = page();
  p.run(`api = async (_path, body) => {
    globalThis.lockedDuringRequest = field.readOnly;
    return { response: { status: 200, ok: true }, data: { item, outcome: { status: 'incorrect' } } };
  }`);
  await p.check();
  assert.equal(p.context.lockedDuringRequest, true);
});

test('choices: all busy, then another choice is sent under a new id', async () => {
  const p = page('choice');
  p.context.checkedRadio = { value: 'a' };
  p.reply(BUSY, BUSY, BUSY, BUSY);
  await p.check();
  assert.equal(p.context.radios[0].disabled, false);
  p.context.checkedRadio = { value: 'b' };
  await p.check();
  assert.equal(p.context.sent.at(-1).answer.choice_id, 'b');
  assert.notEqual(p.context.sent.at(-1).submission_id, p.context.sent[0].submission_id);
});

test('choices: a lost reply disables the radios until it resolves', async () => {
  const p = page('choice');
  p.context.checkedRadio = { value: 'a' };
  p.reply(LOST, BUSY, BUSY, BUSY);
  await p.check();
  assert.ok(p.context.radios.every((r) => r.disabled));
  await p.check();
  assert.equal(p.context.sent.at(-1).answer.choice_id, 'a');
  assert.ok(p.context.radios.every((r) => !r.disabled));
});
