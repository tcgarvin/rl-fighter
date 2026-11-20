// The live page's missions (M3 stage A): which ones a bundle can stage, the rotation,
// the roster for each and the one-line brief at the muster. Pure, so the Node smoke
// test stages exactly what the page does.
//
// Mission *parameters* (arena, clock, convoy route, jump radius, hangar sizes, win
// thresholds) are never set here: the page passes only the mission's name, and the
// sim fills in its defaults (LiveMatch reads them back from the sim's views). Mission
// rosters are the sim's too (`missionRostersJson`, balanced by the mission survey);
// missionRoster() picks one, and only an older wasm without them falls back to the
// drafts in FALLBACK_ROSTERS.
//
// The station assault (SIM_VERSION 9) rotates with the others on a bundle that has it
// (the owner's call, 2026-11-19: all the live pilots, no special selection), though the
// live pilots fly its bombers badly and the attacker wins only 0.36 to 0.39 with them
// (lab/runs/2026-11-19-station-bomber). From SIM_VERSION 10 it is always the citadel's
// (the owner asked for the big station): the sim's "citadel" roster, a carrier and a
// dreadnought against the citadel, whose turrets and bays can be shot off
// (lab/runs/2026-11-19-citadel-dreadnought). A v9 bundle keeps its station.

import type { Rng } from "./policy.js";
import { chooseRoster, draftSide, draftableHulls, type Roster, type RosterMode, type RosterRules } from "./roster.ts";
import { ROLE_CARRIER, ROLE_LINE, ROLE_TRANSPORT, SIM_HZ, isCapitalHull, type ConvoyState, type HullInfo, type SimModule } from "./sim.ts";
import { TEAM_WORDS, teamSpan } from "./teams.ts";

/** The sim's mission kind names (SIM_SPEC §10.3), in kind order (`mission_kind()`). */
export const MISSIONS = ["deathmatch", "carrier_battle", "convoy_escort", "station_assault"] as const;
export type MissionName = (typeof MISSIONS)[number];

/** The missions the page rotates through, in order; the others play only when pinned. */
export const ROTATION: readonly MissionName[] = ["deathmatch", "carrier_battle", "convoy_escort", "station_assault"];

/** The first sim version with the station assault, its station and its bombers. */
export const STATION_SIM_VERSION = 9;
/** The first sim version with the citadel and the dreadnought (a line-role hull). */
export const CITADEL_SIM_VERSION = 10;

/**
 * Strike hulls a mission is built around, flown as the sim's roster names them even
 * where the champion is not certified for them: a station assault without its bombers
 * would be a carrier battle against a turret.
 */
const MISSION_STRIKE_HULLS: Partial<Record<MissionName, readonly string[]>> = {
  station_assault: ["bomber"],
};

export const MISSION_TITLES: Record<MissionName, string> = {
  deathmatch: "Team deathmatch",
  carrier_battle: "Carrier battle",
  convoy_escort: "Convoy escort",
  station_assault: "Station assault",
};

/** Short labels for the status line. */
export const MISSION_TAGS: Record<MissionName, string> = {
  deathmatch: "DEATHMATCH",
  carrier_battle: "CARRIER BATTLE",
  convoy_escort: "CONVOY",
  station_assault: "STATION ASSAULT",
};

const ALIASES: Record<string, MissionName> = {
  deathmatch: "deathmatch",
  tdm: "deathmatch",
  dm: "deathmatch",
  carrier: "carrier_battle",
  carrier_battle: "carrier_battle",
  carriers: "carrier_battle",
  convoy: "convoy_escort",
  convoy_escort: "convoy_escort",
  escort: "convoy_escort",
  station: "station_assault",
  station_assault: "station_assault",
  assault: "station_assault",
};

/** One of the sim's default rosters for a mission (sim::spec::MissionRosterView). */
export interface MissionRosterSpec {
  name: string;
  fleets: [string[], string[]];
}

