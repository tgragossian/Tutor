// The practice page's help buttons, panel and stale-response rules (milestone C1 task 13),
// run with DOM and transport stubs as in practice_controller.test.mjs.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const path = new URL('../../src/mathtutor/web/static/practice.js', import.meta.url);
const source = readFileSync(path, 'utf8')
  .replace(/^import .*;\r?\n/gm, '')
  .replace(/load\(\);\s*$/, '');

class FakeElement {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.hidden = false;
    this.disabled = false;
    this.dataset = { sessionId: '1' };
    this.content = 'csrf';
    this.attributes = {};
    this._text = '';
    this.innerHTML = '';
    this.value = '';
  }
  get textContent() { return this._text; }
  set textContent(value) { this._text = value; this.children = []; }
  addEventListener() {}
  setAttribute(name, value) { this.attributes[name] = value; }
  append(...nodes) { this.children.push(...nodes); }
  get text() {
    return this.textContent + this.children.map((c) => (typeof c === 'string' ? c : c.text)).join('');
  }
  find(tag) {
    const hits = [];
    for (const c of this.children) {
      if (typeof c === 'string') continue;
      if (c.tagName === tag) hits.push(c);
      hits.push(...c.find(tag));
    }
    return hits;
  }
}

const HELP = {
  enabled: true,
  types: ['hint', 'feedback', 'explain'],
  confusions: [{ id: 'why_multiply_inside', label: 'Why do I multiply by the inner derivative?' }],
  hint_level: 1,
};
const SOURCE = {
  label: '3.6 The Chain Rule',
  url: 'https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule',
  license: 'CC BY-NC-SA 4.0',
};
const reply = (over = {}) => ({
  response: { status: 200, ok: true },
  data: {
    request_id: 'x', status: 'delivered', session_item_id: 1, item_revision: 0, help_seq: 1,
    hint_level: 1, html: '<p>Name the outer function.</p>', sources: [SOURCE], ...over,
  },
});

function page({ help = HELP } = {}) {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, new FakeElement());
    return elements.get(id);
  };
  let uuid = 0;
  const context = vm.createContext({
    MathfieldElement: class {},
    ComputeEngine: class {},
    document: {
      getElementById: element,
      querySelector: element,
      querySelectorAll: () => [],
      createElement: (tag) => new FakeElement(tag),
    },
    crypto: { randomUUID: () => `uuid-${(uuid += 1)}` },
  });
  vm.runInContext(source, context);
  context.help = help;
  vm.runInContext(`
    item = { session_item_id: 1, revision: 0, answer_kind: 'expression', tries_left: 2,
             allowed_actions: ['submit', 'skip'], help };
    field = { value: 'x', readOnly: false };
    globalThis.sent = [];
    globalThis.replies = [];
    sleep = async (s) => { (globalThis.slept ??= []).push(s); };
    helpApi = async (body) => {
      sent.push(JSON.parse(JSON.stringify(body)));
      return replies.shift();
    };
    renderHelpButtons();
  `, context);
  return {
    context,
    el: element,
    reply: (...r) => context.replies.push(...r),
    run: (code) => vm.runInContext(code, context),
  };
}

test('buttons hidden when help null', () => {
  const p = page({ help: null });
  for (const id of ['help-hint', 'help-feedback', 'help-explain']) {
    assert.equal(p.el(id).hidden, true, id);
  }
  assert.equal(p.el('help-controls').hidden, true);
});

test('hint and explain show with help; the explain select lists the confusions', () => {
  const p = page({ help: { ...HELP, types: ['hint', 'explain'] } });
  assert.equal(p.el('help-hint').hidden, false);
  assert.equal(p.el('help-explain').hidden, false);
  assert.equal(p.el('help-feedback').hidden, true);
  p.run('openExplain()');
  const options = p.el('help-confusion').children;
  assert.deepEqual(options.map((o) => o.value), ['why_multiply_inside']);
  assert.equal(options[0].textContent, 'Why do I multiply by the inner derivative?');
});

test('feedback button only after wrong answer', () => {
  // The server offers "feedback" only once the item has a wrong attempt.
  const without = page({ help: { ...HELP, types: ['hint', 'explain'] } });
  assert.equal(without.el('help-feedback').hidden, true);
  const p = page();
  p.run("lastOutcome = { status: 'incorrect' }; renderHelpButtons()");
  assert.equal(p.el('help-feedback').hidden, false);
  p.run("lastOutcome = { status: 'correct' }; renderHelpButtons()");
  assert.equal(p.el('help-feedback').hidden, true);
  p.run("lastOutcome = { code: 'incomplete' }; renderHelpButtons()");
  assert.equal(p.el('help-feedback').hidden, true);
});

test('server html inserted, source link uses server url only', async () => {
  const p = page();
  p.reply(reply({ html: '<p>Name the <math-field read-only>x</math-field>.</p>' }));
  await p.run("askHelp('hint')");
  assert.equal(p.el('help-body').innerHTML.includes('<math-field read-only>x</math-field>'), true);
  const links = p.el('help-sources').find('a');
  assert.equal(links.length, 1);
  assert.equal(links[0].href, SOURCE.url);
  assert.equal(links[0].rel, 'noopener');
  assert.equal(p.el('help-sources').text, 'OpenStax Calculus Vol. 1, 3.6 The Chain Rule ↗ · CC BY-NC-SA 4.0');
  assert.equal(p.el('help-panel').hidden, false);
  assert.equal(p.el('help-hint').disabled, false, 'enabled again after a terminal status');
});

