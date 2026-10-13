import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { ComputeEngine } from "@cortex-js/compute-engine";
import { parse as parseYaml } from "yaml";

const TOOLS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function pkgVersion(name) {
  const p = join(TOOLS_DIR, "node_modules", ...name.split("/"), "package.json");
  return JSON.parse(readFileSync(p, "utf8")).version;
}

function loadYaml(file, label) {
  const text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
  let doc;
  try {
    doc = parseYaml(text, { schema: "core", uniqueKeys: true });
  } catch (e) {
    const dup = /unique/i.test(e.message) ? "duplicate key: " : "";
    throw new Error(`${label}: ${dup}${e.message}`);
  }
  checkControlChars(doc, label, "");
  return doc;
}

function checkControlChars(node, label, path) {
  if (typeof node === "string") {
    if (/[\u0000-\u0009\u000b-\u001f]/.test(node)) {
      throw new Error(
        `${label}: ${path || "(root)"}: control character in string; use single quotes for LaTeX`,
      );
    }
  } else if (Array.isArray(node)) {
    node.forEach((v, i) => checkControlChars(v, label, `${path}[${i}]`));
  } else if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) {
      checkControlChars(v, label, path ? `${path}.${k}` : k);
    }
  }
}

function hasBadNode(node) {
  if (node === "Nothing") return true;
  if (Array.isArray(node)) return node[0] === "Error" || node.some(hasBadNode);
  if (node && typeof node === "object") return Object.values(node).some(hasBadNode);
  return false;
}

// Placeholders vanish from MathJSON (ADR 0002), so they are rejected on the LaTeX string.
function toMathJson(latex, label, field) {
  if (typeof latex !== "string") throw new Error(`${label}: ${field}: latex must be a string`);
  if (latex.includes("\\placeholder") || /\{\s*\}/.test(latex)) {
    throw new Error(`${label}: ${field}: placeholder or empty group in latex ${latex}`);
  }
  // Parsing is stateful: always a fresh engine (ADR 0002).
  const json = new ComputeEngine().parse(latex, { form: "raw" }).json;
  if (hasBadNode(json)) {
    throw new Error(`${label}: ${field}: latex does not parse cleanly: ${latex}`);
  }
  return json;
}

function attachMathJson(problem, label) {
  const a = problem?.answer;
  if (!a || typeof a !== "object") return;
  if (a.kind === "choice") {
    if (!Array.isArray(a.choices)) return;
    a.choices.forEach((c, i) => {
      c.mathjson = toMathJson(c.latex, label, `answer.choices[${i}].latex`);
    });
  } else if ("latex" in a) {
    a.mathjson = toMathJson(a.latex, label, "answer.latex");
  }
}

export function compile(contentDir) {
  const topics = loadYaml(join(contentDir, "topics.yaml"), "topics.yaml");
  const problems = [];
  const pdir = join(contentDir, "problems");
  if (existsSync(pdir)) {
    const files = readdirSync(pdir)
      .filter((f) => f.endsWith(".yaml"))
      .sort();
    for (const f of files) {
      const label = `problems/${f}`;
      const problem = loadYaml(join(pdir, f), label);
      attachMathJson(problem, label);
      problems.push(problem);
    }
  }
  return {
    schema_version: 1,
    tools: {
      mathlive: pkgVersion("mathlive"),
      compute_engine: pkgVersion("@cortex-js/compute-engine"),
    },
    topics,
    problems,
  };
}

function sortKeys(v) {
  if (Array.isArray(v)) return v.map(sortKeys);
  if (v && typeof v === "object") {
    return Object.fromEntries(
      Object.keys(v)
        .sort()
        .map((k) => [k, sortKeys(v[k])]),
    );
  }
  return v;
}

export function serialize(bundle) {
  return JSON.stringify(sortKeys(bundle), null, 2) + "\n";
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [contentDir, out] = process.argv.slice(2);
  const text = serialize(compile(contentDir));
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, text, "utf8");
}
