// The DOM layer over the canvas: the running tally, match status, the perf readout
// (sim + inference ms per tick against the 33 ms budget), the caption, the result
// banner, a faint team ring round any hull drawn too small to read and, behind the
// "Technical details" toggle, per-ship numbers next to each hull.

import { SIM_HZ, TICK_BUDGET_MS } from "./sim.ts";
import type { EndReason, LiveMatch } from "./match.ts";
import type { BundleManifest } from "./bundle.ts";

export const TEAM_NAMES = ["AZURE", "EMBER"] as const;
export const TEAM_CLASSES = ["team-a", "team-b"] as const;
const PERF_INTERVAL = 0.25;
const TAG_OFFSET = 16;
const TAG_GAP = 2;
// Pips fade in as a hull's drawn length drops from PIP_FADE_PX to PIP_FADE_PX - PIP_FADE_SPAN.
const PIP_FADE_PX = 22;
const PIP_FADE_SPAN = 10;
const PIP_MAX_ALPHA = 0.7;

/** A ship's screen position and drawn length, CSS px. */
export interface ShipOnScreen {
  x: number;
  y: number;
  sizePx: number;
}

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Tally {
  wins: [number, number];
  draws: number;
}

function el<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`live page markup is missing #${id}`);
  return node as T;
}

