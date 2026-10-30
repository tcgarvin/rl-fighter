// The live page's missions (M3 stage A): which ones a bundle can stage, the rotation,
// the roster for each and the one-line brief at the muster. Pure, so the Node smoke
// test stages exactly what the page does.
//
// Mission *parameters* (arena, clock, convoy route, jump radius, hangar sizes, win
// thresholds) are never set here: the page passes only the mission's name, and the
// sim fills in its defaults (LiveMatch reads them back from the sim's views). Roster
// choices are all in MISSION_ROSTERS and missionRoster() below; that is the one place
// to swap in WP-S2's per-mission default rosters once the sim exposes them.

import type { Rng } from "./policy.js";
import { chooseRoster, draftSide, draftableHulls, type Roster, type RosterMode, type RosterRules } from "./roster.ts";
import { ROLE_CARRIER, ROLE_TRANSPORT, type ConvoyState, type HullInfo } from "./sim.ts";
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

/**
 * Strike craft per side for each mission, as [min, max] (uniform draw), plus a little
 * budget headroom so a wing can include one heavier hull. Total ships stay well under
 * the sim's 20 (MAX_SHIPS): 2 carriers + 2 × 7, or 5 freighters + 4 + 7.
 * WP-S2: replace these (or missionRoster) with the sim's default rosters.
 */
export const MISSION_ROSTERS = {
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
  return draftSide(hulls, info, cheapest * (n + MISSION_ROSTERS.headroomShips), n, n, rng);
}

/**
 * Both sides' fleets for one match of `mission`. Deathmatch drafts as before (`mode`:
 * ?fleets=). Carrier battle: a carrier and a mirrored wing a side (the sim jumps the
 * first few in and docks the rest). Convoy: team 0 is the freighters and their escort,
 * team 1 the larger strike force that jumps in.
 */
export function missionRoster(mission: MissionName, mode: RosterMode, rules: RosterRules, info: Record<string, HullInfo>, rng: Rng): Roster {
  if (mission === "deathmatch") return chooseRoster(mode, rules, info, rng);
  const R = MISSION_ROSTERS;
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

/**
 * The mission brief under the muster's title (HTML). `convoy` is the sim's convoy view
 * at tick 0, so the numbers are the sim's thresholds, not ours.
 */
export function missionBrief(mission: MissionName, convoy: ConvoyState | null): string {
  if (mission === "carrier_battle") {
    return "Each carrier launches its wing from its bays. Lose your carrier, lose the match.";
  }
  if (mission === "convoy_escort" && convoy) {
    const n = convoy.total;
    return (
      `${n} freighters must reach the jump point. ${teamSpan(0, TEAM_WORDS[0])} escorts, ${teamSpan(1, TEAM_WORDS[1])} intercepts: ` +
      `${convoy.toDestroy} kill${convoy.toDestroy === 1 ? "" : "s"} stop${convoy.toDestroy === 1 ? "s" : ""} the convoy.`
    );
  }
  return "Last side flying wins.";
}
