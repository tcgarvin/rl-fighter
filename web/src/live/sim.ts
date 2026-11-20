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
  /** v10: the hardpoints view (SimModule.HARDPOINT_STRIDE floats per ship, ship order). */
  hardpoints_ptr?(): number;
  hardpoints_len?(): number;
  /** v11: the dock view (SimModule.DOCK_STRIDE floats per ship, ship order). */
  dock_ptr?(): number;
  dock_len?(): number;
  /** MISSION_KINDS index (v9: 3, the station assault). */
  mission_kind(): number;
  /** v9: the mission kind the nets read: a station assault's is 1 or 2 (its spec's `"as"`). */
  obs_mission_kind?(): number;
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
  /** v5: the last step's order reward per ship (SIM_SPEC §8). */
  order_rewards?(): Float32Array;
  // The learned commander (docs/COMMANDER.md "Bindings"; config commanders "learned").
  /** Whether the next step() is `team`'s slow tick, when a learned team decides. */
  commander_due(team: number): boolean;
  /** `team`'s inputs and masks, COMMANDER_FEATURES_LEN floats in commanderIoJson()'s flat layout. */
  commander_features(team: number): Float32Array;
  /** Decode and queue `team`'s decision (COMMANDER_ACTION_DIM ints); returns how many commands it made. */
  submit_commander_action(team: number, action: Int32Array): number;
  /** [team 0, team 1] values now. */
  team_values(): Float32Array;
}

export interface SimModule {
  default(init: { module_or_path: string | URL }): Promise<unknown>;
  initSync(init: { module: BufferSource }): unknown;
  WasmMatch: new (hulls: Array<[string, string]>, weaponsYaml: string, configJson: string) => WasmMatch;
  sim_version(): number;
  /** v4: sim versions whose pilots fly in this build. */
  pilot_compat_versions(): Uint32Array;
  pilot_compatible(version: number): boolean;
  /** v5: JSON {version: obs width} of the obs prefix a pilot of that sim version reads. */
  pilotObsDimsJson?(): string;
  arenaRadiusForMission(mission: string, nShips: number): number;
  /** WP-S2: JSON [{name, mission, fleets}] of the mission's default rosters (first = default; deathmatch "[]"). */
  missionRostersJson?(mission: string): string;
  missionTimeLimitTicks(mission: string): number;
  MAX_SHIPS(): number;
  COMMAND_TICKS(): number;
  /** The learned commander's interface (absent in a wasm before it). */
  COMMANDER_IO_VERSION?(): number;
  COMMANDER_FEATURES_LEN?(): number;
  COMMANDER_ACTION_DIM?(): number;
  LEARNED_COMMAND_TICKS?(): number;
  /** JSON {version, ..., flat_dim, flat_layout: [[name, offset, width], ...]}. */
  commanderIoJson?(): string;
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
  /** v10: `[n_turrets, n_bays, turret_angle[12], turret_state[12], bay_state[4]]` per ship. */
  HARDPOINT_STRIDE?(): number;
  HARDPOINT_TURRET_ANGLE_OFFSET?(): number;
  HARDPOINT_TURRET_STATE_OFFSET?(): number;
  HARDPOINT_BAY_STATE_OFFSET?(): number;
  /** v11: `[phase, bay, point.x, point.y, since, docked_at, ready_at, hp_frac]` per ship. */
  DOCK_STRIDE?(): number;
}

/** Where the v10 hardpoints view keeps each block of a ship's record. */
export interface HardpointLayout {
  stride: number;
  turretAngleOffset: number;
  turretStateOffset: number;
  bayStateOffset: number;
}

export interface SimLayout {
  simVersion: number;
  /** Sim versions whose pilots this build flies (v4; just simVersion before). */
  pilotCompat: number[];
  /** v5: per pilot-compatible sim version, the obs prefix width its pilots read
   * (sim::PILOT_OBS_DIMS: 385 for v3/v4, 403 for v5, 583 for v6). Older wasm: OBS_DIM for all. */
  pilotObsDims: Record<number, number>;
  obsDim: number;
  actionWidth: number;
  shipStride: number;
  throttleOffset: number;
  turretOffset: number;
  powerOffset: number;
  /** v10 appends the weapon id to each projectile (9 floats); 8 before. */
  projectileStride: number;
  eventStride: number;
  /** v10: the hardpoints view's layout; null in a wasm before it. */
  hardpoints: HardpointLayout | null;
  /** v11: floats per ship in the dock view; 0 in a wasm before it. */
  dockStride: number;
}

