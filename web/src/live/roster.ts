// Rosters for the muster: a seeded random draft against a budget (the DESIGN §6 stub
// for learned drafting), or a fixed size from the URL (?fleets=duel, ?fleets=3v3).
// Only hulls the champion is certified to fly are ever drafted. Pure, so the Node
// smoke test drafts exactly as the page does.

import type { Rng } from "./policy.js";
import type { HullInfo } from "./sim.ts";
import type { Fleets } from "./match.ts";

export interface RosterRules {
  hulls: string[];
  min_per_side: number;
  max_per_side: number;
  budget: number;
}

/** How each match's rosters are chosen. */
export type RosterMode = { kind: "draft" } | { kind: "fixed"; perSide: [number, number] };

export interface Roster {
  fleets: Fleets;
  /** Credits each side could spend; null for a fixed-size roster. */
  budget: number | null;
}

const MAX_PER_SIDE = 4;
// A duel is a fighter's fight if the champion can fly one.
const DUEL_HULL = "fighter";

/** `duel` → 1v1, `NvM` → N against M (1–4 each); anything else drafts. */
export function parseRosterMode(param: string | null): RosterMode {
  if (param === "duel") return { kind: "fixed", perSide: [1, 1] };
  const m = /^([1-4])v([1-4])$/.exec(param ?? "");
  if (m) return { kind: "fixed", perSide: [Number(m[1]), Number(m[2])] };
  return { kind: "draft" };
}

/** The hulls a draft may use: the rules' list, restricted to what the catalogue has. */
export function draftableHulls(rules: RosterRules, info: Record<string, HullInfo>): string[] {
  const hulls = rules.hulls.filter((h) => info[h]);
  if (hulls.length === 0) throw new Error(`no draftable hulls: roster ${rules.hulls.join(", ")} not in the catalogue`);
  return hulls;
}

function pick<T>(items: readonly T[], rng: Rng): T {
  const item = items[Math.floor(rng() * items.length)];
  if (item === undefined) throw new Error("pick from an empty list");
  return item;
}

/**
 * Spend `budget` on random affordable hulls until nothing fits or the side is full,
 * never buying a hull that would leave too little to reach `minShips` of the cheapest.
 */
function draftSide(hulls: string[], info: Record<string, HullInfo>, budget: number, minShips: number, maxShips: number, rng: Rng): string[] {
  const cheapest = Math.min(...hulls.map((h) => info[h]!.cost));
  const side: string[] = [];
  let left = budget;
  for (;;) {
    const reserve = cheapest * Math.max(0, minShips - side.length - 1);
    const affordable = hulls.filter((h) => info[h]!.cost + reserve <= left);
    if (affordable.length === 0 || side.length >= maxShips) break;
    const hull = pick(affordable, rng);
    side.push(hull);
    left -= info[hull]!.cost;
  }
  return side;
}

/**
 * Both sides' rosters for one match. A draft first draws the match size (1 to
 * max_per_side of the cheapest hull's worth of credits), then each side spends that
 * same budget independently, so mixed fleets trade numbers for heavier hulls.
 */
export function chooseRoster(mode: RosterMode, rules: RosterRules, info: Record<string, HullInfo>, rng: Rng): Roster {
  const hulls = draftableHulls(rules, info);
  const maxShips = Math.min(MAX_PER_SIDE, rules.max_per_side);
  if (mode.kind === "fixed") {
    const [na, nb] = mode.perSide;
    const duel = na === 1 && nb === 1 && hulls.includes(DUEL_HULL);
    const side = (n: number) => Array.from({ length: n }, () => (duel ? DUEL_HULL : pick(hulls, rng)));
    const a = side(na);
    // Equal sizes mirror the hulls, so ?fleets=3v3 is an even fight rather than a lottery.
    return { fleets: [a, na === nb ? [...a] : side(nb)], budget: null };
  }
  const cheapest = Math.min(...hulls.map((h) => info[h]!.cost));
  const minShips = Math.max(1, Math.min(rules.min_per_side, maxShips));
  const size = minShips + Math.floor(rng() * (maxShips - minShips + 1));
  const budget = Math.min(rules.budget, cheapest * size);
  const side = () => draftSide(hulls, info, budget, minShips, maxShips, rng);
  return { fleets: [side(), side()], budget };
}

const NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight"];

function counts(fleet: string[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const h of fleet) out.set(h, (out.get(h) ?? 0) + 1);
  return out;
}

/** "a gunship and two fighters" */
export function describeFleet(fleet: string[]): string {
  const parts = [...counts(fleet)]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([hull, n]) => (n === 1 ? `${/^[aeiou]/.test(hull) ? "an" : "a"} ${hull}` : `${NUMBER_WORDS[n] ?? n} ${hull}s`));
  if (parts.length <= 1) return parts[0] ?? "nothing";
  return `${parts.slice(0, -1).join(", ")} and ${parts.at(-1)}`;
}

function sameFleet(a: string[], b: string[]): boolean {
  return [...a].sort().join() === [...b].sort().join();
}

/** One line for the muster: who meets whom. */
export function matchupLine(roster: Roster): string {
  const [a, b] = roster.fleets;
  let line: string;
  if (a.length === 1 && b.length === 1 && a[0] === b[0]) line = `A duel: one ${a[0]} each`;
  else if (sameFleet(a, b)) line = `Mirror match: ${describeFleet(a).replace(/^an? /, "one ")} a side`;
  else line = `${describeFleet(a)} against ${describeFleet(b)}`;
  return line.charAt(0).toUpperCase() + line.slice(1) + ".";
}