test('source line does not repeat the book name', async () => {
  const p = page();
  const label = 'Calculus Volume 1, 3.6 The Chain Rule';
  p.reply(reply({ sources: [{ ...SOURCE, label }] }));
  await p.run("askHelp('hint')");
  assert.equal(p.el('help-sources').text, `${label} ↗ · CC BY-NC-SA 4.0`);
});

test('item change resets busy and re-enables the buttons; the old reply is dropped', async () => {
  const p = page();
  let release;
  p.context.hold = new Promise((resolve) => { release = resolve; });
  p.run('helpApi = async () => { await hold; return replies.shift(); }');
  p.reply(reply());
  const first = p.run("askHelp('hint')");
  assert.equal(p.el('help-hint').disabled, true);
  p.run('renderAnswer = () => {}; renderSource = () => {}');
  p.run("render({ done: false, item: { ...item, session_item_id: 9 } }, null)");
  assert.equal(p.run('helpBusy'), false);
  assert.equal(p.el('help-hint').disabled, false);
  release();
  await first;
  assert.equal(p.el('help-body').innerHTML, '');
  assert.equal(p.run('helpBusy'), false);
});

test('a non-openstax source url is not linked', async () => {
  const p = page();
  p.reply(reply({ sources: [{ ...SOURCE, url: 'javascript:alert(1)' }] }));
  await p.run("askHelp('hint')");
  assert.equal(p.el('help-sources').find('a').length, 0);
});

test('stale response ignored', async () => {
  for (const over of [{ session_item_id: 2 }, { item_revision: 5 }]) {
    const p = page();
    p.reply(reply(over));
    await p.run("askHelp('hint')");
    assert.equal(p.el('help-body').innerHTML, '', JSON.stringify(over));
  }
  const p = page();
  p.run('helpShownSeq = 3');
  p.reply(reply({ help_seq: 2 }));
  await p.run("askHelp('hint')");
  assert.equal(p.el('help-body').innerHTML, '');
  // a reply that lands after the item changed is dropped
  const q = page();
  q.run('helpApi = async () => { clearHelp(); return replies.shift(); }');
  q.reply(reply());
  await q.run("askHelp('hint')");
  assert.equal(q.el('help-body').innerHTML, '');
});

test('panel cleared on advance, correct answer and reveal', async () => {
  const p = page();
  p.reply(reply());
  await p.run("askHelp('hint')");
  assert.notEqual(p.el('help-body').innerHTML, '');
  p.run('clearHelp()');
  assert.equal(p.el('help-body').innerHTML, '');
  assert.equal(p.el('help-panel').hidden, true);
  assert.equal(p.el('help-sources').children.length, 0);
  // render() of a new item, of a correct outcome and of a reveal clears it as well
  const codes = [
    'render({ done: false, item: { ...item, session_item_id: 9 } }, null)',
    "render({ done: false, item: { ...item, allowed_actions: ['advance'] } }, null)",
    "render({ done: false, item: { ...item, allowed_actions: ['advance'] } }, 'x')",
  ];
  for (const code of codes) {
    const q = page();
    q.run('renderAnswer = () => {}; renderSource = () => {}');
    q.reply(reply());
    await q.run("askHelp('hint')");
    q.run(code);
    assert.equal(q.el('help-body').innerHTML, '', code);
  }
});

test('same request id on poll', async () => {
  const p = page();
  p.reply(
    { response: { status: 202, ok: true }, data: reply({ status: 'pending', html: null, sources: [] }).data },
    reply(),
  );
  await p.run("askHelp('hint')");
  assert.equal(p.context.sent.length, 2);
  assert.equal(p.context.sent[0].help_request_id, p.context.sent[1].help_request_id);
  assert.equal(JSON.stringify(p.context.slept), '[2]');
  assert.equal(p.el('help-body').innerHTML.includes('outer'), true);
});

test('a second click while a request is open sends nothing', async () => {
  const p = page();
  p.reply(reply());
  const first = p.run("askHelp('hint')");
  const second = p.run("askHelp('hint')");
  await Promise.all([first, second]);
  assert.equal(p.context.sent.length, 1);
});

test('fixed messages show; a failure never shows raw error text', async () => {
  const p = page();
  p.reply(reply({ status: 'unavailable', html: '<p>Hints are unavailable right now.</p>', sources: [] }));
  await p.run("askHelp('hint')");
  assert.equal(p.el('help-body').innerHTML, '<p>Hints are unavailable right now.</p>');
  const limited = page();
  limited.reply({
    response: { status: 429, ok: false },
    data: { error: 'help_limited', message: "You've reached the help limit for now." },
  });
  await limited.run("askHelp('hint')");
  assert.equal(limited.el('help-message').textContent, "You've reached the help limit for now.");
  const broken = page();
  broken.reply({ response: { status: 500, ok: false }, data: { message: 'Traceback: secret' } });
  await broken.run("askHelp('hint')");
  assert.equal(broken.el('help-message').textContent.includes('Traceback'), false);
  assert.notEqual(broken.el('help-message').textContent, '');
  assert.equal(broken.el('help-hint').disabled, false);
});

test('explain sends the chosen confusion; hint sends none', async () => {
  const p = page();
  p.reply(reply(), reply());
  p.el('help-confusion').value = 'why_multiply_inside';
  await p.run("askHelp('explain')");
  assert.equal(p.context.sent[0].confusion, 'why_multiply_inside');
  assert.equal(p.context.sent[0].help_type, 'explain');
  await p.run("askHelp('hint')");
  assert.equal(p.context.sent[1].confusion, null);
  assert.equal(p.context.sent[1].item_revision, 0);
});
