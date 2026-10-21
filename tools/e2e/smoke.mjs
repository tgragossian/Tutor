// Browser smoke test (milestone B task 15): register, practise the chain rule, check
// wrong/right answers, reload, advance and history, failing on any CSP violation.
// Run: BASE_URL=http://127.0.0.1:8000 npm run e2e --prefix tools
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const TIMEOUT = 30_000;

// Keyed by "section/exercise" (public items carry no problem id). Each answer is a list of
// keystrokes: plain strings are typed, names like ArrowRight are pressed. In MathLive "^"
// opens an exponent, and ArrowRight leaves it.
const ANSWERS = {
  '3.6/221': {
    wrong: ['3(3x', '^', '2', 'ArrowRight', '+1)', '^', '2', 'ArrowRight'],
    right: ['18x(3x', '^', '2', 'ArrowRight', '+1)', '^', '2', 'ArrowRight'],
  },
  '3.6/253': { wrong: ['-0.584'], right: ['-0.583'] },
};
const KEY_NAMES = new Set(['ArrowRight', 'ArrowLeft', 'Backspace', 'Tab']);

const problems = [];
function check(condition, message) {
  if (!condition) problems.push(message);
  console.log(`${condition ? 'ok  ' : 'FAIL'} ${message}`);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
page.setDefaultTimeout(TIMEOUT);
const consoleLines = [];
page.on('console', (m) => consoleLines.push(`${m.type()}: ${m.text()}`));
page.on('pageerror', (e) => consoleLines.push(`pageerror: ${e.message}`));

async function itemKey() {
  const text = await page.textContent('#source');
  const match = /§([\d.]+), exercise (\d+)/.exec(text || '');
  return match ? `${match[1]}/${match[2]}` : null;
}

async function waitForItem() {
  await page.waitForSelector('#problem:not([hidden])');
  await page.waitForSelector('#answer math-field, #answer input[type=radio]');
}

async function enter(keys) {
  // A real click: Playwright's zero-length click does not focus a MathLive field.
  await page.click('#answer-field', { delay: 80 });
  await page.evaluate(() => {
    document.getElementById('answer-field').value = '';
  });
  for (const k of keys) {
    if (KEY_NAMES.has(k)) await page.keyboard.press(k);
    else await page.keyboard.type(k);
  }
}

async function submitAndRead() {
  const before = await page.textContent('#feedback');
  await page.click('#check');
  await page.waitForFunction(
    (prev) => {
      const text = document.getElementById('feedback').textContent.trim();
      return text && text !== prev && !text.includes('Retrying');
    },
    before.trim(),
  );
  return (await page.textContent('#feedback')).trim();
}

const triesLeft = async () => (await page.textContent('#tries')).trim();

try {
  // 2. Register and start a chain-rule session.
  const user = `smoke_${Date.now().toString(36)}`;
  await page.goto(`${BASE}/register`);
  await page.fill('input[name=username]', user);
  await page.fill('input[name=password]', 'smoke-password-1');
  await page.click('button[type=submit]');
  await page.waitForURL(`${BASE}/`);
  for (const box of await page.$$('input[name=topics]')) await box.uncheck();
  await page.check('input[value="derivatives.chain_rule"]');
  await page.click('form[action="/sessions"] button[type=submit]');
  await page.waitForURL(/\/practice\/\d+$/);
  await waitForItem();

  // Skip until the current item has known answers.
  let key = await itemKey();
  for (let i = 0; i < 30 && !ANSWERS[key]; i += 1) {
    const statement = await page.innerHTML('#statement');
    await page.click('#skip');
    await page.waitForFunction((s) => document.getElementById('statement').innerHTML !== s, statement);
    key = await itemKey();
  }
  check(Boolean(ANSWERS[key]), `found an item with known answers (${key})`);
  const answers = ANSWERS[key];

  // 3. A known-wrong answer.
  await enter(answers.wrong);
  const typed = await page.evaluate(() => document.getElementById('answer-field').value);
  check(typed.length > 0, `the math-field accepted typed keys (${typed})`); // 7
  const wrong = await submitAndRead();
  check(wrong === 'Not quite — try again (2 left)', `wrong answer feedback: "${wrong}"`);
  check((await triesLeft()) === 'Tries left: 2', 'tries left shows 2');

  // 5. Reload: same item, same tries (no reset).
  const statement = await page.innerHTML('#statement');
  await page.reload();
  await waitForItem();
  check((await page.innerHTML('#statement')) === statement, 'reload keeps the same item');
  check((await triesLeft()) === 'Tries left: 2', 'reload keeps the tries count');

  // 4. The right answer, then Next.
  await enter(answers.right);
  const right = await submitAndRead();
  check(right === 'Correct', `right answer feedback: "${right}"`);
  await page.click('#next');
  await page.waitForFunction((s) => {
    const done = !document.getElementById('done').hidden;
    return done || document.getElementById('statement').innerHTML !== s;
  }, statement);
  const after = await page.innerHTML('#statement');
  check(after !== statement, 'Next shows a different problem');
  if (!(await page.isHidden('#problem'))) {
    await page.reload();
    await waitForItem();
    check((await page.innerHTML('#statement')) === after, 'reload after Next keeps the new item');
  }

  // Review B-A1/B-A5: one mutation at a time. While a (deliberately slow) Check is in flight,
  // Skip is disabled; a double-click on Skip sends exactly one request.
  if (!(await page.isHidden('#problem')) && (await page.isVisible('#answer-field'))) {
    await page.route('**/submit', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      await route.continue();
    });
    await enter(['1']);
    await page.click('#check');
    await page.waitForFunction(() => document.getElementById('check').disabled);
    check(await page.isDisabled('#skip'), 'Skip is disabled while a check is in flight');
    await page.waitForFunction(() => !document.getElementById('skip').disabled, null, {
      timeout: TIMEOUT,
    });
    await page.unroute('**/submit');
    const skips = [];
    page.on('request', (r) => {
      if (r.method() === 'POST' && r.url().endsWith('/skip')) skips.push(r.url());
    });
    // The same problem can come back as a new presentation, so wait for the reply itself.
    const skipped = page.waitForResponse((r) => r.url().endsWith('/skip'));
    await page.dblclick('#skip');
    check((await skipped).status() === 200, 'Skip succeeded');
    await page.waitForTimeout(500);
    check(skips.length === 1, `a double-click on Skip sends one request (${skips.length})`);
    check((await page.textContent('#error')).trim() === '', 'no error after the double-click');
  }

  // 6. History on the start page.
  const sessionPath = new URL(page.url()).pathname;
  await page.goto(`${BASE}/`);
  const row = page.locator('tbody tr', { has: page.locator(`a[href="${sessionPath}"]`) });
  const cells = await row.locator('td').allTextContents();
  check(cells.length === 4 && cells[3].trim() === '1', `history shows 1 correct (${cells.join(' | ')})`);
} catch (error) {
  problems.push(`unexpected error: ${error.message}`);
  console.error(error);
} finally {
  // 1. No CSP violations or refused loads anywhere in the run.
  const bad = consoleLines.filter((l) => /Content Security Policy|Refused to/.test(l));
  check(bad.length === 0, `no CSP violations (${bad.length})`);
  for (const line of bad.slice(0, 5)) console.log(`     ${line}`);
  await browser.close();
}

if (problems.length) {
  console.error(`\n${problems.length} check(s) failed`);
  process.exit(1);
}
console.log('\nbrowser smoke passed');
