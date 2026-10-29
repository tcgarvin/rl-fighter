// Headless smoke test of the web duel: loads the wasm bundle and an exported policy,
// plays full matches with web/duel/duel.js (the page's own loop) and prints each
// winner and the per-tick sim / inference cost. Exits non-zero if a match fails to
// finish or a tick blows the 30 Hz budget on average.
//
// Usage: node tools/web/duel_smoke.mjs <pkg-dir> <policy-dir> [matches=3] [mode=learned-vs-script] [seed=1]

import fs from "node:fs";
import path from "node:path";
import { importRepo, loadCatalogue, loadSim, readPolicyFiles } from "./load.mjs";

const [pkgDir, policyDir, nArg = "3", mode = "learned-vs-script", seedArg = "1"] = process.argv.slice(2);
if (!pkgDir || !policyDir) {
  console.error("usage: node tools/web/duel_smoke.mjs <pkg-dir> <policy-dir> [matches] [mode] [seed]");
  process.exit(2);
}
const { createPolicy } = await importRepo("web/duel/policy.js");
const { Duel, MODES, TICK_BUDGET_MS, simLayout } = await importRepo("web/duel/duel.js");
if (!MODES[mode]) throw new Error(`unknown mode ${mode}; expected ${Object.keys(MODES).join(", ")}`);

const sim = await loadSim(pkgDir);
const layout = simLayout(sim);
const { manifest, weights } = readPolicyFiles(policyDir);
const policy = createPolicy(manifest, weights, layout);
const duel = new Duel({ sim, catalogue: loadCatalogue(), policy, matchConfig: manifest.match_config });

const wasmBytes = fs.statSync(path.join(pkgDir, "sim_wasm_bg.wasm")).size;
const weightBytes = fs.statSync(path.join(policyDir, manifest.weights_file)).size;
console.log(`duel smoke: sim_version ${layout.simVersion}, wasm ${(wasmBytes / 1024).toFixed(0)} KiB, weights ${(weightBytes / 1024).toFixed(0)} KiB, policy update ${manifest.source.update} (${path.basename(manifest.source.checkpoint)})`);

const names = MODES[mode].controllers;
const tally = { 0: 0, 1: 0, draw: 0 };
let worstMean = 0;
let failed = false;
for (let i = 0; i < Number(nArg); i++) {
  const seed = Number(seedArg) + i;
  duel.start(mode, seed);
  let nnTotal = 0;
  let nnTicks = 0;
  let simTotal = 0; // sim step only
  const limit = manifest.match_config.time_limit_ticks + 100;
  while (!duel.over && duel.tick < limit) {
    duel.step();
    simTotal += duel.last.sim;
    if (duel.last.nn > 0) {
      nnTotal += duel.last.nn;
      nnTicks += 1;
    }
  }
  if (!duel.over) {
    console.error(`duel smoke: FAIL match ${i} (seed ${seed}) did not finish by tick ${duel.tick}`);
    failed = true;
    continue;
  }
  const w = duel.winner;
  const who = w === -1 ? "draw" : `team ${w} (${names[w]})`;
  tally[w === -1 ? "draw" : w] += 1;
  const meanSim = simTotal / duel.tick;
  const meanNn = nnTotal / Math.max(1, nnTicks);
  const meanTick = meanSim + meanNn;
  worstMean = Math.max(worstMean, meanTick);
  const hp = duel.ships.map((s) => Math.max(0, s.hp).toFixed(0)).join("/");
  console.log(
    `duel smoke: match ${i} seed ${seed} ${mode}: winner ${who} at tick ${duel.tick} (${(duel.tick / 30).toFixed(1)} s), hp ${hp}; ` +
      `tick ${meanTick.toFixed(3)} ms = sim ${meanSim.toFixed(3)} + inference ${meanNn.toFixed(3)} (${names.filter((n) => n === "learned").length} net) of ${TICK_BUDGET_MS.toFixed(1)} ms`,
  );
}
console.log(`duel smoke: ${names[0]} (team 0) ${tally[0]} · ${names[1]} (team 1) ${tally[1]} · draws ${tally.draw}`);
if (worstMean > TICK_BUDGET_MS) {
  console.error(`duel smoke: FAIL mean tick ${worstMean.toFixed(2)} ms exceeds the ${TICK_BUDGET_MS.toFixed(1)} ms budget`);
  failed = true;
}
process.exit(failed ? 1 : 0);
