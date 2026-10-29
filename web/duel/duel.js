// One live duel: the WASM sim plus a controller per ship (the learned policy or the
// hand-written script), stepped one 30 Hz tick at a time. No DOM or three.js here, so
// tools/web_duel_smoke.mjs runs the same loop headless in Node.

import { mulberry32 } from "./policy.js";

export const SIM_HZ = 30;
export const SIM_DT = 1 / SIM_HZ;
export const TICK_BUDGET_MS = 1000 / SIM_HZ;

export const MODES = {
  "learned-vs-script": { label: "Learned vs Script", controllers: ["learned", "script"] },
  "learned-vs-learned": { label: "Learned vs Learned", controllers: ["learned", "learned"] },
};

const PROJECTILE_KINDS = ["bullet", "beam", "flak", "torpedo"];
const EVENT_KINDS = ["fire", "beam", "hit", "shieldHit", "burst", "death", "arrival", "collision"];
// performance.now() is a global in browsers and Node 16+.
const now = () => performance.now();

/**
 * Read the static module constants once.
 * `sim` is the wasm-bindgen module (sim_wasm.js), already initialised.
 */
export function simLayout(sim) {
  return {
    simVersion: sim.sim_version(),
    obsDim: sim.OBS_DIM(),
    actionWidth: sim.ACTION_WIDTH(),
    shipStride: sim.SHIP_STRIDE(),
    throttleOffset: sim.SHIP_THROTTLE_OFFSET(),
    turretOffset: sim.SHIP_TURRET_OFFSET(),
    powerOffset: sim.SHIP_POWER_OFFSET(),
    projectileStride: sim.PROJECTILE_STRIDE(),
    eventStride: sim.EVENT_STRIDE(),
  };
}

/**
 * A running duel. `catalogue` = { hulls: [[name, yaml], ...], weapons: yaml };
 * `matchConfig` = the policy manifest's match_config (fleets, arena, time limit,
 * reaction ticks: what the policy trained on).
 */
export class Duel {
  constructor({ sim, catalogue, policy, matchConfig }) {
    this.sim = sim;
    this.layout = simLayout(sim);
    this.catalogue = catalogue;
    this.policy = policy;
    this.matchConfig = matchConfig;
    this.match = null;
    this.row = new Int8Array(this.layout.actionWidth);
    // Rolling per-tick timings (ms) for the perf readout.
    this.timing = { sim: 0, nn: 0, ticks: 0 };
    // The last tick's exact split (ms).
    this.last = { sim: 0, nn: 0 };
  }

  /** Start a fresh match. `mode` is a MODES key; `seed` drives both the sim and sampling. */
  start(mode, seed) {
    this.match?.free();
    const cfg = this.matchConfig;
    this.mode = mode;
    this.seed = seed;
    this.controllers = MODES[mode].controllers;
    this.match = new this.sim.WasmMatch(
      this.catalogue.hulls,
      this.catalogue.weapons,
      JSON.stringify({
        seed,
        arena_radius: cfg.arena_radius,
        time_limit_ticks: cfg.time_limit_ticks,
        reaction_ticks: cfg.reaction_ticks,
        fleets: cfg.fleets,
      }),
    );
    this.nShips = cfg.fleets[0].length + cfg.fleets[1].length;
    if (this.controllers.length !== this.nShips) throw new Error(`mode ${mode} has ${this.controllers.length} controllers for ${this.nShips} ships`);
    this.headValid = Array.from({ length: this.nShips }, (_, s) => this.match.head_valid(s));
    // Distinct, reproducible sampling streams per ship.
    this.rngs = Array.from({ length: this.nShips }, (_, s) => mulberry32(Math.imul(seed | 0, 0x9e3779b1) + s * 40503 + 1));
    this.ships = [];
    this.readShips();
    this.maxHp = this.ships.map((s) => s.hp);
    this.projectiles = [];
    this.events = [];
  }

  get tick() {
    return this.match.tick();
  }

  get over() {
    return this.match.phase() === 1;
  }

  /** -2 running, -1 draw, else the winning team. */
  get winner() {
    return this.match.winner();
  }

  /** Choose every ship's action, advance one tick, and refresh ships/projectiles/events. */
  step() {
    const m = this.match;
    let nn = 0;
    for (let s = 0; s < this.nShips; s++) {
      const ship = this.ships[s];
      if (this.controllers[s] === "script") {
        m.set_action(s, m.scripted_action(s));
        continue;
      }
      // An absent or dead ship's row is discarded by the sim (SIM_SPEC §7.1), so skip
      // its forward pass.
      if (!ship.alive || !ship.present) continue;
      const t0 = now();
      const obs = m.obs(s);
      this.policy.act(obs, this.headValid[s], this.rngs[s], this.row);
      nn += now() - t0;
      m.set_action(s, this.row);
    }
    const t1 = now();
    m.step();
    const simMs = now() - t1;
    this.readShips();
    this.readProjectiles();
    this.readEvents();
    this.last = { sim: simMs, nn };
    // Exponential moving average over ~30 ticks; first sample seeds it.
    const k = this.timing.ticks === 0 ? 1 : 1 / 30;
    this.timing.sim += (simMs - this.timing.sim) * k;
    this.timing.nn += (nn - this.timing.nn) * k;
    this.timing.ticks += 1;
  }

  readShips() {
    const L = this.layout;
    const v = new Float32Array(this.sim.wasm_memory().buffer, this.match.ships_ptr(), this.match.ships_len());
    const n = v.length / L.shipStride;
    for (let i = 0; i < n; i++) {
      const o = i * L.shipStride;
      const s = (this.ships[i] ??= { id: i, throttles: new Float32Array(8), turretAngles: new Float32Array(6), power: new Float32Array(3) });
      s.x = v[o];
      s.y = v[o + 1];
      s.vx = v[o + 2];
      s.vy = v[o + 3];
      s.heading = v[o + 4];
      s.omega = v[o + 5];
      s.hp = v[o + 6];
      s.shield = v[o + 7];
      s.alive = v[o + 8] > 0.5;
      s.present = v[o + 9] > 0.5;
      s.team = v[o + 10];
      s.hull = v[o + 11];
      s.throttles.set(v.subarray(o + L.throttleOffset, o + L.throttleOffset + 8));
      s.turretAngles.set(v.subarray(o + L.turretOffset, o + L.turretOffset + 6));
      s.power.set(v.subarray(o + L.powerOffset, o + L.powerOffset + 3));
    }
  }

  readProjectiles() {
    const L = this.layout;
    const v = new Float32Array(this.sim.wasm_memory().buffer, this.match.projectiles_ptr(), this.match.projectiles_len());
    const out = [];
    for (let o = 0; o < v.length; o += L.projectileStride) {
      out.push({ slot: v[o], kind: PROJECTILE_KINDS[v[o + 1]] ?? "bullet", team: v[o + 2], owner: v[o + 3], x: v[o + 4], y: v[o + 5], vx: v[o + 6], vy: v[o + 7] });
    }
    this.projectiles = out;
  }

  readEvents() {
    const L = this.layout;
    const v = new Float32Array(this.sim.wasm_memory().buffer, this.match.events_ptr(), this.match.events_len());
    const out = [];
    for (let o = 0; o < v.length; o += L.eventStride) {
      out.push({ kind: EVENT_KINDS[v[o]] ?? "unknown", a: v[o + 1], b: v[o + 2], x: v[o + 3], y: v[o + 4], f5: v[o + 5], f6: v[o + 6], extra: v[o + 7] });
    }
    this.events = out;
  }
}