function teamSpan(team: number, text: string): string {
  return `<span class="${TEAM_CLASSES[team]}">${text}</span>`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

function throttleBar(t: Float32Array, n: number): string {
  return Array.from(t.subarray(0, n), (v) => (v > 0.66 ? "█" : v > 0.01 ? "▄" : "·")).join("");
}

export class Hud {
  readonly top = el("topbar");
  readonly bottom = el("bottom");
  private readonly tallyEl = el("tally");
  private readonly metaEl = el("meta");
  private readonly metaDetailsEl = el("meta-details");
  private readonly perfEl = el("perf");
  private readonly bannerEl = el("banner");
  private readonly captionEl = el("caption");
  private readonly tagsEl = el("tags");
  readonly detailsBtn = el<HTMLButtonElement>("details-toggle");
  private markers: Array<{ tag: HTMLElement; pip: HTMLElement; text: string }> = [];
  private nextPerf = 0;
  private clock = 0;
  private fps = 60;

  setDetails(on: boolean): void {
    this.detailsBtn.setAttribute("aria-pressed", String(on));
    document.body.classList.toggle("details", on);
  }

  setCaption(manifest: BundleManifest): void {
    const c = manifest.champion;
    const mixed = manifest.roster.hulls.length > 1 ? " One net flies every hull." : "";
    this.captionEl.innerHTML =
      `Every ship here is the same neural network, flying by thruster and trigger, trained overnight.${mixed} ` +
      `<a href="/notebook/#${encodeURIComponent(c.run)}">How this pilot learned&nbsp;→</a>`;
  }

  setTally(t: Tally): void {
    const draws = t.draws ? ` <span class="draws">· ${t.draws} drawn</span>` : "";
    this.tallyEl.innerHTML = `${teamSpan(0, `${TEAM_NAMES[0]} ${t.wins[0]}`)} <span class="dash">–</span> ${teamSpan(1, `${t.wins[1]} ${TEAM_NAMES[1]}`)}${draws}`;
  }

  /** The status line, and the details-only line under it. */
  setMeta(text: string, details: string): void {
    if (this.metaEl.textContent !== text) this.metaEl.textContent = text;
    if (this.metaDetailsEl.textContent !== details) this.metaDetailsEl.textContent = details;
  }

  fail(message: string): void {
    this.metaEl.textContent = message;
    this.metaEl.classList.add("error");
  }

  showResult(match: LiveMatch): void {
    const w = match.winner;
    const reason: EndReason = match.reason;
    const secs = `${(match.tick / SIM_HZ).toFixed(0)} s`;
    let title: string;
    let sub: string;
    if (w === -1) {
      title = "DRAW";
      sub = reason === "mutual" ? `both fleets destroyed · ${secs}` : "even on hull at the time limit";
    } else {
      title = teamSpan(w, `${TEAM_NAMES[w]} WINS`);
      if (reason === "time") {
        const [a, b] = match.teamValues().map((v) => Math.round(v));
        sub = `on hull at the time limit · ${teamSpan(0, String(a))} to ${teamSpan(1, String(b))}`;
      } else {
        const left = match.ships.filter((s) => s.alive).length;
        sub = `last team standing · ${left} ship${left === 1 ? "" : "s"} left · ${secs}`;
      }
    }
    this.bannerEl.innerHTML = `<div class="title">${title}</div><div class="sub">${sub}</div>`;
    this.bannerEl.classList.add("show");
  }

  hideResult(): void {
    this.bannerEl.classList.remove("show");
  }

  /** Smooth the frame rate and, a few times a second, refresh the perf readout. */
  updatePerf(dt: number, realDt: number, match: LiveMatch | null, details: boolean): void {
    this.clock += dt;
    if (realDt > 0) this.fps += (1 / realDt - this.fps) * Math.min(1, realDt * 2);
    if (this.clock < this.nextPerf) return;
    this.nextPerf = this.clock + PERF_INTERVAL;
    const sim = match?.timing.sim ?? 0;
    const nn = match?.timing.nn ?? 0;
    const tick = sim + nn;
    const free = Math.max(0, 100 * (1 - tick / TICK_BUDGET_MS));
    const split = details ? `\nsim ${sim.toFixed(2)} · nn ${nn.toFixed(2)}` : "";
    this.perfEl.textContent = `tick ${tick.toFixed(1)} / ${TICK_BUDGET_MS.toFixed(0)} ms\n${free.toFixed(0)}% free · ${this.fps.toFixed(0)} fps${split}`;
  }

  /** One (hidden) tag and pip per ship of a new match. */
  resetMarkers(n: number): void {
    for (const m of this.markers) {
      m.tag.remove();
      m.pip.remove();
    }
    this.markers = Array.from({ length: n }, () => {
      const tag = document.createElement("div");
      tag.className = "tag";
      tag.hidden = true;
      const pip = document.createElement("div");
      pip.className = "pip";
      pip.hidden = true;
      this.tagsEl.append(pip, tag);
      return { tag, pip, text: "" };
    });
  }

  /**
   * Place the pips (a faint team ring round a hull drawn too small to read) and, with
   * details on, the per-ship tags. `onScreen(i)` is ship i's screen position and drawn
   * length (CSS px), or null; `thrusters[i]` its hull's thruster count.
   */
  updateMarkers(match: LiveMatch, details: boolean, onScreen: (i: number) => ShipOnScreen | null, thrusters: number[]): void {
    const placed: Rect[] = [];
    const pending: Array<{ tag: HTMLElement; x: number; y: number; w: number; h: number }> = [];
    match.ships.forEach((ship, i) => {
      const marker = this.markers[i];
      if (!marker) return;
      const at = ship.alive && ship.present ? onScreen(i) : null;
      const pipAlpha = at ? Math.min(PIP_MAX_ALPHA, Math.max(0, (PIP_FADE_PX - at.sizePx) / PIP_FADE_SPAN)) : 0;
      marker.pip.hidden = pipAlpha <= 0.02;
      if (at && !marker.pip.hidden) {
        marker.pip.className = `pip ${TEAM_CLASSES[ship.team]}`;
        marker.pip.style.opacity = pipAlpha.toFixed(2);
        marker.pip.style.transform = `translate(${Math.round(at.x)}px, ${Math.round(at.y)}px)`;
      }
      if (!details || !at) {
        marker.tag.hidden = true;
        return;
      }
      marker.tag.hidden = false;
      const text = this.tagText(match, i, thrusters[i] ?? 0);
      if (marker.text !== text) {
        marker.tag.innerHTML = text;
        marker.text = text;
        marker.tag.className = `tag ${TEAM_CLASSES[ship.team]}`;
      }
      pending.push({ tag: marker.tag, x: at.x, y: at.y, w: marker.tag.offsetWidth || 80, h: marker.tag.offsetHeight || 24 });
    });
    // Below-right of each ship, flipped left near the right edge; tags that would
    // overlap one already placed slide down past it.
    const width = window.innerWidth;
    pending.sort((a, b) => a.y - b.y);
    for (const p of pending) {
      const x = Math.max(4, p.x + TAG_OFFSET + p.w > width - 8 ? p.x - TAG_OFFSET - p.w : p.x + TAG_OFFSET);
      let y = p.y + 6;
      for (let pass = 0; pass < placed.length; pass++) {
        const hit = placed.find((r) => x < r.x + r.w && r.x < x + p.w && y < r.y + r.h && r.y < y + p.h);
        if (!hit) break;
        y = hit.y + hit.h + TAG_GAP;
      }
      placed.push({ x, y, w: p.w, h: p.h });
      p.tag.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    }
  }

  private tagText(match: LiveMatch, i: number, thrusters: number): string {
    const ship = match.ships[i]!;
    const name = escapeHtml(match.hullNames[i]!.toUpperCase());
    const shield = ship.shield > 0 ? ` ◇${Math.ceil(ship.shield)}` : "";
    const pct = (k: number) => Math.round((ship.power[k] ?? 0) * 100);
    return (
      `${teamSpan(ship.team, name)} <span class="hp">${Math.ceil(Math.max(0, ship.hp))}/${match.maxHp[i]}${shield}</span>` +
      `<span class="stats">${throttleBar(ship.throttles, thrusters)} S${pct(0)} E${pct(1)} W${pct(2)}</span>`
    );
  }
}
