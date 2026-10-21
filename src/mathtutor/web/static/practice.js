// Practice page: renders the current item from the JSON API, submits answers, applies actions.
// Spec 02 and 07. Item content is never in the HTML; it always comes from /current.
import { MathfieldElement } from '/static/vendor/mathlive/mathlive.min.mjs';
import { ComputeEngine } from '/static/vendor/compute-engine/compute-engine.js';

MathfieldElement.fontsDirectory = '/static/vendor/mathlive/fonts';
MathfieldElement.soundsDirectory = null; // no keypress sounds

const root = document.getElementById('practice');
const sessionId = root.dataset.sessionId;
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const $ = (id) => document.getElementById(id);

const KEYS = [
  ['a/b', '\\frac{#@}{#?}'],
  ['xⁿ', '#@^{#?}'],
  ['√', '\\sqrt{#0}'],
  ['sin', '\\sin\\left(#0\\right)'],
  ['cos', '\\cos\\left(#0\\right)'],
  ['tan', '\\tan\\left(#0\\right)'],
  ['ln', '\\ln\\left(#0\\right)'],
  ['eˣ', 'e^{#0}'],
  ['π', '\\pi'],
  ['|x|', '\\left|#0\\right|'],
];

const BUTTONS = { submit: 'check', advance: 'next', skip: 'skip', reveal: 'reveal' };

let item = null;
let field = null;
let pending = null; // {submission_id, body} kept while a submit is retried
let busy = false;

// Same rule as the server's incomplete-input pre-check (ADR 0002).
function incomplete(latex) {
  if (!latex.trim()) return true;
  if (latex.includes('\\placeholder')) return true;
  return /\{\s*\}/.test(latex.replace(/\\[{}]/g, ''));
}

function sleep(seconds) {
  return new Promise((resolve) => setTimeout(resolve, seconds * 1000));
}

async function api(path, body) {
  const options = body === undefined
    ? { headers: { Accept: 'application/json' } }
    : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify(body),
      };
  const response = await fetch(`/api/sessions/${sessionId}${path}`, options);
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { response, data };
}

function showError(message) {
  $('error').textContent = message;
  $('error').hidden = !message;
}

function setFeedback(text, kind) {
  $('feedback').textContent = text;
  $('feedback').className = `feedback ${kind || ''}`;
}

function verdictText(outcome, triesLeft) {
  if (outcome.code) return outcome.message; // format issue: nothing changed
  if (outcome.status === 'correct') return 'Correct';
  if (outcome.status === 'incorrect') {
    return triesLeft > 0 ? `Not quite — try again (${triesLeft} left)` : 'Not quite — no tries left.';
  }
  return "We couldn't check this automatically. You can try another form or skip.";
}

function renderSource(source) {
  const p = $('source');
  p.textContent = '';
  const link = document.createElement('a');
  link.href = source.url.startsWith('https://openstax.org/') ? source.url : '#';
  link.rel = 'noopener';
  const exercise = source.exercise == null ? '' : `, exercise ${source.exercise}`;
  link.textContent = `${source.book}, §${source.section}${exercise}`;
  p.append(link, ` — ${source.license}${source.adapted ? ' (adapted)' : ''}`);
}

function renderKeys() {
  const keys = $('keys');
  keys.textContent = '';
  for (const [label, latex] of KEYS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'key';
    b.textContent = label;
    b.addEventListener('click', () => {
      field.executeCommand(['insert', latex, { focus: true }]);
      updateCheck();
    });
    keys.append(b);
  }
  keys.hidden = false;
}

function renderAnswer(current) {
  const area = $('answer');
  area.textContent = '';
  field = null;
  if (current.answer_kind === 'choice') {
    $('keys').hidden = true;
    const list = document.createElement('fieldset');
    list.className = 'choices';
    for (const choice of current.choices) {
      const label = document.createElement('label');
      label.className = 'choice';
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'choice';
      radio.value = choice.id;
      radio.addEventListener('change', updateCheck);
      const math = new MathfieldElement();
      math.readOnly = true;
      math.value = choice.label_latex;
      label.append(radio, math);
      list.append(label);
    }
    area.append(list);
    return;
  }
  field = new MathfieldElement();
  field.id = 'answer-field';
  field.setAttribute('aria-label', 'Your answer');
  field.mathVirtualKeyboardPolicy = 'auto';
  field.addEventListener('input', updateCheck);
  field.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !$('check').disabled) check();
  });
  area.append(field);
  renderKeys();
}

