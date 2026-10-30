// Headless smoke test of the live page's match loop: loads a champion bundle
// (scripts/build_bundle.sh), drafts rosters with web/src/live/roster.ts and plays full
// matches with web/src/live/match.ts (the page's own code), every ship flown by the JS
// policy. Prints each roster, winner and the per-tick sim / inference cost; exits
// non-zero if a match does not finish, a ship's state goes non-finite, or a mean tick
// blows the 30 Hz budget. The TS sources need Node's type stripping:
//
//   node --experimental-strip-types tools/web/live_smoke.mjs <bundle-dir> [matches=4]
//        [--seed 1] [--modes draft,2v2,3v3,4v4] [--hulls fighter,strafer,gunship]
//
// --modes cycles roster modes (as ?fleets= on the page; "draft" uses the manifest's
// roster rules). --hulls overrides which hulls are drafted, to exercise mixed fleets
// before a champion is certified for them.

import fs from "node:fs";
import path from "node:path";
import { importRepo, loadSim, readPolicyFiles } from "./load.mjs";

const args = process.argv.slice(2);
const flags = {};
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith("--")) flags[args[i].slice(2)] = args[++i];
  else positional.push(args[i]);
}
const [bundleDir, nArg = "4"] = positional;
if (!bundleDir) {
  console.error("usage: node --experimental-strip-types tools/web/live_smoke.mjs <bundle-dir> [matches] [--seed S] [--modes m,...] [--hulls h,...]");
  process.exit(2);
}
const seed0 = Number(flags.seed ?? 1);
const modes = (flags.modes ?? "draft,2v2,3v3,4v4").split(",");

const { mulberry32 } = await importRepo("web/src/live/policy.js");
const { LiveMatch } = await importRepo("web/src/live/match.ts");
const { chooseRoster, parseRosterMode, matchupLine } = await importRepo("web/src/live/roster.ts");
const { assembleBundle, parseManifest } = await importRepo("web/src/live/bundle.ts");
const { TICK_BUDGET_MS } = await importRepo("web/src/live/sim.ts");

const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(bundleDir, rel), "utf8"));
const manifest = parseManifest(readJson("manifest.json"));
const { manifest: policyManifest, weights } = readPolicyFiles(path.join(bundleDir, "policy"));
const sim = await loadSim(path.join(bundleDir, "pkg"));
const bundle = assembleBundle(manifest, sim, policyManifest, weights, readJson("catalogue.json"));
const rules = flags.hulls ? { ...manifest.roster, hulls: flags.hulls.split(",") } : manifest.roster;

const wasmKiB = fs.statSync(path.join(bundleDir, "pkg/sim_wasm_bg.wasm")).size / 1024;
console.log(
  `live smoke: bundle ${manifest.bundle_id}, sim_version ${bundle.layout.simVersion}, wasm ${wasmKiB.toFixed(0)} KiB, ` +
    `champion ${manifest.champion.id} (${manifest.champion.hulls.join(", ")}), drafting ${rules.hulls.join(", ")}`,
);

let failed = false;
let worstMean = 0;
const tally = { 0: 0, 1: 0, draw: 0 };
for (let i = 0; i < Number(nArg); i++) {
  const seed = seed0 + i;
  const mode = modes[i % modes.length];
  const roster = chooseRoster(parseRosterMode(mode), rules, bundle.catalogue.info, mulberry32(seed ^ 0x5bd1e995));
  const match = new LiveMatch({ ...bundle, settings: manifest.match, fleets: roster.fleets, seed });
  let simTotal = 0;
  let nnTotal = 0;
  let nnWorst = 0;
  const limit = manifest.match.time_limit_ticks + 100;
  let nonFinite = false;
  while (!match.over && match.tick < limit) {
    match.step();
    simTotal += match.last.sim;
    nnTotal += match.last.nn;
    nnWorst = Math.max(nnWorst, match.last.nn);
    if (match.ships.some((s) => !Number.isFinite(s.x) || !Number.isFinite(s.y) || !Number.isFinite(s.hp))) nonFinite = true;
  }
  const label = `match ${i} seed ${seed} ${mode} [${roster.fleets.map((f) => f.join("+")).join(" vs ")}]`;
  if (nonFinite) {
    console.error(`live smoke: FAIL ${label}: non-finite ship state`);
    failed = true;
  }
  if (!match.over) {
    console.error(`live smoke: FAIL ${label} did not finish by tick ${match.tick}`);
    failed = true;
    match.free();
    continue;
  }
  const w = match.winner;
  tally[w === -1 ? "draw" : w] += 1;
  const meanSim = simTotal / match.tick;
  const meanNn = nnTotal / match.tick;
  worstMean = Math.max(worstMean, meanSim + meanNn);
  const values = match.teamValues().map((v) => v.toFixed(0)).join("/");
  console.log(
    `live smoke: ${label}: ${w === -1 ? "draw" : `team ${w} wins`} (${match.reason}) at tick ${match.tick} (${(match.tick / 30).toFixed(1)} s), value ${values}; ` +
      `tick ${(meanSim + meanNn).toFixed(3)} ms = sim ${meanSim.toFixed(3)} + inference ${meanNn.toFixed(3)} (worst inference ${nnWorst.toFixed(2)}) of ${TICK_BUDGET_MS.toFixed(1)} ms · "${matchupLine(roster)}"`,
  );
  match.free();
}
console.log(`live smoke: team 0 ${tally[0]} · team 1 ${tally[1]} · draws ${tally.draw}`);
if (worstMean > TICK_BUDGET_MS) {
  console.error(`live smoke: FAIL mean tick ${worstMean.toFixed(2)} ms exceeds the ${TICK_BUDGET_MS.toFixed(1)} ms budget`);
  failed = true;
}
process.exit(failed ? 1 : 0);