/** Read the module's static constants once. */
export function simLayout(sim: SimModule): SimLayout {
  const pilotCompat = typeof sim.pilot_compat_versions === "function" ? Array.from(sim.pilot_compat_versions()) : [sim.sim_version()];
  const obsDim = sim.OBS_DIM();
  const pilotObsDims: Record<number, number> =
    typeof sim.pilotObsDimsJson === "function"
      ? (JSON.parse(sim.pilotObsDimsJson()) as Record<number, number>)
      : Object.fromEntries(pilotCompat.map((v) => [v, obsDim]));
  return {
    simVersion: sim.sim_version(),
    pilotCompat,
    pilotObsDims,
    obsDim,
    actionWidth: sim.ACTION_WIDTH(),
    shipStride: sim.SHIP_STRIDE(),
    throttleOffset: sim.SHIP_THROTTLE_OFFSET(),
    turretOffset: sim.SHIP_TURRET_OFFSET(),
    powerOffset: sim.SHIP_POWER_OFFSET(),
    projectileStride: sim.PROJECTILE_STRIDE(),
    eventStride: sim.EVENT_STRIDE(),
    hardpoints: hardpointLayout(sim),
    dockStride: dockStride(sim),
  };
}

/** The fields this page reads from a dock record (SIM_SPEC §5.11; crates/sim-wasm bridge.rs). */
const DOCK_FIELDS = 8;

function dockStride(sim: SimModule): number {
  if (!sim.DOCK_STRIDE) return 0;
  const stride = sim.DOCK_STRIDE();
  if (stride < DOCK_FIELDS) throw new Error(`dock view stride ${stride} is shorter than the ${DOCK_FIELDS} fields this page reads`);
  return stride;
}

function hardpointLayout(sim: SimModule): HardpointLayout | null {
  if (!sim.HARDPOINT_STRIDE || !sim.HARDPOINT_TURRET_ANGLE_OFFSET || !sim.HARDPOINT_TURRET_STATE_OFFSET || !sim.HARDPOINT_BAY_STATE_OFFSET) return null;
  const layout = {
    stride: sim.HARDPOINT_STRIDE(),
    turretAngleOffset: sim.HARDPOINT_TURRET_ANGLE_OFFSET(),
    turretStateOffset: sim.HARDPOINT_TURRET_STATE_OFFSET(),
    bayStateOffset: sim.HARDPOINT_BAY_STATE_OFFSET(),
  };
  // The page keeps MAX_TURRETS angles and states and MAX_BAYS bay states a ship.
  if (layout.turretStateOffset - layout.turretAngleOffset !== MAX_TURRETS || layout.bayStateOffset - layout.turretStateOffset !== MAX_TURRETS || layout.stride - layout.bayStateOffset !== MAX_BAYS) {
    throw new Error(`hardpoints view ${JSON.stringify(layout)} does not hold ${MAX_TURRETS} turrets and ${MAX_BAYS} bays`);
  }
  return layout;
}

/**
 * The obs width a pilot trained under sim `version` reads: the first that many floats of
 * `WasmMatch.obs` (SIM_VERSION 5 appends the order block after the 385 a v3/v4 pilot
 * knows). Throws for a version this wasm does not fly.
 */
export function pilotObsDim(layout: SimLayout, version: number): number {
  const dim = layout.pilotObsDims[version];
  if (dim === undefined || !Number.isInteger(dim) || dim < 1 || dim > layout.obsDim) {
    throw new Error(`no obs width for a sim_version ${version} pilot in this wasm (it flies ${layout.pilotCompat.join(", ")})`);
  }
  return dim;
}