function selectedChoice() {
  const checked = document.querySelector('input[name="choice"]:checked');
  return checked ? checked.value : null;
}

function updateCheck() {
  if (!item) return;
  const ready = item.answer_kind === 'choice' ? selectedChoice() !== null : !incomplete(field.value);
  $('check').disabled = busy || !ready;
}

function renderButtons(actions) {
  for (const [action, id] of Object.entries(BUTTONS)) {
    $(id).hidden = !actions.includes(action);
  }
  updateCheck();
}

function render(current, revealedLatex) {
  $('loading').hidden = true;
  root.setAttribute('aria-busy', 'false');
  if (current.done) {
    $('problem').hidden = true;
    $('done').hidden = false;
    return;
  }
  const next = current.item;
  const isNew = !item || item.session_item_id !== next.session_item_id;
  item = next;
  $('problem').hidden = false;
  if (isNew) {
    $('statement').innerHTML = next.statement_html; // compiled, trusted content (spec 07)
    renderSource(next.source);
    renderAnswer(next);
    setFeedback('');
    pending = null;
  }
  $('hint').textContent = next.precision_hint || '';
  $('hint').hidden = !next.precision_hint;
  $('revealed').hidden = !revealedLatex;
  if (revealedLatex) $('revealed-field').value = revealedLatex;
  const canSubmit = next.allowed_actions.includes('submit');
  if (field) field.readOnly = !canSubmit;
  $('keys').hidden = !field || !canSubmit;
  $('tries').textContent = `Tries left: ${next.tries_left}`;
  $('tries').hidden = !canSubmit;
  renderButtons(next.allowed_actions);
}

async function load() {
  const { response, data } = await api('/current');
  if (!response.ok) {
    showError(data?.message || 'Could not load this session.');
    return;
  }
  showError('');
  render(data, data.revealed_latex);
}

function buildAnswer() {
  if (item.answer_kind === 'choice') return { kind: 'choice', choice_id: selectedChoice() };
  const latex = field.value;
  // A fresh engine for every parse: parsing is stateful (ADR 0002).
  const mathjson = new ComputeEngine().parse(latex, { form: 'raw' }).json;
  return { kind: item.answer_kind, mathjson, latex };
}

async function check() {
  if (busy) return;
  busy = true;
  updateCheck();
  showError('');
  if (!pending) {
    pending = {
      submission_id: crypto.randomUUID(),
      session_item_id: item.session_item_id,
      item_revision: item.revision,
      answer: buildAnswer(),
    };
  }
  try {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      let result;
      try {
        result = await api('/submit', pending);
      } catch {
        setFeedback('Connection problem. Retrying…');
        await sleep(2);
        continue; // same submission_id, so a retry is never counted twice
      }
      const { response, data } = result;
      if (response.status === 503 || data?.error === 'submission_pending') {
        setFeedback('The checker is busy. Retrying…');
        await sleep(Number(response.headers.get('Retry-After')) || 2);
        continue;
      }
      pending = null;
      if (response.ok) {
        render({ done: false, item: data.item }, null);
        const kind = data.outcome.code ? 'issue' : data.outcome.status;
        setFeedback(verdictText(data.outcome, data.item.tries_left), kind);
      } else if (data?.error === 'stale_item') {
        await load();
      } else {
        showError(data?.message || 'Something went wrong. Please try again.');
      }
      return;
    }
    showError('The checker is still busy. Please try again in a moment.');
  } finally {
    busy = false;
    updateCheck();
  }
}

async function act(action) {
  const { response, data } = await api(`/${action}`, { item_revision: item.revision });
  if (response.ok) {
    if (action !== 'reveal') setFeedback('');
    render(data, data.revealed_latex);
  } else if (data?.error === 'stale_item') {
    await load();
  } else {
    showError(data?.message || 'Something went wrong. Please try again.');
  }
}

$('check').addEventListener('click', check);
$('next').addEventListener('click', () => act('advance'));
$('skip').addEventListener('click', () => act('skip'));
$('reveal').addEventListener('click', () => act('reveal'));
load();
