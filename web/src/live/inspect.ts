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

/** A screen rectangle in CSS px (top < bottom). */
export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** The HUD's pieces that the inspected ship must keep clear of, in CSS px. */
export interface InspectLayout {
  /** The whole screen less the page's side and bottom padding, below the nav. */
  screen: Rect;
  /** The match status (top left) and the perf readout (top right). */
  status: Rect;
  perf: Rect;
  /** The inspector panel and the toggle buttons. */
  panel: Rect;
  controls: Rect;
}

/**
 * Where to frame the inspected ship: above the panel (the whole width, under the top HUD)
 * or, on a wide screen, beside it, from its right edge to the screen's (under whatever
 * of the top HUD reaches that far, above the buttons). The ship's frame is square, so the
 * choice is the one with the longer short side. `clear` is kept from every HUD edge.
 */
export function inspectFrame(l: InspectLayout, clear: number): Rect {
  const topHud = Math.max(l.status.bottom, l.perf.bottom);
  const above: Rect = { left: l.screen.left, right: l.screen.right, top: topHud + clear, bottom: l.panel.top - clear };
  const left = l.panel.right + clear;
  const overlaps = (r: Rect): boolean => r.right > left && r.bottom > r.top;
  const besideTop = Math.max(l.screen.top, ...[l.status, l.perf].filter(overlaps).map((r) => r.bottom + clear));
  const besideBottom = overlaps(l.controls) ? l.controls.top - clear : l.screen.bottom;
  const beside: Rect = { left, right: l.screen.right, top: besideTop, bottom: besideBottom };
  const room = (r: Rect): number => Math.min(r.right - r.left, r.bottom - r.top);
  return room(beside) > room(above) ? beside : above;
}

// ---- The ship view: each control's state, and where each tick's command would take it. ----

/** A command's line is drawn where it would take its control this far on, seconds. */
export const ASK_LOOKAHEAD = 0.25;
/** Thrust level per second of "more" or "less" (crates/sim/src/physics.rs RAMP_RATE). */
const RAMP_RATE = 5;
const DEG = Math.PI / 180;

const clamp01 = (v: number): number => Math.min(1, Math.max(0, v));

/** A turret's travel, from the hull catalogue: degrees and degrees per second. */
export interface TurretTravel {
  rest: number;
  arc: number;
  slew: number;
}

/** Where a thruster command takes its level (0..1): "more" full, "less" off, "hold" stays. */
export function throttleAsk(level: number, head: number): number {
  return clamp01(level + (head - 1) * RAMP_RATE * ASK_LOOKAHEAD);
}

/** A turret angle (radians) along its bar: 0 the left (counter-clockwise) end of the arc. */
export function turretPosition(angle: number, t: TurretTravel): number {
  if (!(t.arc > 0)) return 0.5;
  return clamp01((t.rest + t.arc / 2 - angle / DEG) / t.arc);
}

/** Where a slew command (left, hold, right) takes the turret, along its bar. */
export function turretAsk(angle: number, head: number, t: TurretTravel): number {
  const sign = head === 0 ? 1 : head === 1 ? 0 : -1;
  return turretPosition(angle + sign * t.slew * DEG * ASK_LOOKAHEAD, t);
}

// [shields, engines, weapons] by power head (crates/sim/src/power.rs POWER_TARGETS).
const POWER_TARGETS: ReadonlyArray<readonly [number, number, number]> = [
  [1 / 3, 1 / 3, 1 / 3],
  [0.6, 0.2, 0.2],
  [0.2, 0.6, 0.2],
  [0.2, 0.2, 0.6],
  [0.4, 0.4, 0.2],
  [0.4, 0.2, 0.4],
  [0.2, 0.4, 0.4],
];
const TWO_WAY_CAP = 0.8;

/** The split a power choice aims at; a hull with no shield splits two ways (power.rs). */
export function powerTarget(choice: number, twoWay: boolean): [number, number, number] {
  const t = POWER_TARGETS[choice] ?? POWER_TARGETS[0]!;
  if (!twoWay) return [t[0], t[1], t[2]];
  if (choice === 0) return [0, 0.5, 0.5];
  const e = Math.min(TWO_WAY_CAP, Math.max(1 - TWO_WAY_CAP, t[1] / (t[1] + t[2])));
  return [0, e, 1 - e];
}
