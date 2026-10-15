import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { ComputeEngine } from "@cortex-js/compute-engine";
import markdownit from "markdown-it";
import { isPair, isScalar, isSeq, parseDocument, visit } from "yaml";

const TOOLS_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function pkgVersion(name) {
  const p = join(TOOLS_DIR, "node_modules", ...name.split("/"), "package.json");
  return JSON.parse(readFileSync(p, "utf8")).version;
}

function loadYaml(file, label) {
  const text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
  const parsed = parseDocument(text, { schema: "core", uniqueKeys: true });
  if (parsed.errors.length) {
    const e = parsed.errors[0];
    const dup = /unique/i.test(e.message) ? "duplicate key: " : "";
    throw new Error(`${label}: ${dup}${e.message}`);
  }
  checkDoubleQuotedEscapes(parsed, text, label);
  const doc = parsed.toJS();
  checkControlChars(doc, label, "");
  return doc;
}

function yamlPath(path, key) {
  const parts = [];
  path.forEach((node, i) => {
    if (isPair(node) && isScalar(node.key)) parts.push(String(node.key.value));
    if (isSeq(node)) {
      const next = path[i + 1];
      const idx = next === undefined ? key : node.items.indexOf(next);
      parts[parts.length - 1] += `[${idx}]`;
    }
  });
  return parts.join(".") || "(root)";
}

// Every backslash escape in a double-quoted scalar is a trap for LaTeX: some become control
// characters, but \n, \N, \L, \P and \_ yield newline/U+0085/U+2028/U+2029/U+00A0, so \nu or
// \Pi would silently compile to "u" or "i" (review focus 2).
function checkDoubleQuotedEscapes(parsed, text, label) {
  visit(parsed, {
    Scalar(key, node, path) {
      if (node.type !== "QUOTE_DOUBLE" || !node.range) return;
      if (text.slice(node.range[0], node.range[1]).includes("\\")) {
        throw new Error(
          `${label}: ${yamlPath(path, key)}: backslash escape in a double-quoted string; ` +
            "use single quotes for LaTeX",
        );
      }
    },
  });
}

function checkControlChars(node, label, path) {
  if (typeof node === "string") {
    if (/[\u0000-\u0009\u000b-\u001f\u0085\u00a0\u2028\u2029]/.test(node)) {
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

const OPENSTAX = "https://openstax.org/";

// Raw HTML is escaped (html: false) and links off openstax.org are unwrapped (R3).
const md = markdownit({ html: false, linkify: false }).disable("image");
md.core.ruler.push("openstax_links_only", (state) => {
  for (const block of state.tokens) {
    if (block.type !== "inline" || !block.children) continue;
    const kept = [];
    let dropping = false;
    for (const t of block.children) {
      if (t.type === "link_open") {
        dropping = !(t.attrGet("href") ?? "").startsWith(OPENSTAX);
        if (dropping) continue;
      } else if (t.type === "link_close" && dropping) {
        dropping = false;
        continue;
      }
      kept.push(t);
    }
    block.children = kept;
  }
});

export function statementHtml(statement) {
  return String(statement)
    .split(/(?<!\\)\$((?:\\.|[^$\\])*)\$/)
    .map((part, i) =>
      i % 2 === 1
        ? `<math-field read-only>${md.utils.escapeHtml(part)}</math-field>`
        : md.renderInline(part),
    )
    .join("");
}

// A misconception is "<latex>  # <why>"; for choice problems the part before it is a choice id.
function misconceptionsMathJson(problem, label) {
  if (!Array.isArray(problem.misconceptions) || problem.misconceptions.length === 0) return;
  const isChoice = problem.answer?.kind === "choice";
  problem.misconceptions_mathjson = problem.misconceptions.map((m, i) => {
    if (isChoice || typeof m !== "string") return null;
    const latex = m.split("  #")[0].trim();
    try {
      return toMathJson(latex, label, `misconceptions[${i}]`);
    } catch {
      return null;
    }
  });
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
      misconceptionsMathJson(problem, label);
      problem.statement_html = statementHtml(problem.statement);
      problems.push(problem);
    }
  }
  return {
    schema_version: 2,
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
