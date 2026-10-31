// Node smoke test of the wasm-bindgen build (SIM_SPEC §12): runs the scripted §12
// scenarios to Over through WasmMatch and checks the final tick, state hash and
// winner against the natively generated golden traces in crates/sim/tests/golden/.
//
// Usage: node crates/sim-wasm/tests/node_smoke.mjs <pkg-dir>
// where <pkg-dir> is `wasm-pack build crates/sim-wasm --target web --out-dir <pkg-dir>`:
// the same optimised bundle the browser loads, instantiated here with initSync.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

if (!process.argv[2]) {
  console.error("usage: node node_smoke.mjs <wasm-pack --target web pkg dir>");
  process.exit(2);
}
const pkgDir = path.resolve(process.argv[2]);
const sim = await import(pathToFileURL(path.join(pkgDir, "sim_wasm.js")).href);
sim.initSync({ module: fs.readFileSync(path.join(pkgDir, "sim_wasm_bg.wasm")) });

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const read = (rel) => fs.readFileSync(path.join(repo, rel), "utf8");
// Every shipped hull (v4 ids: carrier 0, fighter 1, freighter 2, gunship 3, strafer 4).
const hulls = ["carrier", "fighter", "freighter", "gunship", "strafer"].map((n) => [n, read(`assets/hulls/${n}/hull.yaml`)]);
const weapons = read("assets/weapons.yaml");

const scenarios = [
  { golden: "duel_fighter_s7", seed: 7, fleets: [["fighter"], ["fighter"]] },
  { golden: "2v2_mixed_s11", seed: 11, fleets: [["fighter", "strafer"], ["gunship", "fighter"]] },
  {
    golden: "3v3_mixed_s13",
    seed: 13,
    fleets: [
      ["fighter", "strafer", "gunship"],
      ["gunship", "fighter", "strafer"],
    ],
  },
  // v4 missions, stub commanders on both sides.
  {
    golden: "carrier_battle_s23",
    seed: 23,
    extra: { mission: "carrier_battle", time_limit_ticks: 9000 },
    fleets: [
      ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"],
      ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"],
    ],
  },
  {
    golden: "convoy_escort_s29",
    seed: 29,
    extra: { mission: { kind: "convoy_escort" }, time_limit_ticks: 9000 },
    fleets: [
      ["freighter", "freighter", "freighter", "freighter", "fighter", "strafer", "fighter"],
      ["fighter", "fighter", "strafer", "gunship", "fighter", "strafer"],
    ],
  },
  // v5: the random commander on both sides.
  {
    golden: "carrier_battle_random_s31",
    seed: 31,
    extra: { mission: "carrier_battle", time_limit_ticks: 9000, commanders: ["random", "random"] },
    fleets: [
      ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"],
      ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"],
    ],
  },
];

function goldenEnd(name) {
  const line = read(`crates/sim/tests/golden/${name}.txt`)
    .split("\n")
    .find((l) => l.startsWith("end "));
  const [, tick, hash, , phase, winner] = line.split(/\s+/);
  return { tick: Number(tick), hash, phase, winner: Number(winner) };
}

function check(cond, msg) {
  if (!cond) {
    console.error(`node smoke: FAIL ${msg}`);
    process.exit(1);
  }
}

check(sim.SHIP_STRIDE() === 29 && sim.EVENT_STRIDE() === 8 && sim.PROJECTILE_STRIDE() === 8, "strides");
check(sim.ACTION_WIDTH() === 21 && sim.OBS_DIM() === 583, "action/obs widths");
check(sim.sim_version() === 6 && Array.from(sim.pilot_compat_versions()).join() === "3,4,5,6", "v6 + pilot compat");
check(
  sim.pilotObsDim(3) === 385 && sim.pilotObsDim(4) === 385 && sim.pilotObsDim(5) === 403 && sim.pilotObsDim(6) === 583,
  "pilot obs dims",
);
check(JSON.stringify(JSON.parse(sim.pilotObsDimsJson())) === '{"3":385,"4":385,"5":403,"6":583}', "pilotObsDimsJson");
check(JSON.parse(sim.obsLayoutJson()).blocks.at(-1).join() === "order_ships,473,110", "obs layout ends with the order_ships block");
check(sim.MAX_TRAIN_SHIPS() === 12, "MAX_TRAIN_SHIPS");
check(sim.pilot_compatible(3) && !sim.pilot_compatible(2), "pilot_compatible");
check(sim.SHIP_EXT_STRIDE() === 10 && sim.SQUAD_STRIDE() === 9 && sim.TEAM_STRIDE() === 8 && sim.CONVOY_STRIDE() === 14, "v4 strides");
check(sim.MAX_SHIPS() === 20 && sim.COMMAND_TICKS() === 60 && sim.arenaRadiusForMission("convoy_escort", 13) === 450, "v4 constants");

let threw = false;
try {
  new sim.WasmMatch(hulls, weapons, '{"seed":1,"fleets":[["fighter"],["bomber"]]}');
} catch (e) {
  threw = String(e.message ?? e).includes("bomber");
}
check(threw, "unknown hull should throw a JS error naming it");

for (const sc of scenarios) {
  const cfg = JSON.stringify({ seed: sc.seed, ...(sc.extra ?? {}), fleets: sc.fleets });
  const m = new sim.WasmMatch(hulls, weapons, cfg);
  const nShips = sc.fleets[0].length + sc.fleets[1].length;
  let maxEvents = 0;
  while (m.phase() === 0 && m.tick() < 9000) {
    for (let s = 0; s < nShips; s++) m.set_action(s, m.scripted_action(s));
    m.step();
    const mem = sim.wasm_memory().buffer;
    const ships = new Float32Array(mem, m.ships_ptr(), m.ships_len());
    check(ships.length === nShips * sim.SHIP_STRIDE(), `${sc.golden} ships view length`);
    const ext = new Float32Array(mem, m.ship_ext_ptr(), m.ship_ext_len());
    check(ext.length === nShips * sim.SHIP_EXT_STRIDE(), `${sc.golden} ship_ext view length`);
    const events = new Float32Array(mem, m.events_ptr(), m.events_len());
    maxEvents = Math.max(maxEvents, events.length / sim.EVENT_STRIDE());
  }
  check(m.obs(0).length === sim.OBS_DIM(), "obs length");
  const want = goldenEnd(sc.golden);
  const got = { tick: m.tick(), hash: m.state_hash_hex(), winner: m.winner() };
  check(
    want.phase === "over" && got.tick === want.tick && got.hash === want.hash && got.winner === want.winner,
    `${sc.golden}: node ${JSON.stringify(got)} != native ${JSON.stringify(want)}`,
  );
  console.log(`node smoke: ${sc.golden} over at tick ${got.tick} hash ${got.hash} winner ${got.winner} (== native)`);
  m.free();
}
