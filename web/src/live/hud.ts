// The DOM layer over the canvas: the running tally, match status, the perf readout
// (sim + inference ms per tick against the 33 ms budget), the mission panel (carrier
// hull per side, or the convoy's progress, and which commander runs each side once the
// stable holds a learned one), the caption, the result banner with the
// reason the match ended and, behind the "Technical details" toggle, per-ship numbers next to each hull.
// The "Show commands" toggle's state lives on <body class="commands">.

import { JUMP_CHARGING, JUMP_DEPARTED, SIM_HZ, TICK_BUDGET_MS } from "./sim.ts";
import type { LiveMatch } from "./match.ts";
import { commanderName, type BundleManifest, type LiveCommander } from "./bundle.ts";
import { TEAM_CLASSES, TEAM_NAMES, TEAM_WORDS, escapeHtml, teamSpan } from "./teams.ts";

export { TEAM_CLASSES, TEAM_NAMES };
const PERF_INTERVAL = 0.25;
const TAG_OFFSET = 16;
const TAG_GAP = 2;

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

function throttleBar(t: Float32Array, n: number): string {
  return Array.from(t.subarray(0, n), (v) => (v > 0.66 ? "█" : v > 0.01 ? "▄" : "·")).join("");
}

export class Hud {
  readonly top = el("topbar");
  readonly bottom = el("bottom");
  private readonly tallyEl = el("tally");
  private readonly metaEl = el("meta");
  private readonly metaDetailsEl = el("meta-details");
  private readonly missionEl = el("mission");
  private readonly perfEl = el("perf");
  private readonly bannerEl = el("banner");
  private readonly captionEl = el("caption");
  private readonly tagsEl = el("tags");
  readonly detailsBtn = el<HTMLButtonElement>("details-toggle");
  readonly commandsBtn = el<HTMLButtonElement>("commands-toggle");
  private markers: Array<{ tag: HTMLElement; text: string }> = [];
  private missionHtml = "";
  private readonly jumpEl = (() => {
    const node = document.createElement("div");
    node.className = "jump-label";
    node.textContent = "JUMP POINT";
    node.hidden = true;
    el("hud").append(node);
    return node;
  })();
  private nextPerf = 0;
  private clock = 0;
  private fps = 60;

  setDetails(on: boolean): void {
    this.detailsBtn.setAttribute("aria-pressed", String(on));
    document.body.classList.toggle("details", on);
  }

  setCommands(on: boolean): void {
    this.commandsBtn.setAttribute("aria-pressed", String(on));
    this.commandsBtn.textContent = on ? "Hide commands" : "Show commands";
    document.body.classList.toggle("commands", on);
  }

  /** The convoy's "JUMP POINT" label under its marker (CSS px), or hidden (null). */
  placeJumpLabel(at: { x: number; y: number } | null): void {
    this.jumpEl.hidden = at === null;
    if (at) this.jumpEl.style.transform = `translate(${Math.round(at.x)}px, ${Math.round(at.y)}px)`;
  }

