// The ship inspector: tap a ship and the camera comes in on it (world.setFocus) while this
// panel says who it is. "Details" opens the rest: which net, what it was trained to do,
// and each control in small boxes: a bar for what the ship is doing (thrust and each power
// system as columns, each gun's aim as a row, its trigger a lamp) with a thin line per tick
// where that tick's command would take it, fading over half a second, so a steady net
// draws one bright line and a wavering one a smear. A toggle swaps them for the odds the
// net gave each choice on the last tick, with numbers. The views are built once per ship;
// the bars redraw every frame, the odds a few times a second. A craft called home (v11)
// says so; once docked it stays inspected in the hangar ("docked", its repair and when it
// may launch) and is followed back out on its relaunch, the same slot and pilot.

import { TEAM_CLASSES, TEAM_NAMES, TEAM_WORDS, escapeHtml } from "./teams.ts";
import { DOCK_INBOUND, DOCK_REPAIRING, JUMP_CHARGING, JUMP_DEPARTED, ROLE_CARRIER, type ShipState } from "./sim.ts";
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
// A trigger lamp's light per tick held: about half a second held lights it full.
const LAMP_ALPHA = 0.22;
/**
 * The hull share the scripted commander relaunches a returned craft at (sim
 * scripted::commander RELAUNCH_HULL_FRAC; tests/test_web_dock.py holds it to rlf_sim.DOCK),
 * and the share of its hull a hangar repairs a second (REPAIR_FRAC_PER_S).
 */
export const SCRIPT_RELAUNCH_HULL = 0.9;
export const REPAIR_PER_SECOND = 0.05;

// The odds view's groups, and what each choice of theirs is.
const GROUPS: Array<{ kind: OutputKind; title: string; legend: string }> = [
  { kind: "throttle", title: "Thrusters", legend: "less · hold · more" },
  { kind: "slew", title: "Turret aim", legend: "left · hold · right" },
  { kind: "fire", title: "Trigger", legend: "hold · fire" },
  { kind: "power", title: "Power", legend: "the seven splits" },
];
// The ship view's power bars run from empty to this share (the most a two-way hull gives
// one system), so the splits' 20 / 33 / 40 / 60 / 80% read well apart.
const POWER_FULL = 0.8;
const SYSTEMS = ["shields", "engines", "weapons"];

/** One row of the odds view. */
interface OddsRow {
  row: OutputRow;
  segments: HTMLElement[];
  value: HTMLElement;
  drawn: number;
}

/** One bar of the ship view: a control's state and its recent commands. */
interface Gauge {
  canvas: HTMLCanvasElement;
  row: OutputRow;
  /** Thrust and power fill upward; aim and trigger run left to right. */
  vertical: boolean;
  /** Power: the system this bar is (0 shields, 1 engines, 2 weapons). */
  system: number;
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

/** "9/12 turrets", "3/4 bays": a capital ship's mounts still standing (v10; none before). */
function mountsLeft(ship: ShipState): string[] {
  const standing = (state: Float32Array, n: number): number => state.subarray(0, n).reduce((k, v) => k + (v > 0 ? 1 : 0), 0);
  const out: string[] = [];
  if (ship.nTurrets > 0) out.push(`${standing(ship.turretState, ship.nTurrets)}/${ship.nTurrets} turrets`);
  if (ship.nBays > 0) out.push(`${standing(ship.bayState, ship.nBays)}/${ship.nBays} bays`);
  return out;
}

/** The order this ship's squad holds, in words; a craft called home has its own. */
function orderText(match: LiveMatch, i: number): string {
  const ship = match.ships[i]!;
  if (ship.dockPhase === DOCK_INBOUND) {
    const metres = Math.round(Math.hypot(ship.dockX - ship.x, ship.dockY - ship.y));
    return `called home · ${metres} m to the bay`;
  }
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
  private oddsRows: OddsRow[] = [];
  private gauges: Gauge[] = [];
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
    this.buildViews(outputRows(heads, match.validHeads(i), thrusters, turrets.map((t) => t.id)), strike, ship.power[0] === 0);
    this.setOdds(this.showOdds);
    this.setTitle(match, i, "");
    this.refresh(match, i);
  }

  close(): void {
    this.ship = -1;
    this.root.hidden = true;
    this.more.replaceChildren();
    this.oddsRows = [];
    this.gauges = [];
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
    return [el("p", "ins-fact", "No neural net: the sim's script flies it.")];
  }

  private buildViews(rows: OutputRow[], strike: boolean, twoWay: boolean): void {
    this.oddsRows = [];
    this.gauges = [];
    const intro = el("p", "ins-fact ins-explain");
    intro.append(this.explain, this.modeBtn);
    // The record stays at the end of the panel, under the outputs.
    this.more.append(intro, this.buildShipView(rows, twoWay), this.buildOddsView(rows, strike), this.record);
  }

