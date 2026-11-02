// One live match: the WASM sim stepped one 30 Hz tick at a time, each strike craft
// flown by a pilot picked for it at random and every capital ship (carrier, freighter)
// by the sim's own script (SIM_SPEC §11). The commanders are scripted inside the sim's step.
// No DOM or three.js here, so tools/web/live_smoke.mjs runs the same loop headless.

import { mulberry32, type Rng } from "./policy.js";
import type { LivePilot } from "./bundle.ts";
import type { MissionName } from "./missions.ts";
import {
  END_REASONS,
  EVENT_KINDS,
  JUMP_DEPARTED,
  MAX_THRUSTERS,
  MAX_TURRETS,
  ORDER_KINDS,
  PROJECTILE_KINDS,
  shipRole,
  type Catalogue,
  type ConvoyState,
  type MatchSettings,
  type ProjectileState,
  type ShipState,
  type SimEndReason,
  type SimEvent,
  type SimLayout,
  type SimModule,
  type SquadState,
  type TeamState,
  type WasmMatch,
} from "./sim.ts";

// Matches SIM_SPEC §5.8's time-limit tiebreak: Σ_in_match (hp + 0.5 · shield).
const VALUE_SHIELD_WEIGHT = 0.5;

export type Fleets = [string[], string[]];

/** Why a finished match ended, for the result banner. */
export type EndReason = "eliminated" | "mutual" | "time" | "carrier" | "convoy_through" | "convoy_destroyed";

const REASONS: Partial<Record<SimEndReason, EndReason>> = {
  eliminated: "eliminated",
  time_limit: "time",
  carrier_destroyed: "carrier",
  convoy_through: "convoy_through",
  convoy_destroyed: "convoy_destroyed",
};

export interface Timing {
  /** Moving averages over ~30 ticks, ms (sim includes the capital-ship scripts). */
  sim: number;
  nn: number;
  ticks: number;
}

// Keeps the pilot draw apart from the ships' sampling streams and the roster draw.
const PILOT_SALT = 0x70696c6f;

/** One pilot per ship, each drawn alone from `pilots`, the same for the same seed. */
export function assignPilots<P>(pilots: readonly P[], nShips: number, seed: number): P[] {
  const rng = mulberry32(Math.imul(seed | 0, 0x2545f491) ^ PILOT_SALT);
  return Array.from({ length: nShips }, () => pilots[Math.floor(rng() * pilots.length)]!);
}

/** What a ship has done this match. */
export interface ShipRecord {
  shots: number;
  hits: number;
  damage: number;
  /** Ships that died with this one's shot the last to hit them. */
  kills: number;
}

/** The last action of the ship being inspected: a pilot's logits, or a script's row alone. */
export interface WatchedAction {
  /** The tick it was chosen on; -1 before the first. */
  tick: number;
  /** A copy of the net's logits (see LiveMatch.watchedScripted). */
  logits: Float32Array;
  row: Int8Array;
}

export interface LiveMatchOptions {
  sim: SimModule;
  layout: SimLayout;
  catalogue: Catalogue;
  /** Each strike craft gets one of these at random (Bundle.pilots). */
  pilots: LivePilot[];
  /** The champion's trained match config (manifest.match): deathmatch clock and reaction. */
  settings: MatchSettings;
  fleets: Fleets;
  seed: number;
  mission?: MissionName;
}

function emptyShip(i: number): ShipState {
  return {
    id: i, x: 0, y: 0, vx: 0, vy: 0, heading: 0, omega: 0, hp: 0, shield: 0, alive: false, present: false, team: 0, hull: 0,
    throttles: new Float32Array(MAX_THRUSTERS),
    turretAngles: new Float32Array(MAX_TURRETS),
    power: new Float32Array(3),
    role: "strike", docked: false, jump: 0, chargeUntil: 0, hasWaypoint: false, waypointX: 0, waypointY: 0, squad: -1,
  };
}

