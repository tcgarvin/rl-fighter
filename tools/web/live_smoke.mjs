// Headless smoke test of the live page's match loop: loads a champion bundle
// (scripts/build_bundle.sh), stages missions and rosters with web/src/live/missions.ts
// and roster.ts and plays full matches with web/src/live/match.ts (the page's own
// code): strike craft flown by the JS policy, capital ships by the sim's scripts, each
// side's commander from the bundle's stable (a learned one runs web/src/live/
// commander.js in the sim's "learned" mode). Prints each roster, winner, end reason,
// mission events, each side's commander with its decisions, commands, orders and
// launches, and the per-tick sim / inference cost and per-decision commander cost;
// exits non-zero if a match does not finish with a proper end reason,
// a ship's state goes non-finite, an event kind is unknown, a mission's defining
// events never happen (no launch in a carrier battle, no convoy jump-out or kill in a
// convoy escort), a learned commander never decides, or a mean tick blows the 30 Hz
// budget. The TS sources need Node's type stripping:
//
//   node --experimental-strip-types tools/web/live_smoke.mjs <bundle-dir> [matches=4]
//        [--seed 1] [--modes draft,carrier_battle,convoy_escort,2v2,3v3,4v4]
//        [--hulls fighter,strafer,gunship] [--commanders <azure>,<ember>|draw]
//
// --modes cycles what each match stages: a mission name (carrier_battle,
// convoy_escort; the page's ?mission=) or a deathmatch roster mode (as ?fleets=;
// "draft" uses the manifest's roster rules). The default puts the three missions
// first, so the bundle build's 4 smoke matches cover every one. --hulls overrides
// which strike craft are drafted, to exercise fleets before a champion is certified.
// --commanders pins each side's commander by id (as the page's ?commander=); "draw"
// draws them as the page does. By default a bundle with a learned commander cycles
// learned vs learned, learned vs scripted, scripted vs learned, then a draw, so the
// bundle build's 4 smoke matches put a learned commander on each side.

import fs from "node:fs";
import path from "node:path";
import { importRepo, loadSim, readCommanderFiles, readPilotFiles, readPolicyFiles } from "./load.mjs";

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
const modes = (flags.modes ?? "draft,carrier_battle,convoy_escort,2v2,3v3,4v4").split(",");

const { mulberry32 } = await importRepo("web/src/live/policy.js");
const { LiveMatch, assignCommanders } = await importRepo("web/src/live/match.ts");
const { parseRosterMode, matchupLine } = await importRepo("web/src/live/roster.ts");
const { availableMissions, defaultRosters, missionRoster, parseMission, missionBrief, MISSION_TITLES } = await importRepo("web/src/live/missions.ts");
const { assembleBundle, commanderName, parseManifest } = await importRepo("web/src/live/bundle.ts");
const { TICK_BUDGET_MS } = await importRepo("web/src/live/sim.ts");

const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(bundleDir, rel), "utf8"));
const manifest = parseManifest(readJson("manifest.json"));
const { manifest: policyManifest, weights } = readPolicyFiles(path.join(bundleDir, "policy"));
const sim = await loadSim(path.join(bundleDir, "pkg"));
const bundle = assembleBundle(
  manifest,
  sim,
  policyManifest,
  weights,
  readJson("catalogue.json"),
  readPilotFiles(bundleDir, manifest),
  readCommanderFiles(bundleDir, manifest),
);
const byId = (id) => {
  const c = bundle.commanders.find((x) => x.id === id);
  if (!c) {
    console.error(`live smoke: no commander ${id} in the stable (${bundle.commanders.map((x) => x.id).join(", ")})`);
    process.exit(2);
  }
  return c;
};
const learnedIds = bundle.commanders.filter((c) => c.net).map((c) => c.id);
// Each match's commanders: pinned, a plan that puts a learned one on each side, or the draw.
function commandersFor(i, seed) {
  if (flags.commanders && flags.commanders !== "draw") {
    const ids = flags.commanders.split(",");
    return [byId(ids[0]), byId(ids[1] ?? ids[0])];
  }
  if (flags.commanders === "draw" || learnedIds.length === 0) return assignCommanders(bundle.commanders, seed);
  const L = byId(learnedIds[i % learnedIds.length]);
  const S = byId("scripted");
  const plan = [[L, L], [L, S], [S, L], null][i % 4];
  return plan ?? assignCommanders(bundle.commanders, seed);
}
const commanded = new Map();
const flown = new Map();
const rules = flags.hulls ? { ...manifest.roster, hulls: flags.hulls.split(",") } : manifest.roster;
// Node has no renderer: every catalogue hull counts as drawable here.
const available = availableMissions(bundle.layout.simVersion, bundle.catalogue.info, () => true);
const rosters = defaultRosters(sim);

