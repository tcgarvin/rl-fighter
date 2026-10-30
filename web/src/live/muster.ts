// The muster (DESIGN §6 phase 1): the mission and its brief, both rosters as cards with
// the real hull thumbnails, the team colours and a one-line matchup, for a few seconds
// before the jump-in. A tap anywhere skips it. In portrait EMBER's side is on top,
// because the camera turns so that team 1 arrives at the top of the screen (in a
// convoy escort it comes in from the side, and the convoy runs up the screen).
// Fleets of more than MAX_CARDS show one card per hull with a count.

import { TEAM_CLASSES, TEAM_NAMES } from "./teams.ts";
import { MISSION_TITLES, type Brief, type MissionName } from "./missions.ts";
import { matchupLine, type Roster } from "./roster.ts";
import type { HullInfo } from "./sim.ts";

// Short enough for four cards across a phone.
const ROLE_LINES: Record<string, string> = {
  fighter: "fast · gun",
  skirmisher: "agile · beam",
  anchor: "slow · 3 turrets",
  carrier: "launches the wing",
  transport: "unarmed · cargo",
};
const MAX_CARDS = 4;
// Leaves time for the fade-out before the fleets jump.
const FADE_OUT = 0.35;

export interface MusterOptions {
  number: number;
  mission: MissionName;
  /** The objective and brief (HTML), missions.ts missionBrief(). */
  brief: Brief;
  roster: Roster;
  info: Record<string, HullInfo>;
  thumbnails: Record<string, [string, string]>;
  duration: number;
}

function el(tag: string, className: string, html?: string): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}

const CAPITAL_FIRST: Record<string, number> = { carrier: 0, transport: 1 };

/** One [hull, count] per hull kind, capital ships first, then by count. */
function grouped(fleet: string[], info: Record<string, HullInfo>): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const h of fleet) counts.set(h, (counts.get(h) ?? 0) + 1);
  const rank = (h: string) => CAPITAL_FIRST[info[h]?.role ?? ""] ?? 2;
  return [...counts].sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1] || a[0].localeCompare(b[0]));
}

export class Muster {
  private readonly root: HTMLElement;
  private bar: HTMLElement | null = null;
  private duration = 1;
  private skipped = false;
  private endAt = Infinity;

  constructor(root: HTMLElement) {
    this.root = root;
    root.addEventListener("pointerdown", (e) => {
      // A tap (or click) anywhere on the muster starts the match early.
      e.preventDefault();
      this.skipped = true;
    });
  }

  show(o: MusterOptions): void {
    this.skipped = false;
    this.endAt = Infinity;
    this.duration = o.duration;
    const root = this.root;
    root.innerHTML = "";
    root.style.setProperty("--muster-duration", `${o.duration}s`);
    const head = el(
      "div",
      "m-head",
      `<div class="kicker">Match ${String(o.number).padStart(2, "0")} · ${MISSION_TITLES[o.mission]}</div>` +
        `<div class="m-matchup">${o.brief.headline ?? matchupLine(o.roster, o.info)}</div>` +
        `<div class="m-brief">${o.brief.brief}</div>` +
        (o.roster.budget !== null ? `<div class="m-budget">${o.roster.budget} credits a side</div>` : ""),
    );
    const sides = el("div", "m-sides");
    for (const team of [0, 1] as const) {
      const fleet = o.roster.fleets[team];
      const side = el("div", `m-side ${TEAM_CLASSES[team]} m-side-${team}`);
      const spent = fleet.reduce((sum, h) => sum + (o.info[h]?.cost ?? 0), 0);
      side.append(
        el("div", "m-side-head", `<span class="m-team">${team === 0 ? "▲" : "■"} ${TEAM_NAMES[team]}</span><span class="m-count">${fleet.length} ship${fleet.length === 1 ? "" : "s"} · ${spent} cr</span>`),
      );
      const cards = el("div", "m-cards");
      const groups = fleet.length > MAX_CARDS ? grouped(fleet, o.info) : fleet.map((h) => [h, 1] as [string, number]);
      cards.style.setProperty("--n", String(groups.length));
      groups.forEach(([hull, n], k) => cards.append(this.card(hull, n, team, k, o)));
      side.append(cards);
      sides.append(side);
    }
    sides.insertBefore(el("div", "m-vs", "VS"), sides.lastChild);
    const foot = el("div", "m-foot", `<div class="m-bar"><i></i></div><button type="button" class="m-skip">Tap to start</button>`);
    root.append(head, sides, foot);
    this.bar = foot.querySelector(".m-bar i");
    root.hidden = false;
    root.classList.remove("leaving");
    // Restart the CSS animations for the new cards.
    void root.offsetWidth;
    root.classList.add("on");
  }

  private card(hull: string, count: number, team: 0 | 1, k: number, o: MusterOptions): HTMLElement {
    const info = o.info[hull];
    const node = el("div", "m-card");
    node.style.animationDelay = `${0.15 + k * 0.09 + team * 0.05}s`;
    const img = document.createElement("img");
    const thumbs = o.thumbnails[hull];
    if (thumbs) img.src = thumbs[team];
    img.alt = "";
    const stats = info ? `${info.hp.toFixed(0)} hp${info.shield ? ` · ${info.shield.toFixed(0)} sh` : ""}` : "";
    node.append(
      img,
      el("div", "m-name", hull.toUpperCase() + (count > 1 ? ` <span class="m-x">×${count}</span>` : "")),
      el("div", "m-role", ROLE_LINES[info?.role ?? ""] ?? info?.role ?? ""),
      el("div", "m-stats", stats),
    );
    return node;
  }

  /** Advance the countdown; true once the muster is over (time up, or tapped and faded). */
  update(t: number): boolean {
    if (this.skipped && this.endAt > t + FADE_OUT) this.endAt = t + FADE_OUT;
    const end = Math.min(this.endAt, this.duration);
    if (this.bar) this.bar.style.transform = `scaleX(${Math.min(1, t / this.duration)})`;
    if (t >= end - FADE_OUT) this.root.classList.add("leaving");
    return t >= end;
  }

  hide(): void {
    this.root.hidden = true;
    this.root.classList.remove("on", "leaving");
    this.root.innerHTML = "";
    this.bar = null;
  }
}
