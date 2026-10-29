// One live match: the WASM sim with every ship flown by the champion policy, stepped
// one 30 Hz tick at a time. No DOM or three.js here, so tools/web/live_smoke.mjs runs
// the same loop headless in Node.

import { mulberry32, type Policy, type Rng } from "./policy.js";
import {
  EVENT_KINDS,
  MAX_THRUSTERS,
  MAX_TURRETS,
  PROJECTILE_KINDS,
  type Catalogue,
  type MatchSettings,
  type ProjectileState,
  type ShipState,
  type SimEvent,
  type SimLayout,
  type SimModule,
  type WasmMatch,
} from "./sim.ts";

// Matches SIM_SPEC §5.8's time-limit tiebreak: Σ_alive (hp + 0.5 · shield).
const VALUE_SHIELD_WEIGHT = 0.5;

export type Fleets = [string[], string[]];

/** Why a finished match ended, for the result banner. */
export type EndReason = "eliminated" | "mutual" | "time";

export interface Timing {
  /** Moving averages over ~30 ticks, ms. */
  sim: number;
  nn: number;
  ticks: number;
}

export interface LiveMatchOptions {
  sim: SimModule;
  layout: SimLayout;
  catalogue: Catalogue;
  policy: Policy;
  settings: MatchSettings;
  fleets: Fleets;
  seed: number;
}

export class LiveMatch {
  readonly seed: number;
  readonly fleets: Fleets;
  readonly settings: MatchSettings;
  readonly nShips: number;
  readonly ships: ShipState[] = [];
  readonly maxHp: number[];
  /** Hull name per ship (catalogue order resolved). */
  readonly hullNames: string[];
  /** Live projectiles after the last step; the array and its objects are reused. */
  projectiles: ProjectileState[] = [];
  /** Events of the last step; the array and its objects are reused. */
  events: SimEvent[] = [];
  readonly timing: Timing = { sim: 0, nn: 0, ticks: 0 };
  /** The last tick's exact split, ms. */
  last = { sim: 0, nn: 0 };

  private readonly sim: SimModule;
  private readonly layout: SimLayout;
  private readonly policy: Policy;
  private match: WasmMatch | null;
  private readonly headValid: Uint8Array[];
  private readonly rngs: Rng[];
  private readonly row: Int8Array;
  private readonly projectilePool: ProjectileState[] = [];
  private readonly eventPool: SimEvent[] = [];

  constructor(o: LiveMatchOptions) {
    this.sim = o.sim;
    this.layout = o.layout;
    this.policy = o.policy;
    this.seed = o.seed;
    this.fleets = o.fleets;
    this.settings = o.settings;
    this.match = new o.sim.WasmMatch(
      o.catalogue.hulls,
      o.catalogue.weapons,
      JSON.stringify({
        seed: o.seed,
        arena_radius: o.settings.arena_radius,
        time_limit_ticks: o.settings.time_limit_ticks,
        reaction_ticks: o.settings.reaction_ticks,
        fleets: o.fleets,
      }),
    );
    this.nShips = o.fleets[0].length + o.fleets[1].length;
    this.row = new Int8Array(o.layout.actionWidth);
    const m = this.match;
    this.headValid = Array.from({ length: this.nShips }, (_, s) => m.head_valid(s));
    // Distinct, reproducible sampling streams per ship.
    this.rngs = Array.from({ length: this.nShips }, (_, s) => mulberry32(Math.imul(o.seed | 0, 0x9e3779b1) + s * 40503 + 1));
    this.readShips();
    this.maxHp = this.ships.map((s) => s.hp);
    this.hullNames = this.ships.map((s) => o.catalogue.hulls[s.hull]?.[0] ?? "unknown");
  }

  private get wasm(): WasmMatch {
    if (!this.match) throw new Error("match already freed");
    return this.match;
  }

  get tick(): number {
    return this.wasm.tick();
  }

  get over(): boolean {
    return this.wasm.phase() === 1;
  }

  /** -2 running, -1 draw, else the winning team. */
  get winner(): number {
    return this.wasm.winner();
  }

  get reason(): EndReason {
    const alive = [0, 0];
    for (const s of this.ships) if (s.alive) alive[s.team] = (alive[s.team] ?? 0) + 1;
    if (alive[0] === 0 && alive[1] === 0) return "mutual";
    if (alive[0] === 0 || alive[1] === 0) return "eliminated";
    return "time";
  }

  /** Each team's time-limit value (hull plus half of shields, alive ships). */
  teamValues(): [number, number] {
    const v: [number, number] = [0, 0];
    for (const s of this.ships) if (s.alive) v[s.team === 0 ? 0 : 1] += Math.max(0, s.hp) + VALUE_SHIELD_WEIGHT * s.shield;
    return v;
  }