const wasmKiB = fs.statSync(path.join(bundleDir, "pkg/sim_wasm_bg.wasm")).size / 1024;
console.log(
  `live smoke: bundle ${manifest.bundle_id}, sim_version ${bundle.layout.simVersion}, wasm ${wasmKiB.toFixed(0)} KiB, ` +
    `champion ${manifest.champion.id} (${manifest.champion.hulls.join(", ")}), ${bundle.pilots.length} pilots, ` +
    `commanders ${bundle.commanders.map((c) => `${c.id} (${c.kind})`).join(", ")}, drafting ${rules.hulls.join(", ")}; missions ${available.join(", ")}`,
);

const stripTags = (html) => html.replace(/<[^>]+>/g, "");
let failed = false;
let worstMean = 0;
const tally = { 0: 0, 1: 0, draw: 0 };
for (let i = 0; i < Number(nArg); i++) {
  const seed = seed0 + i;
  const mode = modes[i % modes.length];
  const mission = parseMission(mode) ?? "deathmatch";
  if (!available.includes(mission)) {
    console.error(`live smoke: FAIL this bundle cannot stage ${mission} (it has ${available.join(", ")})`);
    failed = true;
    continue;
  }
  const roster = missionRoster(mission, parseRosterMode(mission === "deathmatch" ? mode : null), rules, bundle.catalogue.info, mulberry32(seed ^ 0x5bd1e995), rosters);
  const commanders = commandersFor(i, seed);
  const match = new LiveMatch({ ...bundle, settings: manifest.match, fleets: roster.fleets, seed, mission, commanders });
  for (let s = 0; s < match.nShips; s++) {
    const id = match.pilotId(s);
    if (id) flown.set(id, (flown.get(id) ?? 0) + 1);
  }
  const b = missionBrief(mission, match.convoy);
  const brief = stripTags(`${b.headline ? `${b.headline} ` : ""}${b.brief}`);
  let simTotal = 0;
  let nnTotal = 0;
  let nnWorst = 0;
  const counts = { launch: 0, order: 0, jumpCharge: 0, jumpOut: 0, matchEnd: 0, arrival: 0, death: 0, unknown: 0 };
  const limit = match.timeLimitTicks + 100;
  let nonFinite = false;
  let peakPresent = 0;
  // Per side: Order events (squad orders that changed) and bay launches.
  const sideOrders = [0, 0];
  const sideLaunches = [0, 0];
  while (!match.over && match.tick < limit) {
    match.step();
    simTotal += match.last.sim;
    nnTotal += match.last.nn;
    nnWorst = Math.max(nnWorst, match.last.nn);
    for (const e of match.events) {
      if (e.kind in counts) counts[e.kind] += 1;
      if (e.kind === "order") sideOrders[e.a] += 1;
      if (e.kind === "launch") sideLaunches[match.ships[e.a].team] += 1;
    }
    peakPresent = Math.max(peakPresent, match.ships.filter((s) => match.active(s)).length);
    if (match.ships.some((s) => !Number.isFinite(s.x) || !Number.isFinite(s.y) || !Number.isFinite(s.hp))) nonFinite = true;
  }
  const label = `match ${i} seed ${seed} ${mission === "deathmatch" ? mode : `${mission} (${roster.name ?? "drafted"})`} [${roster.fleets.map((f) => f.join("+")).join(" vs ")}]`;
  const fail = (why) => {
    console.error(`live smoke: FAIL ${label}: ${why}`);
    failed = true;
  };
  if (nonFinite) fail("non-finite ship state");
  if (counts.unknown) fail(`${counts.unknown} events of an unknown kind`);
  if (!match.over) {
    fail(`did not finish by tick ${match.tick}`);
    match.free();
    continue;
  }
  if (match.simReason === "not_over") fail("over, but the sim reports no end reason");
  if (bundle.layout.simVersion >= 4 && counts.matchEnd !== 1) fail(`${counts.matchEnd} MatchEnd events (want 1)`);
  if (mission === "carrier_battle" && counts.launch === 0) fail("no bay launch in a carrier battle");
  const c = match.convoy;
  if (mission === "convoy_escort" && (!c || c.escaped + c.destroyed === 0) && match.simReason !== "eliminated") fail("no freighter escaped or died");
  const w = match.winner;
  tally[w === -1 ? "draw" : w] += 1;
  const meanSim = simTotal / match.tick;
  const meanNn = nnTotal / match.tick;
  worstMean = Math.max(worstMean, meanSim + meanNn);
  const values = match.teamValues().map((v) => v.toFixed(0)).join("/");
  const extra =
    mission === "carrier_battle"
      ? `; carriers ${match.teams.map((t) => `${Math.round((100 * Math.max(0, t.hp)) / Math.max(1, t.maxHp))}%`).join("/")}, hangars ${match.teams.map((t) => t.hangar).join("/")}`
      : mission === "convoy_escort" && c
        ? `; convoy ${c.escaped} escaped / ${c.destroyed} destroyed of ${c.total} (need ${c.toEscape} / ${c.toDestroy})`
        : "";
  const ev = `events launch ${counts.launch} arrival ${counts.arrival} order ${counts.order} charge ${counts.jumpCharge} jump-out ${counts.jumpOut} death ${counts.death}`;
  const sides = [0, 1].map((t) => {
    const c = match.commanders[t];
    const st = match.commanderStats[t];
    const tally = commanded.get(c.id) ?? { sides: 0, decisions: 0, commands: 0, orders: 0, launches: 0, ms: 0, worstMs: 0 };
    Object.assign(tally, {
      sides: tally.sides + 1,
      decisions: tally.decisions + st.decisions,
      commands: tally.commands + st.commands,
      orders: tally.orders + sideOrders[t],
      launches: tally.launches + sideLaunches[t],
      ms: tally.ms + st.ms,
      worstMs: Math.max(tally.worstMs, st.worstMs),
    });
    commanded.set(c.id, tally);
    if (c.net && st.decisions === 0) fail(`${["azure", "ember"][t]}'s learned commander ${c.id} never decided`);
    const cost = c.net ? `, ${st.decisions} decisions → ${st.commands} commands, ${(st.ms / Math.max(1, st.decisions)).toFixed(2)} ms/decision (worst ${st.worstMs.toFixed(2)})` : "";
    return `${["azure", "ember"][t]} ${commanderName(c)} (orders ${sideOrders[t]}, launches ${sideLaunches[t]}${cost})`;
  });
  console.log(
    `live smoke: ${label}: ${w === -1 ? "draw" : `team ${w} wins`} (${match.simReason}) at tick ${match.tick} (${(match.tick / 30).toFixed(1)} s), value ${values}${extra}; ${ev}; peak ${peakPresent} ships on the field; ` +
      `tick ${(meanSim + meanNn).toFixed(3)} ms = sim ${meanSim.toFixed(3)} + inference ${meanNn.toFixed(3)} (worst inference ${nnWorst.toFixed(2)}) of ${TICK_BUDGET_MS.toFixed(1)} ms · ` +
      `"${MISSION_TITLES[mission]}: ${brief} ${matchupLine(roster, bundle.catalogue.info)}"`,
  );
  console.log(`live smoke:   commanders ${sides.join(" · ")}`);
  match.free();
}
console.log(`live smoke: team 0 ${tally[0]} · team 1 ${tally[1]} · draws ${tally.draw}`);
console.log(`live smoke: strike craft per pilot: ${[...flown].sort().map(([id, n]) => `${id} ${n}`).join(", ")}`);
for (const [id, t] of [...commanded].sort()) {
  const cost = t.decisions ? `, ${t.decisions} decisions → ${t.commands} commands, ${(t.ms / t.decisions).toFixed(2)} ms/decision (worst ${t.worstMs.toFixed(2)})` : "";
  console.log(`live smoke: commander ${id}: ${t.sides} sides, ${t.orders} orders, ${t.launches} launches${cost}`);
}
if (bundle.pilots.length > 1 && flown.size < 2) {
  console.error(`live smoke: FAIL ${bundle.pilots.length} pilots in the bundle, but only ${flown.size} flew`);
  failed = true;
}
if (worstMean > TICK_BUDGET_MS) {
  console.error(`live smoke: FAIL mean tick ${worstMean.toFixed(2)} ms exceeds the ${TICK_BUDGET_MS.toFixed(1)} ms budget`);
  failed = true;
}
process.exit(failed ? 1 : 0);