export class LiveMatch {
  readonly seed: number;
  readonly fleets: Fleets;
  readonly settings: MatchSettings;
  readonly mission: MissionName;
  /** From the sim's per-mission rule, not the manifest, so the page sizes arenas as training does. */
  readonly arenaRadius: number;
  readonly timeLimitTicks: number;
  readonly nShips: number;
  readonly ships: ShipState[] = [];
  readonly maxHp: number[];
  /** Hull name per ship (catalogue order resolved). */
  readonly hullNames: string[];
  /** "freighter 2", "carrier": the hull plus its number among its side's hulls of that kind. */
  readonly labels: string[];
  /** Live projectiles after the last step; the array and its objects are reused. */
  projectiles: ProjectileState[] = [];
  /** Events of the last step; the array and its objects are reused. */
  events: SimEvent[] = [];
  /** Both teams' carrier and hangar after the last step. */
  readonly teams: [TeamState, TeamState];
  /** Every squad (team 0's then team 1's) after the last step. */
  squads: SquadState[] = [];
  /** The convoy after the last step; null outside a convoy escort. */
  convoy: ConvoyState | null = null;
  readonly timing: Timing = { sim: 0, nn: 0, ticks: 0 };
  /** The last tick's exact split, ms. */
  last = { sim: 0, nn: 0 };
  readonly records: ShipRecord[];
  /** The inspected ship's slot, whose outputs step() keeps in `watched`, or -1. */
  watching = -1;
  readonly watched: WatchedAction;
  /** The watched row came from the sim's script, so its logits mean nothing. */
  watchedScripted = false;

  private readonly sim: SimModule;
  private readonly layout: SimLayout;
  private readonly shipPilots: LivePilot[];
  private match: WasmMatch | null;
  private readonly headValid: Uint8Array[];
  private readonly rngs: Rng[];
  private readonly row: Int8Array;
  /** Who last hit each ship, for kill credit; -1 if nobody has. */
  private readonly lastHitBy: number[];
  private readonly projectilePool: ProjectileState[] = [];
  private readonly eventPool: SimEvent[] = [];
  private readonly squadPool: SquadState[] = [];
  /** The v4 views (ship ext, squads, teams, convoy) exist in this wasm. */
  private readonly v4: boolean;

  constructor(o: LiveMatchOptions) {
    this.sim = o.sim;
    this.layout = o.layout;
    this.seed = o.seed;
    this.fleets = o.fleets;
    this.settings = o.settings;
    this.mission = o.mission ?? "deathmatch";
    this.nShips = o.fleets[0].length + o.fleets[1].length;
    this.shipPilots = assignPilots(o.pilots, this.nShips, o.seed);
    this.v4 = typeof o.sim.arenaRadiusForMission === "function";
    const deathmatch = this.mission === "deathmatch";
    if (!this.v4 && !deathmatch) throw new Error(`mission ${this.mission} needs a SIM_VERSION 4 bundle`);
    this.arenaRadius = this.v4 ? o.sim.arenaRadiusForMission(this.mission, this.nShips) : o.sim.arenaRadiusFor(this.nShips);
    // Deathmatch keeps the champion's trained clock; missions take the sim's default.
    this.timeLimitTicks = deathmatch ? o.settings.time_limit_ticks : o.sim.missionTimeLimitTicks(this.mission);
    this.match = new o.sim.WasmMatch(
      o.catalogue.hulls,
      o.catalogue.weapons,
      JSON.stringify({
        seed: o.seed,
        arena_radius: this.arenaRadius,
        time_limit_ticks: this.timeLimitTicks,
        reaction_ticks: o.settings.reaction_ticks,
        fleets: o.fleets,
        ...(deathmatch ? {} : { mission: this.mission }),
      }),
    );
    this.row = new Int8Array(o.layout.actionWidth);
    this.lastHitBy = Array.from({ length: this.nShips }, () => -1);
    this.records = Array.from({ length: this.nShips }, () => ({ shots: 0, hits: 0, damage: 0, kills: 0 }));
    this.watched = { tick: -1, logits: new Float32Array(o.pilots[0]!.policy.manifest.n_logits), row: new Int8Array(o.layout.actionWidth) };
    const m = this.match;
    this.headValid = Array.from({ length: this.nShips }, (_, s) => m.head_valid(s));
    // Distinct, reproducible sampling streams per ship.
    this.rngs = Array.from({ length: this.nShips }, (_, s) => mulberry32(Math.imul(o.seed | 0, 0x9e3779b1) + s * 40503 + 1));
    this.teams = [this.emptyTeam(), this.emptyTeam()];
    this.readShips();
    this.readMission();
    this.maxHp = this.ships.map((s) => s.hp);
    this.hullNames = this.ships.map((s) => o.catalogue.hulls[s.hull]?.[0] ?? "unknown");
    this.labels = this.hullNames.map((name, i) => {
      const team = this.ships[i]!.team;
      const same = this.hullNames.map((_, j) => j).filter((j) => this.hullNames[j] === name && this.ships[j]!.team === team);
      return same.length > 1 ? `${name} ${same.indexOf(i) + 1}` : name;
    });
  }