/** The hulls of SIM_VERSION 4 to 9 in their id order, frozen (sim::data::LEGACY_HULL_ORDER; v10 adds
 * the citadel and the dreadnought after them, by name). */
const LEGACY_HULL_ORDER = ["carrier", "fighter", "freighter", "gunship", "strafer", "bomber", "station"];

/**
 * `hulls` in the sim's id order (sim::data::hull_order): the legacy hulls first, in
 * their order, then every other hull by name. The sim numbers a catalogue this way
 * whatever order it is passed in, so a ship's `hull` indexes this list; before v9 (no
 * other hulls) it is plain name order. assembleBundle checks it against the wasm.
 */
export function simHullOrder<T extends [string, string]>(hulls: readonly T[]): T[] {
  const rank = (name: string): number => {
    const i = LEGACY_HULL_ORDER.indexOf(name);
    return i < 0 ? LEGACY_HULL_ORDER.length : i;
  };
  return [...hulls].sort((a, b) => rank(a[0]) - rank(b[0]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}

/** `{ hulls: [[name, yaml]], weapons: yaml, info }`, from tools/build_bundle.py (hulls by name). */
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
  /** v9: never moves (the station); absent in older bundles. */
  static?: boolean;
  shield_radius: number;
  collision: Array<{ pos: [number, number]; r: number }>;
  thrusters: Array<{ id: string; pos: [number, number]; dir: [number, number]; max_force: number }>;
  turrets: Array<{ id: string; pos: [number, number]; rest_deg: number; arc_deg: number; slew_deg_s: number; weapon: string }>;
  bays: Array<{ id: string; pos: [number, number]; dir: [number, number] }>;
}

/** Hull roles (YAML `role`) of the capital ships, which scripts fly (SIM_SPEC §11). */
export const ROLE_CARRIER = "carrier";
export const ROLE_TRANSPORT = "transport";
/** v10: a gun capital ship with no bays (the dreadnought). */
export const ROLE_LINE = "line";
export const CAPITAL_ROLES: readonly string[] = [ROLE_CARRIER, ROLE_TRANSPORT, ROLE_LINE];

/** Whether a catalogue hull is a capital ship (a script flies it, never a pilot). */
export function isCapitalHull(info: HullInfo | undefined): boolean {
  return info !== undefined && (CAPITAL_ROLES.includes(info.role) || Boolean(info.geometry?.static));
}

/** The ship-ext view's role code (SIM_SPEC §10.2; v10 adds 3, line). */
export type ShipRole = "strike" | "carrier" | "transport" | "line";
const SHIP_ROLES: ShipRole[] = ["strike", "carrier", "transport", "line"];
/** A code this page does not know is a capital ship all the same: only the sim's script can fly it. */
export function shipRole(code: number): ShipRole {
  if (code === 0) return "strike";
  return SHIP_ROLES[code] ?? "line";
}

/** Jump drive state (SIM_SPEC §5.10): 0 idle, 1 charging, 2 departed. */
export const JUMP_IDLE = 0;
export const JUMP_CHARGING = 1;
export const JUMP_DEPARTED = 2;

/** A ship's dock phase (the dock view, rlf_sim.DOCK_PHASES): none; inbound under a dock
 * order; back in its carrier's hangar inside its turnaround; ready to relaunch. */
export const DOCK_NONE = 0;
export const DOCK_INBOUND = 1;
export const DOCK_REPAIRING = 2;
export const DOCK_READY = 3;
/** DockAborted's reasons. */
export const DOCK_ABORT_REASONS = ["carrier lost", "no bay left"] as const;

/** Squad order kinds (SIM_SPEC §5.9 and the `Order` event; v6: defend and go-to). */
export const ORDER_KINDS = ["none", "attack", "defend", "goto"] as const;
export type OrderKind = (typeof ORDER_KINDS)[number];

/** `MissionKind` codes (SIM_SPEC §10.3; v9 adds the station assault). */
export const MISSION_KINDS = ["deathmatch", "carrier_battle", "convoy_escort", "station_assault"] as const;

/** `EndReason` codes (SIM_SPEC §5.8; v9: 6 and 7, the station assault's). */
export const END_REASONS = [
  "not_over",
  "eliminated",
  "time_limit",
  "carrier_destroyed",
  "convoy_through",
  "convoy_destroyed",
  "station_destroyed",
  "assault_repelled",
] as const;
export type SimEndReason = (typeof END_REASONS)[number];

export interface MatchSettings {
  arena_radius: number;
  time_limit_ticks: number;
  reaction_ticks: number;
}

export const PROJECTILE_KINDS = ["bullet", "beam", "flak", "torpedo"] as const;
export type ProjectileKind = (typeof PROJECTILE_KINDS)[number];
export const EVENT_KINDS = [
  "fire", "beam", "hit", "shieldHit", "burst", "death", "arrival", "collision", "launch", "order", "jumpCharge", "jumpOut", "matchEnd",
  // v10: `[kind, ship, turret or bay, x, y, 0, 0, shooter]`.
  "turretDestroyed", "bayDestroyed",
  // v11 (dock and repair, SIM_SPEC §5.11): dockOrdered `[k, ship, carrier, x, y, 0, 0, bay]`
  // (the dock point), docked `[k, ship, carrier, x, y, hp_frac, 0, bay]` (where it was),
  // repaired `[k, ship, carrier, 0, 0, 0, 0, 0]`, relaunched `[k, ship, carrier, 0, 0,
  // hp_frac, 0, bay]` (after its launch), dockAborted `[k, ship, carrier, 0, 0, 0, 0, reason]`.
  "dockOrdered", "docked", "repaired", "relaunched", "dockAborted",
] as const;
export type EventKind = (typeof EVENT_KINDS)[number] | "unknown";

/** Weapon ids are assets/weapons.yaml file order (SIM_SPEC §4.2): `Fire` and (v10) each projectile carry one. */
export const WEAPON_NAMES = ["gauss", "laser", "flak", "torpedo", "rail", "lance"] as const;

export const MAX_THRUSTERS = 8;
/** Turret angles in the ships view and turret heads in an action row. */
export const ACTION_TURRETS = 6;
/** Turrets a hull may have (v10: the citadel's 12); the hardpoints view has them all. */
export const MAX_TURRETS = 12;
/** Bays a hull may have. */
export const MAX_BAYS = 4;

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
  /** Index into the catalogue's hull list, in the sim's id order (simHullOrder). */
  hull: number;
  throttles: Float32Array;
  /** Every turret's angle, body frame (MAX_TURRETS; past the first ACTION_TURRETS only from v10's hardpoints view). */
  turretAngles: Float32Array;
  // v10 (the hardpoints view): the hull's turrets and bays, and each one's hp fraction
  // (0 destroyed; 1 for a mount that cannot be). Zero counts before v10.
  nTurrets: number;
  nBays: number;
  turretState: Float32Array;
  bayState: Float32Array;
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
  // v11 (the dock view; DOCK_NONE and zeros before v11 or while the dock rules do not run).
  /** DOCK_NONE, DOCK_INBOUND, DOCK_REPAIRING or DOCK_READY. */
  dockPhase: number;
  /** The dock order's bay, or -1. */
  dockBay: number;
  /** The ordered bay's dock point now (rides on the carrier); 0 without a dock order. */
  dockX: number;
  dockY: number;
  /** The tick the dock order was given; 0 without one. */
  dockSince: number;
  /** The tick a returned ship docked; 0 if it is not back in the hangar. */
  dockedAt: number;
  /** The first tick it may relaunch; 0 for always. */
  readyAt: number;
}

/** One squad of the commander layer (the `squads()` view, SQUAD_STRIDE). */
export interface SquadState {
  team: number;
  index: number;
  members: number;
  /** Bitmask over ship slots. */
  mask: number;
  order: OrderKind;
  /** Attack target or defend ward slot, or -1. */
  target: number;
  /** Go-to point, or the target's position. */
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
  /**
   * The weapon's name (assets/weapons.yaml) when the bridge reports it: v10's rail and
   * lance are kind "bullet" but drawn with looks of their own (render/effects.js).
   */
  weapon?: string;
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
