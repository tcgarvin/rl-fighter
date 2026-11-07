// The command log behind "show commands": an ambient computer readout of what each
// side's commander does (launches, squad orders) and what the convoy's jump drives do,
// fed from the sim's events, which it raises alike for a scripted commander and for the
// decisions a learned one submits. Collapsed it is a few faint lines, not meant to be read
// in passing; a tap opens it into a readable panel, and another tap closes it.

import { commanderName } from "./bundle.ts";
import type { LiveMatch } from "./match.ts";
import { MISSION_TITLES, type MissionName } from "./missions.ts";
import { ORDER_KINDS, SIM_HZ, type SimEvent } from "./sim.ts";
import { TEAM_CLASSES, TEAM_NAMES, escapeHtml } from "./teams.ts";

// Enough to scroll back through a whole carrier battle's orders; older lines drop.
const MAX_LINES = 90;

export class CommandLog {
  private readonly root: HTMLElement;
  private readonly list: HTMLElement;
  private open = false;
  private bays: (hull: string) => string[];

  /** `bays(hull)` names a carrier hull's bays in sim order ("port", "starboard"). */
  constructor(root: HTMLElement, bays: (hull: string) => string[]) {
    this.root = root;
    this.bays = bays;
    this.list = document.createElement("div");
    this.list.className = "cl-lines";
    root.append(this.list);
    root.setAttribute("role", "log");
    root.tabIndex = 0;
    root.setAttribute("aria-label", "Command log (tap to expand)");
    root.setAttribute("aria-expanded", "false");
    const toggle = (e: Event) => {
      e.preventDefault();
      this.setOpen(!this.open);
    };
    root.addEventListener("click", toggle);
    root.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") toggle(e);
      else if (e.key === "Escape") this.setOpen(false);
    });
  }

  setBays(bays: (hull: string) => string[]): void {
    this.bays = bays;
  }

  setOpen(on: boolean): void {
    this.open = on;
    this.root.classList.toggle("open", on);
    this.root.setAttribute("aria-expanded", String(on));
    if (on) this.list.scrollTop = this.list.scrollHeight;
  }

  /** A separator and the opening lines for a new match. */
  newMatch(number: number, m: LiveMatch): void {
    this.line(-1, `── MATCH ${String(number).padStart(2, "0")} · ${MISSION_TITLES[m.mission as MissionName].toUpperCase()} ──`, "cl-sep");
    // Who is in command, once a learned commander is on the field.
    if (m.commanders.some((c) => c.net)) {
      for (const team of [0, 1] as const) {
        const c = m.commanders[team];
        this.line(team, `${this.who(team)} › ${commanderName(c)} in command${c.net ? "{ · neural net, decides each second}" : ""}`, "", 0);
      }
    }
    if (m.convoy) {
      const c = m.convoy;
      this.line(0, `${this.who(0)} › convoy under way · ${c.total} freighters → jump point{ ${fmtPoint(c.jumpX, c.jumpY)}}`, "", 0);
    }
    for (const team of [0, 1] as const) {
      const t = m.teams[team];
      if (t.carrier < 0) continue;
      const inSpace = m.ships.filter((s) => s.team === team && s.role === "strike" && !s.docked).length;
      this.line(team, `${this.who(team)} › carrier under way · ${inSpace} jumping in, ${t.hangar} in the hangar`, "", 0);
    }
  }

  /** Log the commander and jump events of the step just taken. */
  ingest(m: LiveMatch): void {
    for (const e of m.events) {
      const text = this.describe(m, e);
      if (text) this.line(text[0], text[1], text[2] ?? "", m.tick);
    }
  }

  private who(team: number): string {
    return `${TEAM_NAMES[team]} CMD`;
  }

  private describe(m: LiveMatch, e: SimEvent): [number, string, string?] | null {
    switch (e.kind) {
      case "launch": {
        const ship = m.ships[e.a];
        if (!ship) return null;
        const bay = this.bays(m.hullNames[e.b] ?? "")[e.extra] ?? `bay ${e.extra}`;
        return [ship.team, `${this.who(ship.team)} › launch ${m.labels[e.a]} · bay ${bay}`];
      }
      case "order": {
        const team = e.a;
        const kind = ORDER_KINDS[e.extra] ?? "none";
        const sq = m.squads.find((s) => s.team === team && s.index === e.b);
        const size = sq && sq.members > 0 ? `{ ×${sq.members}}` : "";
        const head = `${this.who(team)} › squad ${e.b + 1}${size}`;
        const target = e.f5 >= 0 ? (m.labels[e.f5] ?? `ship ${e.f5}`) : "";
        if (kind === "attack") return [team, `${head} · attack → ${target}`];
        if (kind === "defend") return [team, `${head} · defend → ${target}`];
        if (kind === "goto") return [team, `${head} · go to{ ${fmtPoint(e.x, e.y)} r${Math.round(e.f6)}}`];
        return [team, `${head} · stand down`];
      }
      case "jumpCharge": {
        const ship = m.ships[e.a];
        if (!ship) return null;
        return [ship.team, `${TEAM_NAMES[ship.team]} NAV › ${m.labels[e.a]} · jump drive spooling`];
      }
      case "jumpOut": {
        const ship = m.ships[e.a];
        if (!ship) return null;
        const c = m.convoy;
        const tally = c ? ` (${c.escaped}/${c.total} through)` : "";
        return [ship.team, `${TEAM_NAMES[ship.team]} NAV › ${m.labels[e.a]} · jumped out${tally}`, "cl-hi"];
      }
      case "death": {
        const ship = m.ships[e.a];
        if (!ship || ship.role === "strike") return null;
        return [ship.team, `${TEAM_NAMES[ship.team]} › ${m.labels[e.a]} destroyed`, "cl-hi"];
      }
      case "matchEnd":
        return [-1, `END › ${m.simReason.replace(/_/g, " ")}${e.a >= 0 ? ` · ${TEAM_NAMES[e.a]} wins` : " · draw"}`, "cl-sep"];
      default:
        return null;
    }
  }

  private line(team: number, text: string, cls = "", tick?: number): void {
    const row = document.createElement("div");
    row.className = `cl-line ${team >= 0 ? TEAM_CLASSES[team] : ""} ${cls}`;
    const t = tick === undefined ? "" : `<span class="cl-t">T+${String(Math.floor(tick / SIM_HZ)).padStart(3, "0")}</span> `;
    // "{…}" marks detail shown only in the open panel; the team and layer lead in bold.
    row.innerHTML =
      t +
      escapeHtml(text)
        .replace(/^([A-Z]+(?: [A-Z]+)?) ›/, "<b>$1</b> ›")
        .replace(/\{([^}]*)\}/g, '<span class="cl-d">$1</span>');
    this.list.append(row);
    while (this.list.childElementCount > MAX_LINES) this.list.firstElementChild!.remove();
    if (this.open) this.list.scrollTop = this.list.scrollHeight;
  }
}

function fmtPoint(x: number, y: number): string {
  return `(${Math.round(x)}, ${Math.round(y)})`;
}
