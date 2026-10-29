// Node loaders shared by the web duel's headless tools: the wasm-pack (--target web)
// bundle, the hull/weapon catalogue from assets/, and an exported policy directory.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

export async function importRepo(rel) {
  return import(pathToFileURL(path.join(REPO, rel)).href);
}

/** Instantiate the sim bundle in `pkgDir` synchronously (same bytes the browser loads). */
export async function loadSim(pkgDir) {
  const dir = path.resolve(pkgDir);
  const sim = await import(pathToFileURL(path.join(dir, "sim_wasm.js")).href);
  sim.initSync({ module: fs.readFileSync(path.join(dir, "sim_wasm_bg.wasm")) });
  return sim;
}

/** Every hull under assets/hulls plus weapons.yaml, in the WasmMatch constructor's shape. */
export function loadCatalogue() {
  const hullsDir = path.join(REPO, "assets/hulls");
  const names = fs.readdirSync(hullsDir).filter((n) => fs.existsSync(path.join(hullsDir, n, "hull.yaml"))).sort();
  return {
    hulls: names.map((n) => [n, fs.readFileSync(path.join(hullsDir, n, "hull.yaml"), "utf8")]),
    weapons: fs.readFileSync(path.join(REPO, "assets/weapons.yaml"), "utf8"),
  };
}

/** Read manifest.json and weights.bin from an export directory. */
export function readPolicyFiles(policyDir) {
  const manifest = JSON.parse(fs.readFileSync(path.join(policyDir, "manifest.json"), "utf8"));
  const bytes = fs.readFileSync(path.join(policyDir, manifest.weights_file));
  // Copy into a fresh, aligned ArrayBuffer (Buffer slices may share a pool).
  const weights = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  return { manifest, weights };
}