  /** The pilot flying a ship; "" for a capital ship, which the sim's script flies. */
  pilotId(s: number): string {
    return this.ships[s]!.role === "strike" ? this.shipPilots[s]!.id : "";
  }

  /** The pilot flying a strike craft; a capital ship's slot still holds an unused draw. */
  pilot(s: number): LivePilot {
    return this.shipPilots[s]!;
  }

  /** Which thruster and turret heads this ship's hull actually has (1 meaningful, 0 masked). */
  validHeads(s: number): Uint8Array {
    return this.headValid[s]!;
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

  /** The sim's end reason name ("not_over" while running). */
  get simReason(): SimEndReason {
    if (!this.v4) return this.over ? (this.reasonFromShips() === "time" ? "time_limit" : "eliminated") : "not_over";
    return END_REASONS[this.wasm.end_reason()] ?? "not_over";
  }

  get reason(): EndReason {
    if (!this.v4) return this.reasonFromShips();
    const r = REASONS[this.simReason] ?? "time";
    return r === "eliminated" && this.winner === -1 ? "mutual" : r;
  }

  private reasonFromShips(): EndReason {
    const alive = [0, 0];
    for (const s of this.ships) if (this.inMatch(s)) alive[s.team] = (alive[s.team] ?? 0) + 1;
    if (alive[0] === 0 && alive[1] === 0) return "mutual";
    if (alive[0] === 0 || alive[1] === 0) return "eliminated";
    return "time";
  }

  /** Alive and not jumped out (docked reserves and pending arrivals count). */
  inMatch(s: ShipState): boolean {
    return s.alive && s.jump !== JUMP_DEPARTED;
  }

  /** On the field now: present, alive, not docked or departed. */
  active(s: ShipState): boolean {
    return s.alive && s.present && !s.docked && s.jump !== JUMP_DEPARTED;
  }

  /** Each team's time-limit value (hull plus half of shields, ships still in the match). */
  teamValues(): [number, number] {
    const v: [number, number] = [0, 0];
    for (const s of this.ships) if (this.inMatch(s)) v[s.team === 0 ? 0 : 1] += Math.max(0, s.hp) + VALUE_SHIELD_WEIGHT * s.shield;
    return v;
  }

  /** Choose every ship's action (policy or script), advance one tick, refresh the views. */
  step(): void {
    const m = this.wasm;
    let nn = 0;
    let script = 0;
    for (let s = 0; s < this.nShips; s++) {
      const ship = this.ships[s]!;
      // An absent or dead ship's row is discarded by the sim (SIM_SPEC §7.1), so skip
      // its forward pass.
      if (!ship.alive || !ship.present) continue;
      if (ship.role !== "strike") {
        const t0 = performance.now();
        const row = m.scripted_action(s);
        m.set_action(s, row);
        script += performance.now() - t0;
        if (s === this.watching) this.watch(row, null);
        continue;
      }
      const t0 = performance.now();
      // An older pilot reads the prefix of the obs it was trained on.
      const pilot = this.shipPilots[s]!;
      const logits = pilot.policy.forward(m.obs(s).subarray(0, pilot.obsDim));
      pilot.policy.actFromLogits(logits, this.headValid[s]!, this.rngs[s]!, this.row);
      nn += performance.now() - t0;
      m.set_action(s, this.row);
      if (s === this.watching) this.watch(this.row, logits);
    }
    const t1 = performance.now();
    m.step();
    this.readShips();
    this.readProjectiles();
    this.readEvents();
    this.readMission();
    const simMs = performance.now() - t1 + script;
    this.last = { sim: simMs, nn };
    const k = this.timing.ticks === 0 ? 1 : 1 / 30;
    this.timing.sim += (simMs - this.timing.sim) * k;
    this.timing.nn += (nn - this.timing.nn) * k;
    this.timing.ticks += 1;
  }

  /** Keep the inspected ship's action; the net's logits array is overwritten by the next ship. */
  private watch(row: Int8Array, logits: Float32Array | null): void {
    const w = this.watched;
    w.tick = this.wasm.tick();
    w.row.set(row);
    if (logits) w.logits.set(logits);
    else w.logits.fill(0);
    this.watchedScripted = logits === null;
  }

  /** Release the wasm match. The object is unusable afterwards. */
  free(): void {
    this.match?.free();
    this.match = null;
  }

  private record(e: SimEvent): void {
    if (e.kind === "fire" || e.kind === "beam") {
      const r = this.records[e.a];
      if (r) r.shots += 1;
    } else if (e.kind === "hit" || e.kind === "shieldHit") {
      const r = this.records[e.b];
      if (!r) return;
      this.lastHitBy[e.a] = e.b;
      r.hits += 1;
      // A shield hit's last field says whether it dropped the shield, not how much it did.
      if (e.kind === "hit") r.damage += e.extra;
    } else if (e.kind === "death") {
      const by = this.records[this.lastHitBy[e.a] ?? -1];
      if (by) by.kills += 1;
    }
  }

  private view(ptr: number, len: number): Float32Array {
    return new Float32Array(this.sim.wasm_memory().buffer, ptr, len);
  }

  private emptyTeam(): TeamState {
    return { carrier: -1, hp: 0, maxHp: 0, shield: 0, maxShield: 0, hangar: 0, bays: 0, baysReady: 0 };
  }

  private readShips(): void {
    const L = this.layout;
    const v = this.view(this.wasm.ships_ptr(), this.wasm.ships_len());
    const n = v.length / L.shipStride;
    for (let i = 0; i < n; i++) {
      const o = i * L.shipStride;
      let s = this.ships[i];
      if (!s) {
        s = emptyShip(i);
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
    if (!this.v4) return;
    const stride = this.sim.SHIP_EXT_STRIDE();
    const x = this.view(this.wasm.ship_ext_ptr(), this.wasm.ship_ext_len());
    for (let i = 0; i < n && (i + 1) * stride <= x.length; i++) {
      const o = i * stride;
      const s = this.ships[i]!;
      s.role = shipRole(x[o]!);
      s.docked = x[o + 1]! > 0.5;
      s.jump = x[o + 3]!;
      s.chargeUntil = x[o + 4]!;
      s.hasWaypoint = x[o + 5]! > 0.5;
      s.waypointX = x[o + 6]!;
      s.waypointY = x[o + 7]!;
      s.squad = x[o + 8]!;
    }
  }

  private readMission(): void {
    if (!this.v4) return;
    const m = this.wasm;
    for (const t of [0, 1] as const) {
      const v = m.team_state(t);
      Object.assign(this.teams[t], {
        carrier: v[0]!, hp: v[1]!, maxHp: v[2]!, shield: v[3]!, maxShield: v[4]!, hangar: v[5]!, bays: v[6]!, baysReady: v[7]!,
      });
    }
    const q = m.squads();
    const stride = this.sim.SQUAD_STRIDE();
    const n = Math.floor(q.length / stride);
    const pool = this.squadPool;
    while (pool.length < n) pool.push({ team: 0, index: 0, members: 0, mask: 0, order: "none", target: -1, x: 0, y: 0, radius: 0 });
    for (let i = 0; i < n; i++) {
      const o = i * stride;
      const sq = pool[i]!;
      sq.team = q[o]!;
      sq.index = q[o + 1]!;
      sq.members = q[o + 2]!;
      sq.mask = q[o + 3]!;
      sq.order = ORDER_KINDS[q[o + 4]!] ?? "none";
      sq.target = q[o + 5]!;
      sq.x = q[o + 6]!;
      sq.y = q[o + 7]!;
      sq.radius = q[o + 8]!;
    }
    this.squads = pool.slice(0, n);
    const c = m.convoy();
    if (c.length === 0) {
      this.convoy = null;
      return;
    }
    const cv = this.convoy ?? ({} as ConvoyState);
    Object.assign(cv, {
      total: c[0]!, enRoute: c[1]!, charging: c[2]!, escaped: c[3]!, destroyed: c[4]!, toDestroy: c[5]!, toEscape: c[6]!, progress: c[7]!,
      startX: c[8]!, startY: c[9]!, jumpX: c[10]!, jumpY: c[11]!, jumpRadius: c[12]!, chargeTicks: c[13]!,
    });
    this.convoy = cv;
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
      this.record(e);
    }
    this.events = pool.slice(0, n);
  }
}
