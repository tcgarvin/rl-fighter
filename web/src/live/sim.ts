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
  /** The scripted controller's row for `ship` now (capital ships fly by script). */
  scripted_action(ship: number): Int8Array;
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
  // v4 (SIM_SPEC §10.2): missions and the commander layer.
  ship_ext_ptr(): number;
  ship_ext_len(): number;
  mission_kind(): number;
  end_reason(): number;
  command_due(): boolean;
  submit_commands(team: number, json: string): void;
  command_results_json(team: number): string;
  commander_obs_json(team: number): string;
  mission_state_json(): string;
  squads(): Float32Array;
  team_state(team: number): Float32Array;
  hangar_hulls(team: number): Uint16Array;
  convoy(): Float32Array;
}

export interface SimModule {
  default(init: { module_or_path: string | URL }): Promise<unknown>;
  initSync(init: { module: BufferSource }): unknown;
  WasmMatch: new (hulls: Array<[string, string]>, weaponsYaml: string, configJson: string) => WasmMatch;
  sim_version(): number;
  /** v4: sim versions whose pilots fly in this build. */
  pilot_compat_versions(): Uint32Array;
  pilot_compatible(version: number): boolean;
  arenaRadiusForMission(mission: string, nShips: number): number;
  /** WP-S2: JSON [{name, mission, fleets}] of the mission's default rosters (first = default; deathmatch "[]"). */
  missionRostersJson?(mission: string): string;
  missionTimeLimitTicks(mission: string): number;
  MAX_SHIPS(): number;
  COMMAND_TICKS(): number;
  MAX_SQUADS(): number;
  SHIP_EXT_STRIDE(): number;
  SQUAD_STRIDE(): number;
  TEAM_STRIDE(): number;
  CONVOY_STRIDE(): number;
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
  /** Sim versions whose pilots this build flies (v4; just simVersion before). */
  pilotCompat: number[];
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
    pilotCompat: typeof sim.pilot_compat_versions === "function" ? Array.from(sim.pilot_compat_versions()) : [sim.sim_version()],
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
  /** The sim's mounts (tools/build_bundle.py; absent in older bundles). */
  geometry?: HullGeometry;
}

/** A hull YAML's drawable parts, body frame (+x forward, +y port), metres. */
export interface HullGeometry {
  speed_cap: number;
  shield_radius: number;
  collision: Array<{ pos: [number, number]; r: number }>;
  thrusters: Array<{ id: string; pos: [number, number]; dir: [number, number]; max_force: number }>;
  turrets: Array<{ id: string; pos: [number, number]; rest_deg: number; arc_deg: number; slew_deg_s: number; weapon: string }>;
  bays: Array<{ id: string; pos: [number, number]; dir: [number, number] }>;
}

/** Hull roles (YAML `role`) of the capital ships, which scripts fly (SIM_SPEC §11). */
export const ROLE_CARRIER = "carrier";
export const ROLE_TRANSPORT = "transport";

/** The ship-ext view's role code (SIM_SPEC §10.2). */
export type ShipRole = "strike" | "carrier" | "transport";
const SHIP_ROLES: ShipRole[] = ["strike", "carrier", "transport"];
export function shipRole(code: number): ShipRole {
  return SHIP_ROLES[code] ?? "strike";
}

/** Jump drive state (SIM_SPEC §5.10): 0 idle, 1 charging, 2 departed. */
export const JUMP_IDLE = 0;
export const JUMP_CHARGING = 1;
export const JUMP_DEPARTED = 2;

/** Squad order kinds (SIM_SPEC §5.9 and the `Order` event). */
export const ORDER_KINDS = ["none", "attack", "guard", "hold"] as const;
export type OrderKind = (typeof ORDER_KINDS)[number];

/** `EndReason` codes (SIM_SPEC §5.8). */
export const END_REASONS = ["not_over", "eliminated", "time_limit", "carrier_destroyed", "convoy_through", "convoy_destroyed"] as const;
export type SimEndReason = (typeof END_REASONS)[number];

export interface MatchSettings {
  arena_radius: number;
  time_limit_ticks: number;
  reaction_ticks: number;
}

export const PROJECTILE_KINDS = ["bullet", "beam", "flak", "torpedo"] as const;
export type ProjectileKind = (typeof PROJECTILE_KINDS)[number];
export const EVENT_KINDS = ["fire", "beam", "hit", "shieldHit", "burst", "death", "arrival", "collision", "launch", "order", "jumpCharge", "jumpOut", "matchEnd"] as const;
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
  // v4 (the ship-ext view, SIM_SPEC §10.2).
  role: ShipRole;
  /** Waiting in a carrier's hangar: alive, never drawn. */
  docked: boolean;
  /** JUMP_IDLE, JUMP_CHARGING or JUMP_DEPARTED. */
  jump: number;
  chargeUntil: number;
  hasWaypoint: boolean;
  waypointX: number;
  waypointY: number;
  /** Squad index in its team, or -1. */
  squad: number;
}

/** One squad of the commander layer (the `squads()` view, SQUAD_STRIDE). */
export interface SquadState {
  team: number;
  index: number;
  members: number;
  /** Bitmask over ship slots. */
  mask: number;
  order: OrderKind;
  /** Attack target or guard ward slot, or -1. */
  target: number;
  /** Hold point, or the target's position. */
  x: number;
  y: number;
  radius: number;
}

/** A team's carrier and hangar (the `team_state()` view, TEAM_STRIDE). */
export interface TeamState {
  carrier: number;
  hp: number;
  maxHp: number;
  shield: number;
  maxShield: number;
  hangar: number;
  bays: number;
  baysReady: number;
}

/** The convoy (the `convoy()` view, CONVOY_STRIDE). */
export interface ConvoyState {
  total: number;
  enRoute: number;
  charging: number;
  escaped: number;
  destroyed: number;
  toDestroy: number;
  toEscape: number;
  /** Mean route progress of the transports not destroyed, 0..1 (escaped = 1). */
  progress: number;
  startX: number;
  startY: number;
  jumpX: number;
  jumpY: number;
  jumpRadius: number;
  chargeTicks: number;
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
