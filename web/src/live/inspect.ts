// What the ship inspector works out, with no DOM here so Node tests run it: which ship a
// tap meant, and the net's outputs for one ship as rows of odds. The net's outputs are
// the policy heads (SIM_SPEC §7.1): a throttle rate per thruster, an aim rate and a
// trigger per turret, and one power split. Only a hull's real mounts are valid.

import type { PolicyHead } from "./policy.js";

/** A touch needs this much room (CSS px): ships are small on a phone. */
const TAP_REACH = 26;

export interface OnScreen {
  id: number;
  x: number;
  y: number;
  sizePx: number;
}

/**
 * The ship a tap at (x, y) meant, or -1. A ship counts within TAP_REACH of its hull. The
 * nearest centre wins, with big hulls allowed only TAP_REACH of credit for their size, so
 * a tap on a carrier takes the carrier unless a fighter is close by under the finger.
 */
export function pickShip(ships: readonly OnScreen[], x: number, y: number): number {
  let best = -1;
  let bestScore = Infinity;
  for (const s of ships) {
    const radius = s.sizePx / 2;
    const distance = Math.hypot(s.x - x, s.y - y);
    if (distance - radius > TAP_REACH) continue;
    const score = distance - Math.min(radius, TAP_REACH);
    if (score < bestScore) {
      best = s.id;
      bestScore = score;
    }
  }
  return best;
}

export type OutputKind = "throttle" | "slew" | "fire" | "power";

/** One head of the net, for one mount of this hull. */
export interface OutputRow {
  kind: OutputKind;
  /** The mount, without its "thruster." or "turret." prefix; "" for the power split. */
  label: string;
  /** Which thruster or turret; 0 for the power split. */
  mount: number;
  column: number;
  logitStart: number;
  choices: number;
}

const stripMount = (id: string): string => id.replace(/^(thruster|turret)\./, "");

/** The rows for a hull: the heads `valid` says it really has, in head order. */
export function outputRows(heads: readonly PolicyHead[], valid: Uint8Array, thrusters: readonly string[], turrets: readonly string[]): OutputRow[] {
  const rows: OutputRow[] = [];
  for (const h of heads) {
    const kind = h.name as OutputKind;
    for (let k = 0; k < h.count; k++) {
      const column = h.action_start + k;
      if (!valid[column]) continue;
      const names = kind === "throttle" ? thrusters : turrets;
      rows.push({
        kind,
        label: kind === "power" ? "" : stripMount(names[k] ?? `${k + 1}`),
        mount: k,
        column,
        logitStart: h.logit_start + k * h.choices,
        choices: h.choices,
      });
    }
  }
  return rows;
}

/**
 * The odds a row's head gave each choice, written into `out`. Without logits (a ship the
 * script flies) the script's choice has all of them: it has no odds, it just decides.
 */
export function rowOdds(row: OutputRow, logits: Float32Array | null, action: Int8Array, out: Float64Array): void {
  if (!logits) {
    for (let c = 0; c < row.choices; c++) out[c] = c === action[row.column] ? 1 : 0;
    return;
  }
  let max = -Infinity;
  for (let c = 0; c < row.choices; c++) max = Math.max(max, logits[row.logitStart + c]!);
  let total = 0;
  for (let c = 0; c < row.choices; c++) {
    out[c] = Math.exp(logits[row.logitStart + c]! - max);
    total += out[c]!;
  }
  for (let c = 0; c < row.choices; c++) out[c] = out[c]! / total;
}

/** What each power choice asks for (SIM_SPEC §5.2): shields, engines, weapons. */
export const POWER_NAMES = ["even", "shields", "engines", "weapons", "shields + engines", "shields + weapons", "engines + weapons"];
