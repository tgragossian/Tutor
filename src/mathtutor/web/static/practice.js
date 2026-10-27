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

const DONE_MESSAGES = {
  all_correct: "You've answered every problem in these topics correctly.",
  session_complete: "You've worked through every problem in these topics.",
};

// Typing a function name inserts its parentheses with the cursor inside: "sinx" → sin(x).
const FUNCTIONS = ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'arcsin', 'arccos', 'arctan', 'ln', 'log', 'exp'];

function functionShortcuts(defaults) {
  const shortcuts = { ...defaults };
  // Drop longer names that start with a function (sinh, cosh, …): unsupported, and while they
  // exist MathLive waits before expanding "sin", which breaks the "(" handling below.
  for (const key of Object.keys(shortcuts)) {
    if (FUNCTIONS.some((f) => key !== f && key.startsWith(f))) delete shortcuts[key];
  }
  for (const f of FUNCTIONS) shortcuts[f] = `\\${f}\\left(#?\\right)`;
  return shortcuts;
}

// A "(" typed straight after a function name would nest a second pair: sin((x)). Swallow it
// while the cursor sits in the function's still-empty argument.
function skipRedundantParen(event) {
  if (event.key !== '(' || !field) return;
  const before = field.getValue(0, field.position);
  const emptyArgument = /\\left\(\\placeholder\{\}\\right\)/.test(field.value);
  if (emptyArgument && /\\placeholder\{\}$/.test(before)) event.preventDefault();
}

let item = null;
let field = null;
let pending = null; // the submit body being retried, under one submission_id
// True once the server may hold `pending` (a lost reply, or "still being checked"). Until a
// definite reply arrives the answer stays locked and Check resends the same body, so the
// visible answer is always the one being checked and nothing counts twice (review B-R1).
let unresolved = false;
let lastOutcome = null; // the latest check result for the shown item (null after a reload)
let busy = false; // one check or action at a time; every button is disabled meanwhile

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
  field.addEventListener('keydown', skipRedundantParen, { capture: true });
  field.addEventListener('input', updateCheck);
  field.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !$('check').disabled) check();
  });
  area.append(field);
  field.inlineShortcuts = functionShortcuts(field.inlineShortcuts); // needs a mounted field
  renderKeys();
}

// The answer can't be edited while it is being checked or might still be held by the server.
function lockAnswer(locked) {
  const canSubmit = Boolean(item?.allowed_actions?.includes('submit'));
  if (field) field.readOnly = locked || !canSubmit;
  if (item?.answer_kind === 'choice') {
    for (const radio of document.querySelectorAll('input[name="choice"]')) radio.disabled = locked;
  }
}

function selectedChoice() {
  const checked = document.querySelector('input[name="choice"]:checked');
  return checked ? checked.value : null;
}

function updateCheck() {
  if (!item) return;
  const ready = item.answer_kind === 'choice' ? selectedChoice() !== null : !incomplete(field.value);
  $('check').disabled = busy || !ready;
  for (const id of ['next', 'skip', 'reveal']) $(id).disabled = busy;
}

// -- help (milestone C1) ----------------------------------------------------------------
const HELP_FAILED = "Help isn't available right now. Please try again in a moment.";
const HELP_SLOW = 'Help is taking longer than expected. Please try again in a moment.';
const HELP_IDS = ['help-hint', 'help-feedback', 'help-explain', 'help-explain-go'];
let helpBusy = false;
let helpGen = 0; // bumped whenever the panel is cleared: older replies are dropped
let helpShownSeq = 0; // the newest help_seq shown for this item

