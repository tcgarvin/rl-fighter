// The ship inspector: tap a ship and the camera comes in on it (world.setFocus) while this
// panel says who it is. "Details" opens the rest: which net, what it was trained to do,
// and each control: a bar for what the ship is doing (thrust, turret angle, shots, power
// split) with a thin line per tick where that tick's command would take it, fading over
// half a second, so a steady net draws one bright line and a wavering one a smear. A
// toggle swaps the bars for the odds the net gave each choice on the last tick. The rows
// are built once per ship; the bars redraw every frame, the numbers a few times a second.

import { TEAM_CLASSES, TEAM_NAMES, TEAM_WORDS, escapeHtml } from "./teams.ts";
import { JUMP_CHARGING, JUMP_DEPARTED, ROLE_CARRIER, type ShipState } from "./sim.ts";
import {
  POWER_NAMES,
  outputRows,
  powerTarget,
  rowOdds,
  throttleAsk,
  turretAsk,
  turretPosition,
  type OutputKind,
  type OutputRow,
  type TurretTravel,
} from "./inspect.ts";
import type { LiveMatch } from "./match.ts";
import { SIM_HZ } from "./sim.ts";
import { commanderName, type PilotEntry } from "./bundle.ts";

const REFRESH_SECONDS = 0.12;
const RAD_TO_DEG = 180 / Math.PI;
// Inputs a pilot needs to read orders at all (SIM_SPEC §0.3: v5 appended them at 385).
const ORDER_OBS_DIM = 403;
const MAX_CHOICES = 7;
// A command's line fades out over this long, seconds; a shot's flash over SHOT_FLASH.
const LINE_FADE = 0.5;
const SHOT_FLASH = 0.3;
// The brightest a single line starts; overlapping lines add up toward solid.
const LINE_ALPHA = 0.6;

const GROUPS: Array<{ kind: OutputKind; title: string; odds: string; ship: string }> = [
  { kind: "throttle", title: "Thrusters", odds: "less · hold · more", ship: "thrust, off to full" },
  { kind: "slew", title: "Turret aim", odds: "left · hold · right", ship: "angle across its arc" },
  { kind: "fire", title: "Trigger", odds: "hold · fire", ship: "a flash per shot · fire at the right" },
  { kind: "power", title: "Power", odds: "the seven splits", ship: "shields · engines · weapons" },
];

interface RowView {
  row: OutputRow;
  /** The odds view. */
  segments: HTMLElement[];
  /** The ship view. */
  canvas: HTMLCanvasElement;
  value: HTMLElement;
  drawn: number;
}

interface Palette {
  accent: string;
  track: string;
  state: string;
}