/** The sim's default rosters per mission; the first of each list is the default. */
export type DefaultRosters = Partial<Record<MissionName, MissionRosterSpec[]>>;

function isFleet(x: unknown): x is string[] {
  return Array.isArray(x) && x.length > 0 && x.every((h) => typeof h === "string");
}

/**
 * Read the sim's default rosters (`missionRostersJson`), checked at the boundary. A
 * wasm without the call (before WP-S2) gives none, and the page drafts its own; one
 * before SIM_VERSION 9 has no station assault to ask about.
 */
export function defaultRosters(sim: Pick<SimModule, "missionRostersJson" | "sim_version">): DefaultRosters {
  const out: DefaultRosters = {};
  if (typeof sim.missionRostersJson !== "function") return out;
  for (const mission of MISSIONS) {
    if (mission === "station_assault" && sim.sim_version() < STATION_SIM_VERSION) continue;
    const raw: unknown = JSON.parse(sim.missionRostersJson(mission));
    if (!Array.isArray(raw)) throw new Error(`missionRostersJson(${mission}) is not an array`);
    out[mission] = raw.map((r: unknown, i) => {
      const rec = r as { name?: unknown; fleets?: unknown };
      const fleets = rec.fleets;
      if (typeof rec.name !== "string" || !Array.isArray(fleets) || fleets.length !== 2 || !isFleet(fleets[0]) || !isFleet(fleets[1])) {
        throw new Error(`missionRostersJson(${mission})[${i}] is not {name, fleets: [[...], [...]]}`);
      }
      return { name: rec.name, fleets: [fleets[0], fleets[1]] };
    });
  }
  return out;
}

// The page plays the sim's default roster this often and the alternatives otherwise.
const DEFAULT_ROSTER_SHARE = 0.5;

/**
 * Pick one of the sim's rosters for a match and keep it flyable: a strike craft the
 * champion is not certified for (an older champion's replay) is swapped for one it is,
 * except the hulls the mission is built around (`kept`).
 */
function fromSim(list: MissionRosterSpec[], rules: RosterRules, info: Record<string, HullInfo>, rng: Rng, kept: readonly string[] = []): Roster {
  const r = rng() < DEFAULT_ROSTER_SHARE || list.length === 1 ? list[0]! : list[1 + Math.floor(rng() * (list.length - 1))]!;
  const flyable = [...draftableHulls(rules, info), ...kept.filter((h) => info[h])];
  // Capital ships (carriers, freighters, the dreadnought, stations) are the sim's scripts' to fly, never swapped.
  const swap = (hull: string): string => {
    if (!info[hull]) throw new Error(`the sim's roster ${r.name} names hull ${hull}, which is not in the catalogue`);
    return isCapitalHull(info[hull]) || flyable.includes(hull) ? hull : flyable[0]!;
  };
  return { fleets: [r.fleets[0].map(swap), r.fleets[1].map(swap)], budget: null, name: r.name };
}

/**
 * Fallback drafts for a wasm without default rosters: strike craft per side as
 * [min, max] (uniform), plus budget headroom for one heavier hull.
 */
export const FALLBACK_ROSTERS = {
  carrier_battle: { wing: [5, 7] as [number, number] },
  convoy_escort: {
    freighters: [3, 5] as [number, number],
    escorts: [3, 4] as [number, number],
    attackers: [5, 7] as [number, number],
  },
  /** Credits beyond the cheapest hull's worth, per side: room for one gunship. */
  headroomShips: 2,
};

/** `?mission=` value → a mission name, or null (rotate). */
export function parseMission(param: string | null): MissionName | null {
  return ALIASES[(param ?? "").toLowerCase()] ?? null;
}

/**
 * The first catalogue hull with YAML role `role`, if any (catalogue order: by name);
 * `fixed` picks among the static hulls (the station) instead of the mobile ones.
 */
export function hullWithRole(info: Record<string, HullInfo>, role: string, fixed = false): string | null {
  return Object.keys(info).find((name) => info[name]!.role === role && Boolean(info[name]!.geometry?.static) === fixed) ?? null;
}

