// Copies the prototype into an output directory with bare "three" imports rewritten to
// absolute jsDelivr +esm URLs. The Artifact host doesn't honour import maps, and +esm
// builds make three.js and its addons resolve to one shared module instance.
//
// Usage: node build_artifact.mjs <outDir>

import { cpSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const THREE_VERSION = "0.170.0";
const THREE_URL = `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/+esm`;
const addonUrl = (path) => `https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/examples/jsm/${path}/+esm`;

const srcDir = dirname(fileURLToPath(import.meta.url));
const outDir = process.argv[2];
if (!outDir) {
  throw new Error("Usage: node build_artifact.mjs <outDir>");
}

function rewriteImports(code) {
  return code
    .replace(/(from\s*|import\s*\(\s*)(["'])three\2/g, `$1"${THREE_URL}"`)
    .replace(/(from\s*|import\s*\(\s*)(["'])three\/addons\/([^"']+)\2/g, (_, lead, _q, path) => `${lead}"${addonUrl(path)}"`);
}

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

mkdirSync(outDir, { recursive: true });
const published = [];
for (const file of walk(srcDir)) {
  const rel = relative(srcDir, file);
  // round1/ is a frozen local snapshot; it isn't part of the published demo.
  if (!rel.endsWith(".js") || rel.startsWith("build_") || rel.startsWith("round1/")) continue;
  const target = join(outDir, rel);
  mkdirSync(dirname(target), { recursive: true });
  const code = rewriteImports(readFileSync(file, "utf8"));
  if (/from\s*["']three/.test(code)) {
    throw new Error(`Unrewritten bare three import left in ${rel}`);
  }
  writeFileSync(target, code);
  published.push(rel);
}
const page = readFileSync(join(srcDir, "artifact.html"), "utf8").replace(/<script type="importmap">[\s\S]*?<\/script>/, "");
writeFileSync(join(outDir, "artifact.html"), page);
cpSync(join(srcDir, "PROPOSALS.md"), join(outDir, "PROPOSALS.md"));
console.log(JSON.stringify(published));