  /**
   * The caption under the battle; `replay` marks a past champion (?champion=),
   * `capitals` a match with scripted carriers or freighters in it, and `commanders`
   * each side's commander this match.
   */
  setCaption(manifest: BundleManifest, replay = false, capitals = false, commanders: readonly LiveCommander[] = []): void {
    const c = manifest.champion;
    const mixed = manifest.roster.hulls.length > 1 ? " One net flies every hull." : "";
    const craft = capitals ? "fighter" : "ship";
    const scripts = scriptsSentence(capitals, commanders);
    const nPilots = manifest.pilots?.length ?? 1;
    if (!replay && nPilots > 1) {
      const lead = `Each ${craft} here is flown by one of ${nPilots} neural networks, picked at random ship by ship, flying by thruster and trigger, trained overnight. Tap a ship to look closer. `;
      const entry = manifest.pilots_entry ? `#${encodeURIComponent(manifest.pilots_entry)}` : "";
      this.captionEl.innerHTML = lead + scripts + `<a href="/notebook/${entry}">Meet the pilots&nbsp;→</a>`;
      return;
    }
    const lead = replay
      ? `A past champion, ${escapeHtml(c.name)}: every ${craft} is flown by it.${mixed} <a href="/">Watch today's pilots&nbsp;→</a> `
      : `Every ${craft} here is the same neural network, flying by thruster and trigger, trained overnight.${mixed} `;
    this.captionEl.innerHTML = lead + scripts + `<a href="/notebook/#${encodeURIComponent(c.run)}">How this pilot learned&nbsp;→</a>`;
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

  /**
   * The mission panel under the status: carrier hull per side, or the convoy's
   * progress; and, with `commanders`, which commander runs each side.
   */
  updateMission(match: LiveMatch | null, commanders = false): void {
    const html = match ? missionPanel(match) + (commanders ? commanderRow(match) : "") : "";
    if (html === this.missionHtml) return;
    this.missionHtml = html;
    this.missionEl.innerHTML = html;
    this.missionEl.hidden = html === "";
  }

  showResult(match: LiveMatch): void {
    const [title, sub] = resultText(match);
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

  /** One (hidden) tag per ship of a new match. */
  resetMarkers(n: number): void {
    for (const m of this.markers) {
      m.tag.remove();
    }
    this.markers = Array.from({ length: n }, () => {
      const tag = document.createElement("div");
      tag.className = "tag";
      tag.hidden = true;
      this.tagsEl.append(tag);
      return { tag, text: "" };
    });
  }

  /**
   * With details on, place the per-ship tags. `onScreen(i)` is ship i's screen position and drawn
   * length (CSS px), or null; `thrusters[i]` its hull's thruster count.
   */
  updateMarkers(match: LiveMatch, details: boolean, onScreen: (i: number) => ShipOnScreen | null, thrusters: number[]): void {
    const placed: Rect[] = [];
    const pending: Array<{ tag: HTMLElement; x: number; y: number; w: number; h: number }> = [];
    match.ships.forEach((ship, i) => {
      const marker = this.markers[i];
      if (!marker) return;
      const at = details && ship.alive && ship.present ? onScreen(i) : null;
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

/** Which commander runs each side, one short line in the sides' colours. */
function commanderRow(match: LiveMatch): string {
  const side = (t: 0 | 1) => teamSpan(t, `${TEAM_NAMES[t]} ${escapeHtml(commanderName(match.commanders[t]))}`);
  return `<div class="mrow msub"><span class="mlabel">CMD</span>${side(0)} · ${side(1)}</div>`;
}

/** What the caption says is scripted, and which commander is a net. */
function scriptsSentence(capitals: boolean, commanders: readonly LiveCommander[]): string {
  const learned = [0, 1].filter((t) => commanders[t]?.net);
  if (learned.length === 0) return capitals ? "Carriers, freighters and both commanders are scripted. " : "";
  const who = learned.length === 2 ? "Both commanders are neural networks" : `The ${TEAM_WORDS[learned[0]!]} commander is a neural network`;
  const net = `${who} too, giving orders once a second.`;
  return capitals ? `Carriers and freighters are scripted. ${net} ` : `${net} `;
}

function pct(hp: number, max: number): number {
  return Math.round((100 * Math.max(0, hp)) / Math.max(1, max));
}

/** Each transport's state, in slot order: escaped, lost, charging or en route. */
function convoyPips(match: LiveMatch): string {
  return match.ships
    .filter((s) => s.role === "transport")
    .map((s) => {
      if (!s.alive) return '<i class="cv-lost" title="destroyed">✕</i>';
      if (s.jump === JUMP_DEPARTED) return '<i class="cv-out" title="through">◆</i>';
      if (s.jump === JUMP_CHARGING) return '<i class="cv-charge" title="charging">◈</i>';
      return '<i class="cv-go" title="en route">◇</i>';
    })
    .join("");
}

/** Metres from the freighter nearest the jump point (still en route) to the jump zone. */
function convoyDistance(match: LiveMatch): number | null {
  const c = match.convoy;
  if (!c) return null;
  let best: number | null = null;
  for (const s of match.ships) {
    if (s.role !== "transport" || !match.active(s)) continue;
    const d = Math.max(0, Math.hypot(c.jumpX - s.x, c.jumpY - s.y) - c.jumpRadius);
    if (best === null || d < best) best = d;
  }
  return best;
}

function missionPanel(match: LiveMatch): string {
  if (match.mission === "carrier_battle") {
    return [0, 1]
      .map((team) => {
        const t = match.teams[team]!;
        const p = t.carrier >= 0 ? pct(t.hp, t.maxHp) : 0;
        const hangar = t.hangar > 0 ? `${t.hangar} in hangar` : "hangar empty";
        return (
          `<div class="mrow ${TEAM_CLASSES[team]}${p === 0 ? " down" : ""}"><span class="mlabel">${TEAM_NAMES[team]} CARRIER</span>` +
          `<span class="mbar"><i style="width:${p}%"></i></span><span class="mval">${p}%</span><span class="mnote">${hangar}</span></div>`
        );
      })
      .join("");
  }
  const c = match.convoy;
  if (match.mission === "convoy_escort" && c) {
    // Each side's score against its own threshold: Azure escorts n through, Ember kills n.
    const left = convoyDistance(match);
    const dist = left === null || match.over ? "" : ` · ${left > 0 ? `${Math.round(left)} m to the jump` : "at the jump point"}`;
    return (
      `<div class="mrow"><span class="mlabel">${teamSpan(0, "CONVOY")}</span><span class="pips">${convoyPips(match)}</span>` +
      `<span class="mval">${teamSpan(0, `${c.escaped}/${c.toEscape} through`)}</span></div>` +
      `<div class="mrow msub">${teamSpan(1, `${TEAM_NAMES[1]} ${c.destroyed}/${c.toDestroy} kills`)}${dist}</div>`
    );
  }
  return "";
}

/** The result banner's title and reason line (HTML). */
export function resultText(match: LiveMatch): [string, string] {
  const w = match.winner;
  const reason = match.reason;
  const secs = `${(match.tick / SIM_HZ).toFixed(0)} s`;
  const c = match.convoy;
  const title = w === -1 ? "DRAW" : teamSpan(w, `${TEAM_NAMES[w]} WINS`);
  const word = (t: number) => teamSpan(t, TEAM_WORDS[t]!);
  switch (reason) {
    case "carrier":
      return [title, w === -1 ? `Both carriers destroyed · ${secs}` : `${word(1 - w)}'s carrier destroyed · ${secs}`];
    case "convoy_through":
      return [title, c ? `Convoy through — ${c.escaped} of ${c.total} escaped · ${secs}` : `Convoy through · ${secs}`];
    case "convoy_destroyed":
      return [title, c ? `Convoy destroyed — ${c.destroyed} of ${c.total} lost · ${secs}` : `Convoy destroyed · ${secs}`];
    case "mutual":
      return [title, `Both fleets destroyed · ${secs}`];
    case "eliminated": {
      if (c && w === 0) return [title, `Every attacker destroyed · ${c.escaped} of ${c.total} through`];
      const left = match.ships.filter((s) => match.inMatch(s)).length;
      return [title, `Last team standing · ${left} ship${left === 1 ? "" : "s"} left · ${secs}`];
    }
    case "time": {
      if (c) return [title, `Time limit — the convoy didn't get through · ${c.escaped} of ${c.total} escaped`];
      if (match.mission === "carrier_battle") {
        const [a, b] = match.teams.map((t) => pct(t.hp, t.maxHp));
        if (a !== b) return [title, `Time limit — carriers at ${teamSpan(0, `${a}%`)} and ${teamSpan(1, `${b}%`)}`];
      }
      if (w === -1) return [title, "Time limit — even on hull"];
      const [a, b] = match.teamValues().map((v) => Math.round(v));
      return [title, `Time limit — ahead on hull · ${teamSpan(0, String(a))} to ${teamSpan(1, String(b))}`];
    }
  }
}