async function helpApi(body) {
  const response = await fetch('/api/help', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify(body),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  return { response, data };
}

function setHelpDisabled(disabled) {
  for (const id of HELP_IDS) $(id).disabled = disabled;
}

function renderHelpButtons() {
  const help = item?.help;
  const enabled = Boolean(help?.enabled);
  const types = enabled ? help.types : [];
  // After a reload the last outcome is unknown; the server lists "feedback" only when the
  // item has a wrong attempt, so trust that until a check says otherwise.
  const wrong = lastOutcome === null || (lastOutcome.status === 'incorrect' && !lastOutcome.code);
  $('help-controls').hidden = !enabled;
  $('help-note').hidden = !enabled;
  $('help-hint').hidden = !types.includes('hint');
  $('help-feedback').hidden = !(types.includes('feedback') && wrong);
  $('help-explain').hidden = !(types.includes('explain') && help.confusions.length > 0);
  if (!enabled) $('help-explain-row').hidden = true;
}

function openExplain() {
  const select = $('help-confusion');
  select.textContent = '';
  for (const confusion of item.help.confusions) {
    const option = document.createElement('option');
    option.value = confusion.id;
    option.textContent = confusion.label;
    select.append(option);
  }
  $('help-explain-row').hidden = false;
}

function clearHelp() {
  helpGen += 1; // an in-flight reply for the old view is now dropped
  helpShownSeq = 0;
  helpBusy = false;
  setHelpDisabled(false);
  $('help-body').innerHTML = '';
  $('help-sources').textContent = '';
  $('help-message').textContent = '';
  $('help-panel').hidden = true;
  $('help-explain-row').hidden = true;
}

function showHelpMessage(text) {
  $('help-body').innerHTML = '';
  $('help-sources').textContent = '';
  $('help-message').textContent = text;
  $('help-panel').hidden = false;
}

function renderHelpSources(sources) {
  const out = $('help-sources');
  out.textContent = '';
  for (const source of sources) {
    if (!source.url.startsWith('https://openstax.org/')) continue; // never link elsewhere
    const row = document.createElement('span');
    row.className = 'help-source';
    const link = document.createElement('a');
    link.href = source.url;
    link.rel = 'noopener';
    link.target = '_blank';
    const named = source.label.includes('Calculus Volume 1');
    link.textContent = `${named ? '' : 'OpenStax Calculus Vol. 1, '}${source.label} ↗`;
    row.append(link, ` · ${source.license}`);
    out.append(row);
  }
}

function showHelp(data) {
  if (data.help_seq > 0) helpShownSeq = data.help_seq;
  $('help-message').textContent = '';
  $('help-body').innerHTML = data.html || ''; // the server renders and sanitizes it
  renderHelpSources(data.status === 'delivered' || data.status === 'fallback' ? data.sources : []);
  $('help-panel').hidden = false;
}

function helpIsCurrent(data) {
  return Boolean(item)
    && data.session_item_id === item.session_item_id
    && data.item_revision === item.revision
    && !(data.help_seq > 0 && data.help_seq < helpShownSeq);
}

async function askHelp(type) {
  if (helpBusy || !item?.help) return;
  const confusion = type === 'explain' ? $('help-confusion').value : null;
  if (type === 'explain' && !confusion) return;
  helpBusy = true;
  setHelpDisabled(true);
  const generation = helpGen;
  const body = {
    help_request_id: crypto.randomUUID(), // reused for the one poll
    session_item_id: item.session_item_id,
    item_revision: item.revision,
    help_type: type,
    confusion,
  };
  try {
    for (let attempt = 0; attempt < 2; attempt += 1) {
      let result;
      try {
        result = await helpApi(body);
      } catch {
        if (generation === helpGen) showHelpMessage(HELP_FAILED);
        return;
      }
      if (generation !== helpGen) return; // the panel was cleared while waiting
      const { response, data } = result;
      if (response.ok && data?.status === 'pending') {
        if (attempt === 0) await sleep(2);
        else showHelpMessage(HELP_SLOW);
        continue;
      }
      if (response.ok && data?.status === 'stale') {
        await load();
      } else if (response.ok) {
        if (helpIsCurrent(data)) showHelp(data);
      } else if (data?.error === 'stale_item' || response.status === 409) {
        await load();
      } else if (data?.error === 'help_limited') {
        showHelpMessage(data.message); // fixed server text
      } else {
        showHelpMessage(HELP_FAILED); // never the raw error body
      }
      return;
    }
  } finally {
    if (generation === helpGen) { // else clearHelp already reset it, maybe for a newer request
      helpBusy = false;
      setHelpDisabled(false);
    }
  }
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
    $('done-message').textContent = DONE_MESSAGES[current.reason] || DONE_MESSAGES.session_complete;
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
    unresolved = false;
    lastOutcome = null;
  }
  if (isNew || revealedLatex || !next.allowed_actions.includes('submit')) clearHelp();
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
  renderHelpButtons();
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
    unresolved = false;
  }
  lockAnswer(true);
  try {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      let result;
      try {
        result = await api('/submit', pending);
      } catch {
        unresolved = true; // the server may have received it
        setFeedback('Connection problem. Retrying…');
        await sleep(2);
        continue; // same submission_id, so a retry is never counted twice
      }
      const { response, data } = result;
      if (response.status === 503 || data?.error === 'submission_pending') {
        // Only verifier_busy means the server kept nothing; anything else may be in progress.
        if (data?.error !== 'verifier_busy') unresolved = true;
        setFeedback('The checker is busy. Retrying…');
        await sleep(Number(response.headers.get('Retry-After')) || 2);
        continue;
      }
      const target = pending.session_item_id;
      pending = null;
      unresolved = false;
      if (response.ok && data.item.session_item_id !== item.session_item_id) {
        await load(); // a reply about a problem that is no longer shown (e.g. a replay)
      } else if (response.ok && item.session_item_id !== target) {
        await load();
      } else if (response.ok) {
        lastOutcome = data.outcome;
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
    if (unresolved) {
      showError('Your answer is still being checked. Press Check to try it again; it won\'t count twice.');
    } else {
      pending = null; // every reply was verifier_busy: an edit is a new answer
      showError('The checker is still busy. Please try again in a moment.');
    }
  } finally {
    busy = false;
    lockAnswer(Boolean(pending && unresolved));
    updateCheck();
  }
}

async function act(action) {
  if (busy) return; // a duplicate click never sends a second action
  busy = true;
  updateCheck();
  showError('');
  try {
    const { response, data } = await api(`/${action}`, {
      session_item_id: item.session_item_id,
      item_revision: item.revision,
    });
    if (response.ok) {
      if (action !== 'reveal') setFeedback('');
      render(data, data.revealed_latex);
    } else if (data?.error === 'stale_item') {
      await load();
    } else {
      showError(data?.message || 'Something went wrong. Please try again.');
    }
  } catch {
    showError('Connection problem. Please try again.');
  } finally {
    busy = false;
    updateCheck();
  }
}

$('check').addEventListener('click', check);
$('next').addEventListener('click', () => act('advance'));
$('skip').addEventListener('click', () => act('skip'));
$('reveal').addEventListener('click', () => act('reveal'));
$('help-hint').addEventListener('click', () => askHelp('hint'));
$('help-feedback').addEventListener('click', () => askHelp('feedback'));
$('help-explain').addEventListener('click', openExplain);
$('help-explain-go').addEventListener('click', () => askHelp('explain'));
load();
