// The ship inspector: tap a ship and the camera comes in on it (world.setFocus) while this
// panel says who it is. "Details" opens the rest: which net, what it was trained to do,
// and the odds it gave each output on the last tick, next to what it drew. The rows are
// built once per ship and only their numbers change, a few times a second.

import { TEAM_CLASSES, TEAM_NAMES, escapeHtml } from "./teams.ts";
import { JUMP_CHARGING, JUMP_DEPARTED, ROLE_CARRIER, type ShipState } from "./sim.ts";
import { POWER_NAMES, outputRows, rowOdds, type OutputKind, type OutputRow } from "./inspect.ts";
import type { LiveMatch } from "./match.ts";

const REFRESH_SECONDS = 0.12;
const RAD_TO_DEG = 180 / Math.PI;
// Inputs a pilot needs to read orders at all (SIM_SPEC §0.3: v5 appended them at 385).
const ORDER_OBS_DIM = 403;
const MAX_CHOICES = 7;

const GROUPS: Array<{ kind: OutputKind; title: string; legend: string }> = [
  { kind: "throttle", title: "Thrusters", legend: "less · hold · more" },
  { kind: "slew", title: "Turret aim", legend: "left · hold · right" },
  { kind: "fire", title: "Trigger", legend: "hold · fire" },
  { kind: "power", title: "Power", legend: "the seven splits" },
];

interface RowView {
  row: OutputRow;
  segments: HTMLElement[];
  value: HTMLElement;
  drawn: number;
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
  private readonly title = el("div", "ins-title");
  private readonly line = el("div", "ins-line");
  private readonly hullBar = el("i");
  private readonly more = el("div", "ins-more");
  private readonly record = el("p", "ins-fact");
  private rows: RowView[] = [];
  private ship = -1;
  private untilRefresh = 0;
  private readonly odds = new Float64Array(MAX_CHOICES);

  constructor(private readonly root: HTMLElement) {
    this.outputsBtn = el("button", "ins-outputs", "Details") as HTMLButtonElement;
    this.outputsBtn.setAttribute("type", "button");
    this.closeBtn = el("button", "ins-close", "✕") as HTMLButtonElement;
    this.closeBtn.setAttribute("type", "button");
    this.closeBtn.setAttribute("aria-label", "Stop inspecting this ship");
    const head = el("div", "ins-head");
    head.append(this.title, this.outputsBtn, this.closeBtn);
    const bar = el("span", "ins-hull");
    bar.append(this.hullBar);
    const status = el("div", "ins-status");
    status.append(bar, this.line);
    this.root.append(head, status, this.more);
  }

  /** Inspect ship `i`. `thrusters` and `turrets` are its hull's mount ids, in sim order. */
  open(match: LiveMatch, i: number, thrusters: string[], turrets: string[], entry: string): void {
    this.ship = i;
    this.untilRefresh = 0;
    const ship = match.ships[i]!;
    this.root.className = TEAM_CLASSES[ship.team]!;
    this.root.hidden = false;
    const strike = ship.role === "strike";
    this.more.replaceChildren(...(strike ? this.pilotFacts(match, i, entry) : this.scriptFacts()), this.record);
    const heads = match.pilot(i).policy.manifest.heads;
    this.buildRows(outputRows(heads, match.validHeads(i), thrusters, turrets), strike);
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

  /** Refresh the numbers, a few times a second. */
  update(match: LiveMatch, realDt: number): void {
    if (this.ship < 0) return;
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

  private pilotFacts(match: LiveMatch, i: number, entry: string): HTMLElement[] {
    const pilot = match.pilot(i);
    const m = pilot.policy.manifest;
    const info = pilot.entry;
    const shape = [m.layers[0]!.in, ...m.layers.map((l) => l.out)].join(" → ");
    const facts: HTMLElement[] = [];
    if (info?.note) facts.push(el("p", "ins-note", info.note));
    facts.push(el("p", "ins-fact", `Net: ${shape} · ${m.weights_floats.toLocaleString("en-GB")} weights`));
    if (info) {
      const rating = `${info.rating >= 0 ? "+" : ""}${Math.round(info.rating)}`;
      facts.push(el("p", "ins-fact", `Rated ${rating} · family ${info.family} · trained in sim ${info.sim_version}`));
    }
    facts.push(el("p", "ins-fact", this.followText(pilot.obsDim, info?.follows)));
    if (entry) {
      const p = el("p", "ins-fact");
      const a = el("a", "", "Meet the pilots →") as HTMLAnchorElement;
      a.href = `/notebook/#${encodeURIComponent(entry)}`;
      p.append(a);
      facts.push(p);
    }
    return facts;
  }

  private followText(obsDim: number, follows: { go_to?: number; attack?: number; defend?: number } | undefined): string {
    if (obsDim < ORDER_OBS_DIM) return "Orders: this net has no inputs for them.";
    if (!follows || follows.go_to === undefined) return "Orders: never drilled.";
    return `Order drills: go-to ${percent(follows.go_to)} · attack ${percent(follows.attack ?? 0)} · defend ${percent(follows.defend ?? 0)}`;
  }

  private scriptFacts(): HTMLElement[] {
    return [el("p", "ins-note", "No neural net here. Carriers and freighters are flown by a script in the sim, so each output below is a decision, not a set of odds.")];
  }

  private buildRows(rows: OutputRow[], strike: boolean): void {
    this.rows = [];
    for (const group of GROUPS) {
      const members = rows.filter((r) => r.kind === group.kind);
      if (!members.length) continue;
      const heading = el("p", "ins-group");
      heading.append(el("span", "", group.title), el("span", "ins-legend", strike ? group.legend : ""));
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
    const value = el("span", "ins-value");
    if (row.label) node.append(el("span", "ins-label", row.label));
    node.append(bar, value);
    this.rows.push({ row, segments, value, drawn: -1 });
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
    setText(this.record, `This match: ${plural(r.shots, "shot")} · ${plural(r.hits, "hit")} · ${Math.round(r.damage)} damage · ${plural(r.kills, "kill")}`);
    const w = match.watched;
    if (w.tick < 0 || match.watching !== i) return;
    const logits = match.watchedScripted ? null : w.logits;
    for (const view of this.rows) {
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

  /** Beside each bar: what the ship is doing with that output now. */
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
