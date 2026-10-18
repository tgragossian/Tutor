// Shared by the capture tools: a static server rooted at tools/ and the Chromium page driver.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const toolsRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.css': 'text/css',
  '.woff2': 'font/woff2',
};

export function startServer() {
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

export async function readVersion(name) {
  const pkg = JSON.parse(await readFile(join(toolsRoot, 'node_modules', name, 'package.json'), 'utf8'));
  return pkg.version;
}

export function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortKeys(value[k])]));
  }
  return value;
}

// One input on a fresh page (MathLive keeps cursor/mode state across setValue calls):
// `keys` are pressed one by one, otherwise `latex` is set. Returns window.capture.read().
export async function captureOne(page, server, input) {
  await page.goto(`http://127.0.0.1:${server.address().port}/capture/page.html`);
  await page.waitForFunction(() => window.capture?.ready === true);
  if (input.keys) {
    await page.focus('math-field');
    for (const k of input.keys) await page.keyboard.press(k);
  } else {
    await page.evaluate((l) => window.capture.setValue(l), input.latex);
  }
  return page.evaluate(() => window.capture.read());
}