/** A roster with a line-role ship in it (v10's citadel assault brings a dreadnought). */
function hasLineShip(r: MissionRosterSpec, info: Record<string, HullInfo>): boolean {
  return r.fleets.some((f) => f.some((h) => info[h]?.role === ROLE_LINE));
}

/**
 * The station assault's rosters this bundle plays: from SIM_VERSION 10 only the
 * citadel's (the ones with a dreadnought), else the sim's list as it is.
 */
export function stationRosters(list: MissionRosterSpec[], info: Record<string, HullInfo>): MissionRosterSpec[] {
  const big = list.filter((r) => hasLineShip(r, info));
  return big.length > 0 ? big : list;
}

/**
 * The missions this bundle can stage: every mission needs a v4 sim; the carrier battle
 * a carrier-role hull and the convoy a transport-role hull in the catalogue, and the
 * station assault (v9) a static carrier-role hull, a mobile carrier and a bomber, each
 * with the renderer's model for it (`drawable`); from v10 also the dreadnought (a
 * line-role hull) and the citadel.
 */
export function availableMissions(simVersion: number, info: Record<string, HullInfo>, drawable: (hull: string) => boolean): MissionName[] {
  const out: MissionName[] = ["deathmatch"];
  if (simVersion < 4) return out;
  const has = (hull: string | null): boolean => hull !== null && hull in info && drawable(hull);
  const carrier = hullWithRole(info, ROLE_CARRIER);
  if (has(carrier)) out.push("carrier_battle");
  if (has(hullWithRole(info, ROLE_TRANSPORT))) out.push("convoy_escort");
  const strike = MISSION_STRIKE_HULLS.station_assault ?? [];
  const station = simVersion >= STATION_SIM_VERSION && has(carrier) && has(hullWithRole(info, ROLE_CARRIER, true)) && strike.every(has);
  // Every static carrier and line ship the v10 assault may field must be drawable.
  const v10Capitals = Object.keys(info).filter((h) => info[h]!.role === ROLE_LINE || (info[h]!.role === ROLE_CARRIER && info[h]!.geometry?.static));
  if (station && (simVersion < CITADEL_SIM_VERSION || v10Capitals.every(has))) out.push("station_assault");
  return out;
}

/**
 * The pinned mission if this bundle can stage it, else the rotation's pick for `seed`
 * among the available missions that rotate.
 */
export function missionFor(seed: number, available: MissionName[], pinned: MissionName | null): MissionName {
  if (pinned && available.includes(pinned)) return pinned;
  const rotating = available.filter((m) => ROTATION.includes(m));
  return rotating[Math.abs(Math.trunc(seed)) % rotating.length]!;
}

function between([lo, hi]: [number, number], rng: Rng): number {
  return lo + Math.floor(rng() * (hi - lo + 1));
}

/** `n` strike craft drafted from the champion's hulls, mostly the cheapest kinds. */
function wing(n: number, rules: RosterRules, info: Record<string, HullInfo>, rng: Rng): string[] {
  const hulls = draftableHulls(rules, info);
  const cheapest = Math.min(...hulls.map((h) => info[h]!.cost));
  return draftSide(hulls, info, cheapest * (n + FALLBACK_ROSTERS.headroomShips), n, n, rng);
}

/**
 * Both sides' fleets for one match of `mission`. Deathmatch drafts as before (`mode`:
 * ?fleets=). The carrier battle and the convoy take one of the sim's default rosters
 * (`rosters`, from defaultRosters()): a carrier and its wing a side (the sim jumps the
 * first few in and docks the rest); the freighters and their escort against raiders.
 */