  /** Boxes that wrap to the panel's width: thrust columns, power columns, a row per turret. */
  private buildShipView(rows: OutputRow[], twoWay: boolean): HTMLElement {
    const view = el("div", "ins-shipview");
    const thrust = rows.filter((r) => r.kind === "throttle");
    if (thrust.length) {
      const cols = el("div", "ins-cols");
      for (const row of thrust) cols.append(this.column(row, row.label, 0));
      view.append(this.box("Thrust", "", cols));
    }
    const power = rows.find((r) => r.kind === "power");
    if (power) {
      const cols = el("div", "ins-cols");
      // A hull with no shield splits its power two ways.
      for (const k of twoWay ? [1, 2] : [0, 1, 2]) cols.append(this.column(power, SYSTEMS[k]!, k));
      view.append(this.box("Power", "", cols));
    }
    const mounts = [...new Set(rows.filter((r) => r.kind === "slew" || r.kind === "fire").map((r) => r.mount))].sort((a, b) => a - b);
    if (mounts.length) {
      const lines = mounts.map((mount) => {
        const aim = rows.find((r) => r.kind === "slew" && r.mount === mount);
        const fire = rows.find((r) => r.kind === "fire" && r.mount === mount);
        const line = el("div", "ins-turret");
        line.append(el("span", "ins-label", (aim ?? fire)!.label));
        if (aim) line.append(this.gauge(aim, false, 0, "ins-aim"));
        if (fire) line.append(this.gauge(fire, false, 0, "ins-lamp"));
        return line;
      });
      const anyAim = rows.some((r) => r.kind === "slew");
      const box = this.box("Guns", anyAim ? "aim · lit: firing · ring: shot" : "lit: firing · ring: shot", ...lines);
      if (anyAim) box.classList.add("ins-box--guns");
      view.append(box);
    }
    return view;
  }

  private box(title: string, legend: string, ...content: HTMLElement[]): HTMLElement {
    const box = el("div", "ins-box");
    const head = el("div", "ins-box-head");
    head.append(el("span", "", title));
    if (legend) head.append(el("span", "ins-legend", legend));
    box.append(head, ...content);
    return box;
  }

  private column(row: OutputRow, label: string, system: number): HTMLElement {
    const col = el("div", "ins-col");
    col.append(this.gauge(row, true, system, "ins-vbar"), el("span", "ins-col-label", label));
    return col;
  }

  private gauge(row: OutputRow, vertical: boolean, system: number, className: string): HTMLCanvasElement {
    const canvas = document.createElement("canvas");
    canvas.className = className;
    this.gauges.push({ canvas, row, vertical, system });
    return canvas;
  }

  /** The net's odds on the last tick, a row per output with its number beside it. */
  private buildOddsView(rows: OutputRow[], strike: boolean): HTMLElement {
    const view = el("div", "ins-oddsview");
    for (const group of GROUPS) {
      const members = rows.filter((r) => r.kind === group.kind);
      if (!members.length) continue;
      const heading = el("p", "ins-group");
      // A script has no odds to label.
      heading.append(el("span", "", group.title), el("span", "ins-legend", strike ? group.legend : ""));
      const grid = el("div", `ins-rows ins-rows--${group.kind}`);
      for (const row of members) grid.append(this.oddsRow(row));
      view.append(heading, grid);
    }
    return view;
  }

  private oddsRow(row: OutputRow): HTMLElement {
    const node = el("div", "ins-row");
    const bar = el("span", "ins-bar");
    const segments = Array.from({ length: row.choices }, (_, c) => {
      const seg = el("i", `c${row.kind === "fire" ? c * 2 : row.kind === "power" ? 1 : c}`);
      bar.append(seg);
      return seg;
    });
    const value = el("span", "ins-value");
    if (row.label) node.append(el("span", "ins-label", row.label));
    node.append(bar, value);
    this.oddsRows.push({ row, segments, value, drawn: -1 });
    return node;
  }

