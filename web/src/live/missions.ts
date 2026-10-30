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

import type { Rng } from "./policy.js";
import { chooseRoster, draftSide, draftableHulls, type Roster, type RosterMode, type RosterRules } from "./roster.ts";
import { ROLE_CARRIER, ROLE_TRANSPORT, type ConvoyState, type HullInfo, type SimModule } from "./sim.ts";
import { TEAM_WORDS, teamSpan } from "./teams.ts";

/** The sim's mission kind names (SIM_SPEC §10.3), in rotation order. */
export const MISSIONS = ["deathmatch", "carrier_battle", "convoy_escort"] as const;
export type MissionName = (typeof MISSIONS)[number];

export const MISSION_TITLES: Record<MissionName, string> = {
  deathmatch: "Team deathmatch",
  carrier_battle: "Carrier battle",
  convoy_escort: "Convoy escort",
};

/** Short labels for the status line. */
export const MISSION_TAGS: Record<MissionName, string> = {
  deathmatch: "DEATHMATCH",
  carrier_battle: "CARRIER BATTLE",
  convoy_escort: "CONVOY",
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
 * wasm without the call (before WP-S2) gives none, and the page drafts its own.
 */
export function defaultRosters(sim: Pick<SimModule, "missionRostersJson">): DefaultRosters {
  const out: DefaultRosters = {};
  if (typeof sim.missionRostersJson !== "function") return out;
  for (const mission of MISSIONS) {
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
 * champion is not certified for (an older champion's replay) is swapped for one it is.
 */
function fromSim(list: MissionRosterSpec[], rules: RosterRules, info: Record<string, HullInfo>, rng: Rng): Roster {
  const r = rng() < DEFAULT_ROSTER_SHARE || list.length === 1 ? list[0]! : list[1 + Math.floor(rng() * (list.length - 1))]!;
  const flyable = draftableHulls(rules, info);
  const swap = (hull: string): string => {
    const role = info[hull]?.role;
    if (!info[hull]) throw new Error(`the sim's roster ${r.name} names hull ${hull}, which is not in the catalogue`);
    return role === ROLE_CARRIER || role === ROLE_TRANSPORT || flyable.includes(hull) ? hull : flyable[0]!;
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

/** The first catalogue hull with YAML role `role`, if any (catalogue order: by name). */
export function hullWithRole(info: Record<string, HullInfo>, role: string): string | null {
  return Object.keys(info).find((name) => info[name]!.role === role) ?? null;
}

/**
 * The missions this bundle can stage: every mission needs a v4 sim; the carrier battle
 * a carrier-role hull and the convoy a transport-role hull in the catalogue, and both
 * the renderer's model for it (`drawable`).
 */
export function availableMissions(simVersion: number, info: Record<string, HullInfo>, drawable: (hull: string) => boolean): MissionName[] {
  const out: MissionName[] = ["deathmatch"];
  if (simVersion < 4) return out;
  const carrier = hullWithRole(info, ROLE_CARRIER);
  const freighter = hullWithRole(info, ROLE_TRANSPORT);
  if (carrier && drawable(carrier)) out.push("carrier_battle");
  if (freighter && drawable(freighter)) out.push("convoy_escort");
  return out;
}

/** The pinned mission if this bundle can stage it, else the rotation's pick for `seed`. */
export function missionFor(seed: number, available: MissionName[], pinned: MissionName | null): MissionName {
  if (pinned && available.includes(pinned)) return pinned;
  return available[Math.abs(Math.trunc(seed)) % available.length]!;
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
  const list = rosters[mission];
  if (list && list.length > 0) return fromSim(list, rules, info, rng);
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
 * numbers are the sim's thresholds, not ours.
 */
export function missionBrief(mission: MissionName, convoy: ConvoyState | null): Brief {
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
