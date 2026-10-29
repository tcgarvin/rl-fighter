// The sim-wasm module's surface (crates/sim-wasm, SIM_SPEC §10.2) as the live page
// uses it, and the record layouts read out of wasm memory. The module itself comes
// from the champion bundle at run time, so it is typed here rather than imported.

export const SIM_HZ = 30;
export const SIM_DT = 1 / SIM_HZ;
export const TICK_BUDGET_MS = 1000 / SIM_HZ;

export interface WasmMatch {
  free(): void;
  step(): void;
  set_action(ship: number, row: Int8Array): void;
  head_valid(ship: number): Uint8Array;
  obs(ship: number): Float32Array;
  ships_ptr(): number;
  ships_len(): number;
  projectiles_ptr(): number;
  projectiles_len(): number;
  events_ptr(): number;
  events_len(): number;
  tick(): number;
  phase(): number;
  winner(): number;
}

export interface SimModule {
  default(init: { module_or_path: string | URL }): Promise<unknown>;
  initSync(init: { module: BufferSource }): unknown;
  WasmMatch: new (hulls: Array<[string, string]>, weaponsYaml: string, configJson: string) => WasmMatch;
  sim_version(): number;
  /** Arena radius for a match of this many ships: the one rule training uses (sim::setup). */
  arenaRadiusFor(nShips: number): number;
  wasm_memory(): WebAssembly.Memory;
  OBS_DIM(): number;
  ACTION_WIDTH(): number;
  SHIP_STRIDE(): number;
  SHIP_THROTTLE_OFFSET(): number;
  SHIP_TURRET_OFFSET(): number;
  SHIP_POWER_OFFSET(): number;
  PROJECTILE_STRIDE(): number;
  EVENT_STRIDE(): number;
}

export interface SimLayout {
  simVersion: number;
  obsDim: number;
  actionWidth: number;
  shipStride: number;
  throttleOffset: number;
  turretOffset: number;
  powerOffset: number;
  projectileStride: number;
  eventStride: number;
}

/** Read the module's static constants once. */
export function simLayout(sim: SimModule): SimLayout {
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

/** `{ hulls: [[name, yaml]], weapons: yaml, info }`, from tools/build_bundle.py. */
export interface Catalogue {
  hulls: Array<[string, string]>;
  weapons: string;
  info: Record<string, HullInfo>;
}

export interface HullInfo {
  role: string;
  cost: number;
  hp: number;
  shield: number;
}

export interface MatchSettings {
  arena_radius: number;
  time_limit_ticks: number;
  reaction_ticks: number;
}

export const PROJECTILE_KINDS = ["bullet", "beam", "flak", "torpedo"] as const;
export type ProjectileKind = (typeof PROJECTILE_KINDS)[number];
export const EVENT_KINDS = ["fire", "beam", "hit", "shieldHit", "burst", "death", "arrival", "collision"] as const;
export type EventKind = (typeof EVENT_KINDS)[number] | "unknown";

export const MAX_THRUSTERS = 8;
export const MAX_TURRETS = 6;

export interface ShipState {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  heading: number;
  omega: number;
  hp: number;
  shield: number;
  alive: boolean;
  present: boolean;
  team: number;
  /** Index into the catalogue's (sorted) hull list. */
  hull: number;
  throttles: Float32Array;
  turretAngles: Float32Array;
  /** Shields, engines, weapons shares. */
  power: Float32Array;
}

export interface ProjectileState {
  slot: number;
  kind: ProjectileKind;
  team: number;
  owner: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/** SIM_SPEC §9: `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]`. */
export interface SimEvent {
  kind: EventKind;
  a: number;
  b: number;
  x: number;
  y: number;
  f5: number;
  f6: number;
  extra: number;
}
