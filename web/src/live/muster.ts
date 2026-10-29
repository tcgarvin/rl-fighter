// The muster (DESIGN §6 phase 1): both rosters as cards with the real hull thumbnails,
// the team colours and a one-line matchup, for a few seconds before the jump-in. A tap
// anywhere skips it. In portrait EMBER's side is on top, because the camera turns so
// that team 1 arrives at the top of the screen.

import { TEAM_CLASSES, TEAM_NAMES } from "./hud.ts";
import { matchupLine, type Roster } from "./roster.ts";
import type { HullInfo } from "./sim.ts";

// Short enough for four cards across a phone.
const ROLE_LINES: Record<string, string> = {
  fighter: "fast · gun",
  skirmisher: "agile · beam",
  anchor: "slow · 3 turrets",
};
// Leaves time for the fade-out before the fleets jump.
const FADE_OUT = 0.35;

export interface MusterOptions {
  number: number;
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
      `<div class="kicker">Match ${String(o.number).padStart(2, "0")} · Muster</div>` +
        `<div class="m-matchup">${matchupLine(o.roster)}</div>` +
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
      cards.style.setProperty("--n", String(fleet.length));
      fleet.forEach((hull, k) => cards.append(this.card(hull, team, k, o)));
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

  private card(hull: string, team: 0 | 1, k: number, o: MusterOptions): HTMLElement {
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
      el("div", "m-name", hull.toUpperCase()),
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