  private refresh(match: LiveMatch, i: number): void {
    const ship = match.ships[i]!;
    this.setTitle(match, i, this.stateWord(match, ship));
    const max = match.maxHp[i] ?? 1;
    this.hullBar.style.width = percent(Math.max(0, ship.hp) / Math.max(1, max));
    setText(this.line, this.statusText(match, i, ship, max));
    if (this.more.hidden) return;
    const r = match.records[i]!;
    const home = r.recalls > 0 ? ` · called home ${r.recalls}× · docked ${r.docks}×` : "";
    setText(this.record, `This match: ${plural(r.shots, "shot")} · ${plural(r.hits, "hit")} · ${Math.round(r.damage)} hull damage · ${plural(r.kills, "kill")}${home}`);
    const w = match.watched;
    if (!this.showOdds || w.tick < 0 || match.watching !== i) return;
    const logits = match.watchedScripted ? null : w.logits;
    for (const view of this.oddsRows) {
      rowOdds(view.row, logits, w.row, this.odds);
      const drawn = w.row[view.row.column]!;
      view.segments.forEach((seg, c) => {
        seg.style.flexGrow = this.odds[c]!.toFixed(3);
      });
      if (drawn !== view.drawn) {
        view.segments[view.drawn]?.classList.remove("drawn");
        view.segments[drawn]?.classList.add("drawn");
        view.drawn = drawn;
      }
      setText(view.value, this.valueText(view.row, ship, drawn));
    }
  }