  /** Choose every ship's action with the policy, advance one tick, refresh the views. */
  step(): void {
    const m = this.wasm;
    let nn = 0;
    for (let s = 0; s < this.nShips; s++) {
      const ship = this.ships[s]!;
      // An absent or dead ship's row is discarded by the sim (SIM_SPEC §7.1), so skip
      // its forward pass.
      if (!ship.alive || !ship.present) continue;
      const t0 = performance.now();
      this.policy.act(m.obs(s), this.headValid[s]!, this.rngs[s]!, this.row);
      nn += performance.now() - t0;
      m.set_action(s, this.row);
    }
    const t1 = performance.now();
    m.step();
    const simMs = performance.now() - t1;
    this.readShips();
    this.readProjectiles();
    this.readEvents();
    this.last = { sim: simMs, nn };
    const k = this.timing.ticks === 0 ? 1 : 1 / 30;
    this.timing.sim += (simMs - this.timing.sim) * k;
    this.timing.nn += (nn - this.timing.nn) * k;
    this.timing.ticks += 1;
  }

  /** Release the wasm match. The object is unusable afterwards. */
  free(): void {
    this.match?.free();
    this.match = null;
  }

  private view(ptr: number, len: number): Float32Array {
    return new Float32Array(this.sim.wasm_memory().buffer, ptr, len);
  }

  private readShips(): void {
    const L = this.layout;
    const v = this.view(this.wasm.ships_ptr(), this.wasm.ships_len());
    const n = v.length / L.shipStride;
    for (let i = 0; i < n; i++) {
      const o = i * L.shipStride;
      let s = this.ships[i];
      if (!s) {
        s = {
          id: i, x: 0, y: 0, vx: 0, vy: 0, heading: 0, omega: 0, hp: 0, shield: 0, alive: false, present: false, team: 0, hull: 0,
          throttles: new Float32Array(MAX_THRUSTERS),
          turretAngles: new Float32Array(MAX_TURRETS),
          power: new Float32Array(3),
        };
        this.ships[i] = s;
      }
      s.x = v[o]!;
      s.y = v[o + 1]!;
      s.vx = v[o + 2]!;
      s.vy = v[o + 3]!;
      s.heading = v[o + 4]!;
      s.omega = v[o + 5]!;
      s.hp = v[o + 6]!;
      s.shield = v[o + 7]!;
      s.alive = v[o + 8]! > 0.5;
      s.present = v[o + 9]! > 0.5;
      s.team = v[o + 10]!;
      s.hull = v[o + 11]!;
      s.throttles.set(v.subarray(o + L.throttleOffset, o + L.throttleOffset + MAX_THRUSTERS));
      s.turretAngles.set(v.subarray(o + L.turretOffset, o + L.turretOffset + MAX_TURRETS));
      s.power.set(v.subarray(o + L.powerOffset, o + L.powerOffset + 3));
    }
  }

  private readProjectiles(): void {
    const stride = this.layout.projectileStride;
    const v = this.view(this.wasm.projectiles_ptr(), this.wasm.projectiles_len());
    const n = v.length / stride;
    const pool = this.projectilePool;
    while (pool.length < n) pool.push({ slot: 0, kind: "bullet", team: 0, owner: 0, x: 0, y: 0, vx: 0, vy: 0 });
    for (let i = 0; i < n; i++) {
      const o = i * stride;
      const p = pool[i]!;
      p.slot = v[o]!;
      p.kind = PROJECTILE_KINDS[v[o + 1]!] ?? "bullet";
      p.team = v[o + 2]!;
      p.owner = v[o + 3]!;
      p.x = v[o + 4]!;
      p.y = v[o + 5]!;
      p.vx = v[o + 6]!;
      p.vy = v[o + 7]!;
    }
    this.projectiles = pool.slice(0, n);
  }

  private readEvents(): void {
    const stride = this.layout.eventStride;
    const v = this.view(this.wasm.events_ptr(), this.wasm.events_len());
    const n = v.length / stride;
    const pool = this.eventPool;
    while (pool.length < n) pool.push({ kind: "unknown", a: 0, b: 0, x: 0, y: 0, f5: 0, f6: 0, extra: 0 });
    for (let i = 0; i < n; i++) {
      const o = i * stride;
      const e = pool[i]!;
      e.kind = EVENT_KINDS[v[o]!] ?? "unknown";
      e.a = v[o + 1]!;
      e.b = v[o + 2]!;
      e.x = v[o + 3]!;
      e.y = v[o + 4]!;
      e.f5 = v[o + 5]!;
      e.f6 = v[o + 6]!;
      e.extra = v[o + 7]!;
    }
    this.events = pool.slice(0, n);
  }
}