export function missionRoster(
  mission: MissionName,
  mode: RosterMode,
  rules: RosterRules,
  info: Record<string, HullInfo>,
  rng: Rng,
  rosters: DefaultRosters = {},
): Roster {
  if (mission === "deathmatch") return chooseRoster(mode, rules, info, rng);
  const sims = rosters[mission];
  const list = sims && mission === "station_assault" ? stationRosters(sims, info) : sims;
  if (list && list.length > 0) return fromSim(list, rules, info, rng, MISSION_STRIKE_HULLS[mission]);
  // Every wasm with the station assault has its rosters.
  if (mission === "station_assault") throw new Error("station assault: the sim gave no roster for it");
  const R = FALLBACK_ROSTERS;
  if (mission === "carrier_battle") {
    const carrier = hullWithRole(info, ROLE_CARRIER);
    if (!carrier) throw new Error("carrier battle: no carrier-role hull in the catalogue");
    const w = wing(between(R.carrier_battle.wing, rng), rules, info, rng);
    return { fleets: [[carrier, ...w], [carrier, ...w]], budget: null };
  }
  const freighter = hullWithRole(info, ROLE_TRANSPORT);
  if (!freighter) throw new Error("convoy escort: no transport-role hull in the catalogue");
  const convoy = Array.from({ length: between(R.convoy_escort.freighters, rng) }, () => freighter);
  const escorts = wing(between(R.convoy_escort.escorts, rng), rules, info, rng);
  const attackers = wing(between(R.convoy_escort.attackers, rng), rules, info, rng);
  return { fleets: [[...convoy, ...escorts], attackers], budget: null };
}

/** The muster's objective-first headline and the brief under it (HTML). */
export interface Brief {
  /** The objective; null for deathmatch, whose headline is the matchup. */
  headline: string | null;
  brief: string;
}

/**
 * The mission brief at the muster. `convoy` is the sim's convoy view at tick 0, so the
 * numbers are the sim's thresholds, not ours; `timeLimitTicks` is the match's clock;
 * `fleets` the match's (a station assault with a dreadnought is v10's citadel assault).
 */
export function missionBrief(mission: MissionName, convoy: ConvoyState | null, timeLimitTicks = 0, fleets?: readonly (readonly string[])[]): Brief {
  if (mission === "station_assault") {
    const clock = timeLimitTicks > 0 ? `${Math.round(timeLimitTicks / SIM_HZ)}&nbsp;s` : "the clock";
    if (fleets?.[1]?.includes("dreadnought")) {
      return {
        headline: "Take the citadel, or&nbsp;hold&nbsp;it.",
        brief:
          `${teamSpan(1, TEAM_WORDS[1])} jumps in with a carrier, a dreadnought and bombers: the citadel falls, ${TEAM_WORDS[1]} wins. ` +
          `${teamSpan(0, TEAM_WORDS[0])} holds it for ${clock}, or wipes out the attack. Turrets and bays can be shot&nbsp;off.`,
      };
    }
    return {
      headline: "Take the station, or&nbsp;hold&nbsp;it.",
      brief:
        `${teamSpan(1, TEAM_WORDS[1])} jumps in with a carrier and bombers: the station falls, ${TEAM_WORDS[1]} wins. ` +
        `${teamSpan(0, TEAM_WORDS[0])} holds it for ${clock}, or wipes out the attack.`,
    };
  }
  if (mission === "carrier_battle") {
    return { headline: "Destroy the enemy carrier.", brief: "Each carrier launches its wing from its bays. Lose yours and you lose the&nbsp;match." };
  }
  if (mission === "convoy_escort" && convoy) {
    return {
      headline: "Get the convoy to the jump point, or&nbsp;stop&nbsp;it.",
      brief:
        `${convoy.total} freighters are under way. ${teamSpan(0, TEAM_WORDS[0])} escorts: ${convoy.toEscape} through wins. ` +
        `${teamSpan(1, TEAM_WORDS[1])} intercepts: ${convoy.toDestroy} kill${convoy.toDestroy === 1 ? "" : "s"} stop${convoy.toDestroy === 1 ? "s" : ""} them.`,
    };
  }
  return { headline: null, brief: "The last side flying wins." };
}
