// Build the human verifier dev set from real MathLive captures (spec 08, task 9).
// Usage: npm run capture:eval --prefix tools
//   reads  evals/verifier/human/dev.src.yaml
//   writes evals/verifier/human/dev.jsonl (one case per line, sorted by id, LF)
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadYaml, toMathJson } from '../compile_content/compile.mjs';
import { captureOne, readVersion, sortKeys, startServer, toolsRoot } from './serve.mjs';

const HUMAN_DIR = resolve(toolsRoot, '..', 'evals', 'verifier', 'human');
const LABELS = new Set(['correct', 'incorrect', 'unsupported']);
const REQUIRED = ['id', 'family', 'category', 'label', 'rationale', 'reviewer'];
const OPTIONAL = ['problem_id', 'inline_spec', 'latex', 'keys', 'choice_id'];
const INPUTS = ['latex', 'keys', 'choice_id'];
const CRASH_RETRIES = 5;
const CRASHED = /Target crashed|frame was detached|Target page, context or browser has been closed/;
// Stands in for the captured MathJSON so the page's exact JSON text is spliced in verbatim.
const SENTINEL = '\u0000mathjson\u0000';

/** Validate authored entries; throws naming the entry and field. */
export function validateEntries(entries) {
  if (!Array.isArray(entries)) throw new Error('dev.src.yaml must be a list of cases');
  const seen = new Set();
  for (const [i, e] of entries.entries()) {
    const where = `case ${i + 1} (${e?.id ?? '?'})`;
    if (!e || typeof e !== 'object') throw new Error(`${where}: must be a mapping`);
    const unknown = Object.keys(e).filter((k) => !REQUIRED.includes(k) && !OPTIONAL.includes(k));
    if (unknown.length) throw new Error(`${where}: unknown field(s) ${unknown.join(', ')}`);
    for (const k of REQUIRED) {
      if (typeof e[k] !== 'string' || !e[k].trim()) {
        throw new Error(`${where}: ${k} must be a non-empty string`);
      }
    }
    if (!LABELS.has(e.label)) throw new Error(`${where}: label must be one of ${[...LABELS]}`);
    if (('problem_id' in e) === ('inline_spec' in e)) {
      throw new Error(`${where}: exactly one of problem_id or inline_spec is required`);
    }
    const inputs = INPUTS.filter((k) => k in e);
    if (inputs.length !== 1) throw new Error(`${where}: exactly one of ${INPUTS.join(', ')}`);
    if ('keys' in e && !(Array.isArray(e.keys) && e.keys.every((k) => typeof k === 'string'))) {
      throw new Error(`${where}: keys must be a list of strings`);
    }
    if ('latex' in e && typeof e.latex !== 'string') {
      throw new Error(`${where}: latex must be a string`);
    }
    if (seen.has(e.id)) throw new Error(`${where}: duplicate id`);
    seen.add(e.id);
  }
  return entries;
}

/** The inline spec with its mathjson compiled exactly as content answers are. */
export function compileInlineSpec(entry) {
  const spec = entry.inline_spec;
  if (!spec || typeof spec !== 'object') throw new Error(`${entry.id}: inline_spec must be a mapping`);
  return { ...spec, mathjson: toMathJson(spec.latex, entry.id, 'inline_spec.latex') };
}

/**
 * One JSONL line. `captured` is window.capture.read() for typed inputs (null for choices);
 * its `mathjson` is the page's JSON text and goes into the line unchanged, so no number
 * passes through a JS float on the way out.
 */
export function formatRow(entry, captured) {
  // `category` is copied so CI can check spec 08 coverage from dev.jsonl (review B-E2).
  const row = { ...entry };
  delete row.latex;
  delete row.keys;
  delete row.choice_id;
  if ('inline_spec' in entry) row.inline_spec = compileInlineSpec(entry);
  if ('choice_id' in entry) {
    row.answer = { choice_id: entry.choice_id };
  } else {
    row.answer = { latex: captured.latex, mathjson: SENTINEL };
    if ('keys' in entry) row.raw_keys = entry.keys;
    else row.raw_latex = entry.latex;
  }
  const text = JSON.stringify(sortKeys(row));
  if (!('choice_id' in entry)) {
    JSON.parse(captured.mathjson); // must be valid JSON before it is spliced in
    return text.replace(JSON.stringify(SENTINEL), () => captured.mathjson);
  }
  return text;
}

export function serializeRows(lines) {
  return lines.length ? `${lines.join('\n')}\n` : '';
}

async function main() {
  const src = resolve(HUMAN_DIR, 'dev.src.yaml');
  const out = resolve(HUMAN_DIR, 'dev.jsonl');
  const entries = validateEntries(loadYaml(src, 'dev.src.yaml'));
  const sorted = [...entries].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const { chromium } = await import('playwright');
  const server = await startServer();
  const browser = await chromium.launch();
  const lines = [];
  // One page per case, closed afterwards. Chromium's renderer occasionally crashes on deeply
  // nested input (seen with 10-31 nested roots), sometimes only after the read returns; a
  // crashed attempt is retried on a new page with the same input.
  const captureFresh = async (entry, input) => {
    for (let attempt = 1; ; attempt++) {
      const page = await browser.newPage();
      page.on('pageerror', (e) => process.stderr.write(`[pageerror] ${e}\n`));
      try {
        return await captureOne(page, server, input);
      } catch (error) {
        if (!CRASHED.test(error.message) || attempt === CRASH_RETRIES) {
          throw new Error(`${entry.id}: ${error.message}`, { cause: error });
        }
        process.stderr.write(`${entry.id}: renderer crashed, retrying (${attempt})\n`);
      } finally {
        await page.close().catch(() => {});
      }
    }
  };
  try {
    for (const entry of sorted) {
      let captured = null;
      if ('keys' in entry) captured = await captureFresh(entry, { keys: entry.keys });
      else if ('latex' in entry) captured = await captureFresh(entry, { latex: entry.latex });
      lines.push(formatRow(entry, captured));
    }
    const versions = `mathlive ${await readVersion('mathlive')}, compute-engine ${await readVersion(
      '@cortex-js/compute-engine',
    )}, chromium ${browser.version()}`;
    writeFileSync(out, serializeRows(lines), 'utf8');
    console.log(`wrote ${out} (${lines.length} cases; ${versions})`);
  } finally {
    await browser.close();
    server.close();
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
