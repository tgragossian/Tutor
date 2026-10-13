// Capture real MathLive + Compute Engine output for every case in cases.json.
// Usage: npm run capture --prefix tools   (writes tests/fixtures/mathjson/captured.json)
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = dirname(fileURLToPath(import.meta.url));
const toolsRoot = resolve(here, '..');
const outFile = resolve(toolsRoot, '..', 'tests', 'fixtures', 'mathjson', 'captured.json');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.css': 'text/css',
  '.woff2': 'font/woff2',
};

function startServer() {
  const server = createServer(async (req, res) => {
    try {
      const path = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname));
      const file = join(toolsRoot, path.endsWith('/') ? `${path}index.html` : path);
      if (!file.startsWith(toolsRoot + sep)) throw new Error('outside root');
      const body = await readFile(file);
      res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end();
    }
  });
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)));
}

async function readVersion(name) {
  const pkg = JSON.parse(await readFile(join(toolsRoot, 'node_modules', name, 'package.json'), 'utf8'));
  return pkg.version;
}

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortKeys(value[k])]));
  }
  return value;
}

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
    // A fresh page per case: MathLive keeps cursor/mode state across setValue calls.
    await page.goto(`http://127.0.0.1:${server.address().port}/capture/page.html`);
    await page.waitForFunction(() => window.capture?.ready === true);
    let input;
    if (c.keys) {
      input = { keys: c.keys };
      await page.focus('math-field');
      for (const k of c.keys) await page.keyboard.press(k);
    } else {
      input = { latex: c.latex };
      await page.evaluate((l) => window.capture.setValue(l), c.latex);
    }
    const r = await page.evaluate(() => window.capture.read());
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