  /** Every gauge: the control's state, then each recent command's fading line over it. */
  private drawShip(match: LiveMatch): void {
    if (match.watching !== this.ship) return;
    const ship = match.ships[this.ship]!;
    // The latest command was chosen on the tick before the sim's clock.
    const now = match.tick - 1;
    const dpr = window.devicePixelRatio || 1;
    const twoWay = ship.power[0] === 0;
    const lineW = Math.max(1, Math.round(dpr));
    for (const g of this.gauges) {
      const c = g.canvas;
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
      if (g.row.kind === "fire") {
        this.drawLamp(ctx, g, match, now, w, h, lineW);
        continue;
      }
      const along = g.vertical ? h : w;
      const across = g.vertical ? w : h;
      const inset = g.vertical ? 0 : Math.round(across * 0.2);
      // A span [a, b] of the bar (0 its empty end) across its track, or a line across all of it.
      const fill = (a: number, b: number, full = false): void => {
        const lo = Math.round(a * along);
        const len = Math.max(0, Math.round(b * along) - lo);
        const c0 = full ? 0 : inset;
        const span = full ? across : across - 2 * inset;
        if (g.vertical) ctx.fillRect(c0, along - lo - len, span, len);
        else ctx.fillRect(lo, c0, len, span);
      };
      ctx.globalAlpha = 1;
      ctx.fillStyle = this.palette.track;
      fill(0, 1);
      ctx.fillStyle = this.palette.state;
      this.drawState(g, ship, fill, (2 * lineW + 1) / along);
      // Lines add up where they overlap: one command held reads bright, a dither dim and spread.
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = this.palette.accent;
      const thick = lineW / along;
      for (const tick of match.watchHistory) {
        if (tick.tick < 0) continue;
        const age = (now - tick.tick) / SIM_HZ;
        if (age < 0 || age >= LINE_FADE) continue;
        ctx.globalAlpha = LINE_ALPHA * (1 - age / LINE_FADE);
        const p = this.asked(g, tick.row[g.row.column]!, tick.throttles, tick.turretAngles, twoWay);
        if (p !== null) fill(p * (1 - thick), p * (1 - thick) + thick, true);
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
    }
  }

  /**
   * A trigger as a lamp: each tick the net held it adds light that fades over half a
   * second, so steady fire glows solid and a stray tap flickers; a ring flashes per shot.
   */
  private drawLamp(ctx: CanvasRenderingContext2D, g: Gauge, match: LiveMatch, now: number, w: number, h: number, ring: number): void {
    const pad = 2 * ring;
    ctx.globalAlpha = 1;
    ctx.fillStyle = this.palette.track;
    ctx.fillRect(pad, pad, w - 2 * pad, h - 2 * pad);
    ctx.globalCompositeOperation = "lighter";
    ctx.fillStyle = this.palette.accent;
    for (const tick of match.watchHistory) {
      if (tick.tick < 0 || tick.row[g.row.column]! <= 0) continue;
      const age = (now - tick.tick) / SIM_HZ;
      if (age < 0 || age >= LINE_FADE) continue;
      ctx.globalAlpha = LAMP_ALPHA * (1 - age / LINE_FADE);
      ctx.fillRect(pad, pad, w - 2 * pad, h - 2 * pad);
    }
    ctx.globalCompositeOperation = "source-over";
    const shot = match.watchedShots[g.row.mount] ?? -1;
    const age = shot < 0 ? Infinity : (now + 1 - shot) / SIM_HZ;
    if (age < SHOT_FLASH) {
      ctx.globalAlpha = 1 - age / SHOT_FLASH;
      ctx.strokeStyle = this.palette.state;
      ctx.lineWidth = ring;
      ctx.strokeRect(ring / 2, ring / 2, w - ring, h - ring);
    }
    ctx.globalAlpha = 1;
  }

  private drawState(g: Gauge, ship: ShipState, fill: (a: number, b: number) => void, mark: number): void {
    const ctx = g.canvas.getContext("2d")!;
    switch (g.row.kind) {
      case "throttle":
        ctx.globalAlpha = 0.45;
        fill(0, ship.throttles[g.row.mount] ?? 0);
        break;
      case "slew": {
        const travel = this.travel[g.row.mount];
        if (!travel) break;
        const p = turretPosition(ship.turretAngles[g.row.mount] ?? 0, travel) * (1 - mark);
        ctx.globalAlpha = 0.8;
        fill(p, p + mark);
        break;
      }
      case "fire":
        // A lamp (drawLamp).
        break;
      case "power":
        ctx.globalAlpha = 0.45;
        fill(0, Math.min(1, (ship.power[g.system] ?? 0) / POWER_FULL));
        break;
    }
  }

  /** Where one tick's command would take its control, 0..1 along the gauge; null for none. */
  private asked(g: Gauge, head: number, throttles: Float32Array, angles: Float32Array, twoWay: boolean): number | null {
    switch (g.row.kind) {
      case "throttle":
        return throttleAsk(throttles[g.row.mount] ?? 0, head);
      case "slew": {
        const travel = this.travel[g.row.mount];
        return travel ? turretAsk(angles[g.row.mount] ?? 0, head, travel) : null;
      }
      case "fire":
        return null;
      case "power":
        return Math.min(1, powerTarget(head, twoWay)[g.system]! / POWER_FULL);
    }
  }

  /** The odds view's number beside each bar. */
  private valueText(row: OutputRow, ship: ShipState, drawn: number): string {
    switch (row.kind) {
      case "throttle":
        return percent(ship.throttles[row.mount] ?? 0);
      case "slew":
        return `${Math.round((ship.turretAngles[row.mount] ?? 0) * RAD_TO_DEG)}°`;
      case "fire":
        return percent(this.odds[1] ?? 0);
      case "power":
        return POWER_NAMES[drawn] ?? "";
    }
  }

  private stateWord(match: LiveMatch, ship: ShipState): string {
    if (!ship.alive) return "destroyed";
    if (match.returned(ship)) return "docked";
    if (ship.dockPhase === DOCK_INBOUND) return "returning";
    if (ship.jump === JUMP_DEPARTED) return "jumped out";
    if (ship.jump === JUMP_CHARGING) return "charging jump";
    return "";
  }

  /** A returned craft in its hangar: how far its repair is and when it may go again. */
  private hangarText(match: LiveMatch, ship: ShipState, max: number): string {
    const share = Math.max(0, ship.hp) / Math.max(1, max);
    const parts = [`${Math.ceil(Math.max(0, ship.hp))}/${max}`, share >= 1 ? "repaired" : `repairing ${percent(share)}`];
    if (ship.dockPhase === DOCK_REPAIRING) {
      parts.push(`ready in ${Math.max(1, Math.ceil((ship.readyAt - match.tick) / SIM_HZ))} s`);
    } else if (!match.commanders[ship.team === 0 ? 0 : 1].net && share < SCRIPT_RELAUNCH_HULL) {
      // The scripted commander (the only one that recalls yet) waits for most of its hull.
      parts.push(`out at ${percent(SCRIPT_RELAUNCH_HULL)} in ~${Math.ceil((SCRIPT_RELAUNCH_HULL - share) / REPAIR_PER_SECOND)} s`);
    } else {
      parts.push("ready to launch");
    }
    return parts.join(" · ");
  }

  private statusText(match: LiveMatch, i: number, ship: ShipState, max: number): string {
    if (match.returned(ship)) return this.hangarText(match, ship, max);
    const parts = [`${Math.ceil(Math.max(0, ship.hp))}/${max}`];
    if (ship.shield > 0) parts.push(`shield ${Math.ceil(ship.shield)}`);
    parts.push(`${Math.round(Math.hypot(ship.vx, ship.vy))} m/s`);
    if (ship.role === "strike") {
      parts.push(match.pilot(i).obsDim < ORDER_OBS_DIM ? "can't read orders" : orderText(match, i));
    } else if (ship.role === ROLE_CARRIER) {
      const repairing = match.repairing(ship.team);
      parts.push(`${match.teams[ship.team]!.hangar} in hangar${repairing ? ` · ${repairing} repairing` : ""}`);
    }
    // v10: a capital ship's turrets and bays can be shot off one by one.
    if (ship.role !== "strike") parts.push(...mountsLeft(ship));
    return parts.join(" · ");
  }
}
