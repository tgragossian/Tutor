// Capture real MathLive + Compute Engine output for every case in cases.json.
// Usage: npm run capture --prefix tools   (writes tests/fixtures/mathjson/captured.json)
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { captureOne, readVersion, sortKeys, startServer, toolsRoot } from './serve.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const outFile = resolve(toolsRoot, '..', 'tests', 'fixtures', 'mathjson', 'captured.json');

const cases = JSON.parse(await readFile(join(here, 'cases.json'), 'utf8'));
const server = await startServer();
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  page.on('console', (m) => process.stderr.write(`[page ${m.type()}] ${m.text()}\n`));
  page.on('pageerror', (e) => process.stderr.write(`[pageerror] ${e}\n`));

  const result = {};
  let aliasMatchesRaw = true;
  for (const c of cases) {
    const input = c.keys ? { keys: c.keys } : { latex: c.latex };
    const r = await captureOne(page, server, input);
    aliasMatchesRaw = aliasMatchesRaw && r.alias_matches_raw;

    result[c.key] = {
      input,
      latex_out: r.latex,
      mathjson: r.mathjson,
      mathjson_canonical: r.mathjson_canonical,
    };
  }

  const out = {
    meta: {
      mathlive: await readVersion('mathlive'),
      compute_engine: await readVersion('@cortex-js/compute-engine'),
      chromium: browser.version(),
      canonical_false_equals_form_raw: String(aliasMatchesRaw),
    },
    cases: result,
  };
  await writeFile(outFile, `${JSON.stringify(sortKeys(out), null, 2)}\n`, 'utf8');
  console.log(`wrote ${outFile} (${Object.keys(result).length} cases)`);
} finally {
  await browser.close();
  server.close();
}