function el(tag: string, className = "", text = ""): HTMLElement {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function setText(node: HTMLElement, text: string): void {
  if (node.textContent !== text) node.textContent = text;
}

const percent = (v: number): string => `${Math.round(v * 100)}%`;
const plural = (n: number, word: string): string => `${n.toLocaleString("en-GB")} ${word}${n === 1 ? "" : "s"}`;
const signed = (v: number): string => `${v >= 0 ? "+" : ""}${Math.round(v)}`;

/** The pilot's score as viewers read it: wins over the script, or combat-rating points. */
function ratingText(info: PilotEntry): string {
  if (info.rated_by === "war") return `${signed(info.rating)} wins/100 over the script`;
  return `Rated ${signed(info.rating)}`;
}

/** The order this ship's squad holds, in words. */
function orderText(match: LiveMatch, i: number): string {
  const ship = match.ships[i]!;
  const squad = match.squads.find((q) => q.team === ship.team && q.index === ship.squad);
  if (!squad || squad.order === "none") return "no order";
  if (squad.order === "goto") return "ordered to a point";
  const target = match.labels[squad.target];
  const whose = match.ships[squad.target]?.team === ship.team ? "our" : "enemy";
  return `ordered to ${squad.order} ${target ? `${whose} ${target}` : "a ship"}`;
}

export class Inspector {
  /** Tap the inspected ship again, or press the button: the details open or close. */
  readonly outputsBtn: HTMLButtonElement;
  readonly closeBtn: HTMLButtonElement;
  /** Swaps the bars between the ship's controls and the net's odds. */
  readonly modeBtn: HTMLButtonElement;
  private readonly title = el("div", "ins-title");
  private readonly line = el("div", "ins-line");
  private readonly hullBar = el("i");
  private readonly more = el("div", "ins-more");
  private readonly record = el("p", "ins-fact");
  private readonly explain = el("span");
  private readonly legends: Array<{ node: HTMLElement; odds: string; ship: string }> = [];
  private rows: RowView[] = [];
  private ship = -1;
  private untilRefresh = 0;
  private readonly odds = new Float64Array(MAX_CHOICES);
  private showOdds: boolean;
  private travel: TurretTravel[] = [];
  private palette: Palette = { accent: "#fff", track: "#333", state: "#999" };

  constructor(
    private readonly root: HTMLElement,
    odds = false,
  ) {
    this.showOdds = odds;
    this.outputsBtn = el("button", "ins-outputs", "Details") as HTMLButtonElement;
    this.outputsBtn.setAttribute("type", "button");
    this.closeBtn = el("button", "ins-close", "✕") as HTMLButtonElement;
    this.closeBtn.setAttribute("type", "button");
    this.closeBtn.setAttribute("aria-label", "Stop inspecting this ship");
    this.modeBtn = el("button", "ins-mode") as HTMLButtonElement;
    this.modeBtn.setAttribute("type", "button");
    const head = el("div", "ins-head");
    head.append(this.title, this.outputsBtn, this.closeBtn);
    const bar = el("span", "ins-hull");
    bar.append(this.hullBar);
    const status = el("div", "ins-status");
    status.append(bar, this.line);
    this.root.append(head, status, this.more);
  }

  /** Whether the bars show the net's odds (true) or the ship's controls. */
  get oddsShown(): boolean {
    return this.showOdds;
  }

  setOdds(on: boolean): void {
    this.showOdds = on;
    this.root.classList.toggle("odds", on);
    this.modeBtn.textContent = on ? "Show the ship" : "Show the odds";
    this.explain.textContent = on ? "Bars: last tick's odds, the pick outlined · " : "Bars: the ship now · lines: each tick's command, fading over ½ s · ";
    for (const l of this.legends) l.node.textContent = on ? l.odds : l.ship;
    this.untilRefresh = 0;
  }

  /** Inspect ship `i`. `thrusters` and `turrets` are its hull's mount ids, in sim order. */
  open(match: LiveMatch, i: number, thrusters: string[], turrets: Array<{ id: string } & TurretTravel>, entry: string): void {
    this.ship = i;
    this.untilRefresh = 0;
    this.travel = turrets;
    const ship = match.ships[i]!;
    this.root.className = TEAM_CLASSES[ship.team]!;
    this.root.hidden = false;
    const css = getComputedStyle(this.root);
    const color = (name: string, fallback: string): string => css.getPropertyValue(name).trim() || fallback;
    this.palette = { accent: color("--ins-accent", "#fff"), track: color("--line", "#333"), state: color("--fg-soft", "#999") };
    const strike = ship.role === "strike";
    const facts = strike ? this.pilotFacts(match, i, entry) : this.scriptFacts();
    this.more.replaceChildren(...facts, ...this.commanderFacts(match, ship.team), this.record);
    const heads = match.pilot(i).policy.manifest.heads;
    this.buildRows(outputRows(heads, match.validHeads(i), thrusters, turrets.map((t) => t.id)), strike, ship.power[0] === 0);
    this.setOdds(this.showOdds);
    this.setTitle(match, i, "");
    this.refresh(match, i);
  }

  close(): void {
    this.ship = -1;
    this.root.hidden = true;
    this.more.replaceChildren();
    this.rows = [];
  }

  /** Whether the details show; the button says which. */
  setOutputs(on: boolean): void {
    this.outputsBtn.setAttribute("aria-pressed", String(on));
    this.more.hidden = !on;
  }

  /** Redraw the ship's bars every frame; refresh the numbers a few times a second. */
  update(match: LiveMatch, realDt: number): void {
    if (this.ship < 0) return;
    if (!this.more.hidden && !this.showOdds) this.drawShip(match);
    this.untilRefresh -= realDt;
    if (this.untilRefresh > 0) return;
    this.untilRefresh = REFRESH_SECONDS;
    this.refresh(match, this.ship);
  }

  private setTitle(match: LiveMatch, i: number, state: string): void {
    const ship = match.ships[i]!;
    const who = ship.role === "strike" ? match.pilotId(i) : "sim's script";
    const stateHtml = state ? ` <span class="ins-state">${escapeHtml(state)}</span>` : "";
    const html = `<b>${TEAM_NAMES[ship.team]} ${escapeHtml(match.labels[i]!)}</b> <span class="ins-who">${escapeHtml(who)}</span>${stateHtml}`;
    if (this.title.innerHTML !== html) this.title.innerHTML = html;
  }

  // Kept to the pilot's sentence and two short lines, so the outputs fit without scrolling.
  private pilotFacts(match: LiveMatch, i: number, entry: string): HTMLElement[] {
    const pilot = match.pilot(i);
    const m = pilot.policy.manifest;
    const info = pilot.entry;
    const shape = [m.layers[0]!.in, ...m.layers.map((l) => l.out)].join("→");
    const facts: HTMLElement[] = [];
    if (info?.note) facts.push(el("p", "ins-note", info.note));
    const who = info ? `${ratingText(info)} · family ${info.family} · ` : "";
    facts.push(el("p", "ins-fact", `${who}net ${shape}`));
    const drills = el("p", "ins-fact", this.followText(pilot.obsDim, info?.follows));
    if (entry) {
      const a = el("a", "", "Meet the pilots →") as HTMLAnchorElement;
      a.href = `/notebook/#${encodeURIComponent(entry)}`;
      drills.append(" · ", a);
    }
    facts.push(drills);
    return facts;
  }

  private followText(obsDim: number, follows: { go_to?: number; attack?: number; defend?: number } | undefined): string {
    if (obsDim < ORDER_OBS_DIM) return "Can't read orders";
    if (!follows || follows.go_to === undefined) return "Orders never drilled";
    return `Drills: go-to ${percent(follows.go_to)} · attack ${percent(follows.attack ?? 0)} · defend ${percent(follows.defend ?? 0)}`;
  }

  /** Who gives this side its orders, in one line. */
  private commanderFacts(match: LiveMatch, team: number): HTMLElement[] {
    const c = match.commanders[team === 0 ? 0 : 1];
    const who = c.net ? `${commanderName(c)} (neural net, once a second)` : "the sim's script";
    return [el("p", "ins-fact", `${TEAM_WORDS[team]} commander: ${who}`)];
  }

  private scriptFacts(): HTMLElement[] {
    return [el("p", "ins-fact", "No neural net here: the sim's script flies it (its odds are all or nothing).")];
  }

  private buildRows(rows: OutputRow[], strike: boolean, twoWay: boolean): void {
    this.rows = [];
    this.legends.length = 0;
    const intro = el("p", "ins-fact ins-explain");
    intro.append(this.explain, this.modeBtn);
    this.more.append(intro);
    for (const group of GROUPS) {
      const members = rows.filter((r) => r.kind === group.kind);
      if (!members.length) continue;
      const heading = el("p", "ins-group");
      const legend = el("span", "ins-legend");
      // A script has no odds to label; its ship view reads the same as a pilot's.
      // A hull with no shield splits its power two ways.
      const ship = group.kind === "power" && twoWay ? "engines · weapons" : group.ship;
      this.legends.push({ node: legend, odds: strike ? group.odds : "", ship });
      heading.append(el("span", "", group.title), legend);
      const grid = el("div", `ins-rows ins-rows--${group.kind}`);
      for (const row of members) grid.append(this.buildRow(row));
      this.more.append(heading, grid);
    }
    // The record stays at the end of the panel, under the outputs.
    this.more.append(this.record);
  }

  private buildRow(row: OutputRow): HTMLElement {
    const node = el("div", "ins-row");
    const bar = el("span", "ins-bar");
    const segments = Array.from({ length: row.choices }, (_, c) => {
      const seg = el("i", `c${row.kind === "fire" ? c * 2 : row.kind === "power" ? 1 : c}`);
      bar.append(seg);
      return seg;
    });
    const canvas = document.createElement("canvas");
    canvas.className = "ins-ship";
    const value = el("span", "ins-value");
    if (row.label) node.append(el("span", "ins-label", row.label));
    node.append(bar, canvas, value);
    this.rows.push({ row, segments, canvas, value, drawn: -1 });
    return node;
  }

  private refresh(match: LiveMatch, i: number): void {
    const ship = match.ships[i]!;
    this.setTitle(match, i, this.stateWord(ship));
    const max = match.maxHp[i] ?? 1;
    this.hullBar.style.width = percent(Math.max(0, ship.hp) / Math.max(1, max));
    setText(this.line, this.statusText(match, i, ship, max));
    if (this.more.hidden) return;
    const r = match.records[i]!;
    setText(this.record, `This match: ${plural(r.shots, "shot")} · ${plural(r.hits, "hit")} · ${Math.round(r.damage)} hull damage · ${plural(r.kills, "kill")}`);
    const w = match.watched;
    if (w.tick < 0 || match.watching !== i) return;
    const logits = match.watchedScripted ? null : w.logits;
    for (const view of this.rows) {
      rowOdds(view.row, logits, w.row, this.odds);
      const drawn = w.row[view.row.column]!;
      if (this.showOdds) {
        view.segments.forEach((seg, c) => {
          seg.style.flexGrow = this.odds[c]!.toFixed(3);
        });
        if (drawn !== view.drawn) {
          view.segments[view.drawn]?.classList.remove("drawn");
          view.segments[drawn]?.classList.add("drawn");
          view.drawn = drawn;
        }
      }
      setText(view.value, this.valueText(match, view.row, ship, drawn));
    }
  }

  /** Every row's bar: the control's state, then each recent command's fading line over it. */
  private drawShip(match: LiveMatch): void {
    if (match.watching !== this.ship) return;
    const ship = match.ships[this.ship]!;
    // The latest command was chosen on the tick before the sim's clock.
    const now = match.tick - 1;
    const dpr = window.devicePixelRatio || 1;
    const twoWay = ship.power[0] === 0;
    for (const view of this.rows) {
      const c = view.canvas;
      const w = Math.round(c.clientWidth * dpr);
      const h = Math.round(c.clientHeight * dpr);
      if (w <= 0 || h <= 0) continue;
      if (c.width !== w || c.height !== h) {
        c.width = w;
        c.height = h;
      }
      const ctx = c.getContext("2d");
      if (!ctx) continue;
      ctx.clearRect(0, 0, w, h);
      const top = Math.round(h * 0.2);
      const band = h - 2 * top;
      ctx.globalAlpha = 1;
      ctx.fillStyle = this.palette.track;
      ctx.fillRect(0, top, w, band);
      this.drawState(ctx, view.row, match, ship, w, top, band, now, dpr);
      // Lines add up where they overlap: one command held reads bright, a dither dim and spread.
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = this.palette.accent;
      const lineW = Math.max(1, Math.round(dpr));
      for (const tick of match.watchHistory) {
        if (tick.tick < 0) continue;
        const age = (now - tick.tick) / SIM_HZ;
        if (age < 0 || age >= LINE_FADE) continue;
        ctx.globalAlpha = LINE_ALPHA * (1 - age / LINE_FADE);
        for (const x of this.asked(view.row, tick.row[view.row.column]!, tick.throttles, tick.turretAngles, twoWay)) {
          ctx.fillRect(Math.round(x * (w - lineW)), 0, lineW, h);
        }
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
    }
  }

  private drawState(ctx: CanvasRenderingContext2D, row: OutputRow, match: LiveMatch, ship: ShipState, w: number, top: number, band: number, now: number, dpr: number): void {
    ctx.fillStyle = this.palette.state;
    switch (row.kind) {
      case "throttle":
        ctx.globalAlpha = 0.45;
        ctx.fillRect(0, top, Math.round(w * (ship.throttles[row.mount] ?? 0)), band);
        break;
      case "slew": {
        const travel = this.travel[row.mount];
        if (!travel) break;
        const mark = Math.max(2, Math.round(3 * dpr));
        ctx.globalAlpha = 0.8;
        ctx.fillRect(Math.round(turretPosition(ship.turretAngles[row.mount] ?? 0, travel) * (w - mark)), top, mark, band);
        break;
      }
      case "fire": {
        const shot = match.watchedShots[row.mount] ?? -1;
        const age = shot < 0 ? Infinity : (now + 1 - shot) / SIM_HZ;
        if (age < SHOT_FLASH) {
          ctx.globalAlpha = 0.7 * (1 - age / SHOT_FLASH);
          ctx.fillRect(0, top, w, band);
        }
        break;
      }
      case "power": {
        // Shields, engines, weapons, left to right, in three tones split by a gap.
        let x = 0;
        const gap = Math.max(1, Math.round(dpr));
        [0.55, 0.35, 0.2].forEach((alpha, k) => {
          const share = ship.power[k] ?? 0;
          const width = Math.round(w * share);
          ctx.globalAlpha = alpha;
          if (width > gap) ctx.fillRect(x, top, width - gap, band);
          x += width;
        });
        break;
      }
    }
  }

  /** Where one tick's command would take its control, 0..1 along the bar (power: two edges). */
  private asked(row: OutputRow, head: number, throttles: Float32Array, angles: Float32Array, twoWay: boolean): number[] {
    switch (row.kind) {
      case "throttle":
        return [throttleAsk(throttles[row.mount] ?? 0, head)];
      case "slew": {
        const travel = this.travel[row.mount];
        return travel ? [turretAsk(angles[row.mount] ?? 0, head, travel)] : [];
      }
      case "fire":
        return [head > 0 ? 1 : 0];
      case "power": {
        const [s, e] = powerTarget(head, twoWay);
        return twoWay ? [e] : [s, s + e];
      }
    }
  }

  /** Beside each bar: what the ship is doing with that output now. */
  private valueText(match: LiveMatch, row: OutputRow, ship: ShipState, drawn: number): string {
    switch (row.kind) {
      case "throttle":
        return percent(ship.throttles[row.mount] ?? 0);
      case "slew":
        return `${Math.round((ship.turretAngles[row.mount] ?? 0) * RAD_TO_DEG)}°`;
      case "fire":
        return this.showOdds ? percent(this.odds[1] ?? 0) : `${percent(this.fireShare(match, row))} on`;
      case "power":
        if (this.showOdds) return POWER_NAMES[drawn] ?? "";
        return (ship.power[0] === 0 ? [1, 2] : [0, 1, 2]).map((k) => Math.round((ship.power[k] ?? 0) * 100)).join(" · ");
    }
  }

  /** The share of the last half second the net held this trigger down. */
  private fireShare(match: LiveMatch, row: OutputRow): number {
    const now = match.tick - 1;
    let on = 0;
    let all = 0;
    for (const t of match.watchHistory) {
      if (t.tick < 0 || (now - t.tick) / SIM_HZ >= LINE_FADE) continue;
      all += 1;
      if (t.row[row.column]! > 0) on += 1;
    }
    return all ? on / all : 0;
  }

  private stateWord(ship: ShipState): string {
    if (!ship.alive) return "destroyed";
    if (ship.jump === JUMP_DEPARTED) return "jumped out";
    if (ship.jump === JUMP_CHARGING) return "charging jump";
    return "";
  }

  private statusText(match: LiveMatch, i: number, ship: ShipState, max: number): string {
    const parts = [`${Math.ceil(Math.max(0, ship.hp))}/${max}`];
    if (ship.shield > 0) parts.push(`shield ${Math.ceil(ship.shield)}`);
    parts.push(`${Math.round(Math.hypot(ship.vx, ship.vy))} m/s`);
    if (ship.role === "strike") {
      parts.push(match.pilot(i).obsDim < ORDER_OBS_DIM ? "can't read orders" : orderText(match, i));
    } else if (ship.role === ROLE_CARRIER) {
      parts.push(`${match.teams[ship.team]!.hangar} in hangar`);
    }
    return parts.join(" · ");
  }
}
