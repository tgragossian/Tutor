// Copy the pinned MathLive and Compute Engine browser files into the app's static folder
// and write manifest.json with a sha384 SRI hash for every JavaScript module.
// Run: npm run vendor --prefix tools
import { createHash } from 'node:crypto';
import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const tools = dirname(fileURLToPath(import.meta.url));
const modules = join(tools, 'node_modules');
const out = resolve(tools, '..', 'src', 'mathtutor', 'web', 'static', 'vendor');

async function version(name) {
  const pkg = JSON.parse(await readFile(join(modules, name, 'package.json'), 'utf8'));
  return pkg.version;
}

async function files(dir) {
  const entries = await readdir(dir, { withFileTypes: true, recursive: true });
  return entries
    .filter((e) => e.isFile())
    .map((e) => join(e.parentPath ?? e.path, e.name))
    .sort();
}

function sri(bytes) {
  return `sha384-${createHash('sha384').update(bytes).digest('base64')}`;
}

const mathlive = join(modules, 'mathlive');
const ce = join(modules, '@cortex-js', 'compute-engine', 'dist', 'esm-min');

await rm(out, { recursive: true, force: true });
await mkdir(join(out, 'mathlive'), { recursive: true });
await mkdir(join(out, 'compute-engine'), { recursive: true });

await cp(join(mathlive, 'mathlive.min.mjs'), join(out, 'mathlive', 'mathlive.min.mjs'));
await cp(join(mathlive, 'LICENSE.txt'), join(out, 'mathlive', 'LICENSE.txt'));
await cp(join(mathlive, 'fonts'), join(out, 'mathlive', 'fonts'), { recursive: true });
await cp(join(mathlive, 'sounds'), join(out, 'mathlive', 'sounds'), { recursive: true });

// compute-engine.js imports only its two chunks; the other entry points are not needed.
await cp(join(ce, 'compute-engine.js'), join(out, 'compute-engine', 'compute-engine.js'));
await cp(join(ce, 'chunks'), join(out, 'compute-engine', 'chunks'), { recursive: true });
await cp(
  join(modules, '@cortex-js', 'compute-engine', 'LICENSE'),
  join(out, 'compute-engine', 'LICENSE'),
).catch(() => {});

const integrity = {};
for (const file of await files(out)) {
  if (file.endsWith('.js') || file.endsWith('.mjs')) {
    integrity[relative(out, file).split(sep).join('/')] = sri(await readFile(file));
  }
}

const manifest = {
  generated_by: 'tools/vendor.mjs',
  versions: {
    mathlive: await version('mathlive'),
    compute_engine: await version('@cortex-js/compute-engine'),
  },
  entries: ['mathlive/mathlive.min.mjs', 'compute-engine/compute-engine.js'],
  integrity,
};
await writeFile(join(out, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`vendored ${Object.keys(integrity).length} modules into ${out}`);
