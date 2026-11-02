// Who beats whom (lab/runs/*/matchups.json, tools/live_pilots.py): a grid of how often the
// row's pilot beat the column's, one mode at a time. Pilots stay in overall rating order in
// every mode, so a mode where the ladder breaks shows blue below the diagonal.
import type { Matchups } from "./types";

const MODES: Array<[string, string, string]> = [
  ["overall", "Overall", "all three missions together"],
  ["deathmatch", "Deathmatch", "team deathmatch"],
  ["carrier_battle", "Carrier", "carrier battle"],
  ["convoy_escort", "Convoy", "convoy escort"],
];
// The strongest tint; beyond this white-ish text loses its 4.5:1 on the colour.
const MAX_MIX = 45;
// A result this far from even takes the strongest tint.
const FULL_MARGIN = 0.45;

function make<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

/** A diverging tint: blue for a winning record, orange for a losing one, grey at even. */
function tint(win: number): string {
  const mix = Math.round((Math.min(1, Math.abs(win - 0.5) / FULL_MARGIN)) * MAX_MIX);
  return `color-mix(in srgb, var(--${win >= 0.5 ? "team-a" : "team-b"}) ${mix}%, var(--bg-raised))`;
}

function table(data: Matchups, mode: string, modeWords: string): HTMLElement {
  const rows = data.modes[mode];
  if (!rows) throw new Error(`matchups: no mode ${mode}`);
  const n = data.n_per_mission * (mode === "overall" ? MODES.length - 1 : 1);
  const grid = make("table", "nb-matchups__grid");
  const head = make("tr");
  head.append(make("th", "nb-matchups__corner", "beat →"));
  data.pilots.forEach((p, j) => {
    const th = make("th", "", String(j + 1));
    th.title = p.id;
    th.scope = "col";
    head.append(th);
  });
  const thead = make("thead");
  thead.append(head);
  const tbody = make("tbody");
  rows.forEach((row, i) => {
    const pilot = data.pilots[i]!;
    const tr = make("tr");
    const th = make("th", "nb-matchups__who");
    th.scope = "row";
    th.append(make("span", "nb-matchups__rank", String(i + 1)), document.createTextNode(pilot.id));
    tr.append(th);
    row.forEach((win, j) => {
      const td = make("td");
      if (win === null) {
        td.className = "nb-matchups__self";
      } else {
        td.textContent = String(Math.round(win * 100));
        td.style.background = tint(win);
        td.title = `${pilot.id} beat ${data.pilots[j]!.id} in ${Math.round(win * 100)}% of ${n} matches of ${modeWords}`;
      }
      tr.append(td);
    });
    tbody.append(tr);
  });
  grid.append(thead, tbody);
  return grid;
}

/** The figure: a mode switch above the grid, a key and a caption below it. */
export function matchupGrid(data: Matchups): HTMLElement {
  const figure = make("figure", "wide nb-matchups");
  const switcher = make("div", "nb-matchups__modes");
  switcher.setAttribute("role", "group");
  switcher.setAttribute("aria-label", "Which mission");
  const holder = make("div", "nb-matchups__holder");
  const buttons = MODES.map(([mode, label, words]) => {
    const button = make("button", "", label);
    button.type = "button";
    button.addEventListener("click", () => show(mode, words, button));
    switcher.append(button);
    return button;
  });
  function show(mode: string, words: string, active: HTMLButtonElement): void {
    for (const b of buttons) b.setAttribute("aria-pressed", String(b === active));
    holder.replaceChildren(table(data, mode, words));
  }
  show(MODES[0]![0], MODES[0]![2], buttons[0]!);
  const key = make("p", "nb-matchups__key");
  const swatch = make("span", "nb-matchups__ramp");
  key.append(make("span", "", "Row loses"), swatch, make("span", "", "Row wins"));
  const caption = make(
    "figcaption",
    "figure__caption",
    `Each number is how often the row's pilot beat the column's, in percent. Pilots keep their overall rating order in every mission. ${data.n_per_mission} matches per pair per mission, so a single mission's number is good to about ±6 points.`,
  );
  figure.append(switcher, holder, key, caption);
  return figure;
}
