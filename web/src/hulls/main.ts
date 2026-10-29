// The hull catalogue: one card per hull in assets/hulls/, from the JSON that
// tools/build_catalogue.py writes. Each card has a turning model, an actuator
// diagram, armour and impact rings, stats, and how the hull is flown.
import { mountNav } from "../shell/nav";
import { actuatorDiagram, multiplierRing } from "./diagram";
import { Turntable, TurntableError } from "./turntable";
import type { Arc, Catalogue, Hull, Weapon } from "./types";
import "./hulls.css";

mountNav("hulls");
const main = document.createElement("main");
main.className = "page hulls";
main.id = "main";
document.body.append(main);

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function n(v: number, digits = 0): string {
  return v.toLocaleString("en-GB", { maximumFractionDigits: digits });
}

function capitalise(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function header(onTeam: (team: number) => void): HTMLElement {
  const head = el("header", "hulls-head");
  head.append(
    el("p", "kicker", "Hull catalogue"),
    el("h1", "", "Three hulls, three ways to fly"),
    el(
      "p",
      "lede",
      "A learned pilot flies every ship by driving its thrusters, turrets and trigger directly. There is no autopilot to point the nose for it. These are the actuators it has to work with, read from each hull's YAML.",
    ),
  );
  const paint = el("div", "paint");
  paint.setAttribute("role", "group");
  paint.setAttribute("aria-label", "Paint the models in a team's colours");
  paint.append(el("span", "kicker", "Paint"));
  const buttons = [0, 1].map((team) => {
    const b = el("button", `paint__swatch paint__swatch--${team ? "b" : "a"}`, team ? "Orange" : "Blue");
    b.type = "button";
    b.setAttribute("aria-pressed", String(team === 0));
    b.addEventListener("click", () => {
      buttons.forEach((other, i) => other.setAttribute("aria-pressed", String(i === team)));
      onTeam(team);
    });
    return b;
  });
  paint.append(...buttons);
  head.append(paint);
  return head;
}

function stat(dl: HTMLElement, label: string, value: string, unit = ""): void {
  const div = el("div", "stat");
  const dd = el("dd", "stat__value", value);
  if (unit) dd.append(el("span", "stat__unit", ` ${unit}`));
  div.append(el("dt", "stat__label", label), dd);
  dl.append(div);
}

function arcList(arcs: Arc[]): string {
  return arcs.map((a) => `${a.name} ×${a.mult}`).join(" · ");
}

function ring(hull: Hull, arcs: Arc[], title: string, note: string): HTMLElement {
  const figure = el("figure", "figure ring-figure");
  figure.append(multiplierRing(hull, arcs, title));
  const caption = el("figcaption", "ring-figure__caption");
  caption.append(el("strong", "", title), el("span", "", note), el("span", "ring-figure__arcs", arcList(arcs)));
  figure.append(caption);
  return figure;
}

function weaponsTable(hull: Hull, weapons: Record<string, Weapon>): HTMLElement {
  const wrap = el("div", "table-scroll hull__table");
  const table = el("table");
  const head = el("tr");
  for (const [label, num] of [["mount", false], ["weapon", false], ["damage", true], ["range", true], ["rate", true], ["arc", true]] as const) {
    head.append(el("th", num ? "num" : "", label));
  }
  const thead = el("thead");
  thead.append(head);
  const tbody = el("tbody");
  for (const t of hull.turrets) {
    const w = weapons[t.weapon];
    const tr = el("tr");
    tr.append(el("td", "mono", t.id.replace(/^turret\./, "")));
    const kind = w && !w.kind_label.startsWith(t.weapon) ? ` (${w.kind_label})` : "";
    tr.append(el("td", "", `${t.weapon}${kind}`));
    tr.append(el("td", "num", w ? n(w.damage) : "–"));
    tr.append(el("td", "num", w ? `${n(w.range)} m` : "–"));
    tr.append(el("td", "num", w ? `${n(w.rate, 1)}/s` : "–"));
    tr.append(el("td", "num", t.arc_deg === 0 ? "fixed" : `${n(t.arc_deg)}° · ${n(t.slew_deg_s)}°/s`));
    tbody.append(tr);
  }
  table.append(thead, tbody);
  wrap.append(table);
  return wrap;
}

function thrusterTable(hull: Hull): HTMLElement {
  const wrap = el("div", "table-scroll hull__table");
  const table = el("table");
  const head = el("tr");
  for (const [label, num] of [["thruster", false], ["pushes", false], ["max force", true], ["at (x, y)", true]] as const) {
    head.append(el("th", num ? "num" : "", label));
  }
  const thead = el("thead");
  thead.append(head);
  const tbody = el("tbody");
  for (const t of hull.thrusters) {
    const [dx, dy] = t.dir;
    const pushes = dx > 0.5 ? "forward" : dx < -0.5 ? "back" : dy > 0.5 ? "to port" : dy < -0.5 ? "to starboard" : "at an angle";
    const tr = el("tr");
    tr.append(el("td", "mono", t.id.replace(/^thruster\./, "")));
    tr.append(el("td", "", pushes));
    tr.append(el("td", "num", `${n(t.max_force)} N`));
    tr.append(el("td", "num mono", `${n(t.pos[0], 1)}, ${n(t.pos[1], 1)}`));
    tbody.append(tr);
  }
  table.append(thead, tbody);
  wrap.append(table);
  return wrap;
}

function card(hull: Hull, weapons: Record<string, Weapon>): { node: HTMLElement; canvas: HTMLCanvasElement } {
  const article = el("article", "hull");
  article.id = hull.name;

  const stage = el("div", "hull__stage");
  const canvas = el("canvas", "hull__canvas");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", `3D model of the ${hull.name}, turning slowly`);
  const plate = el("div", "hull__plate");
  plate.append(el("p", "kicker", hull.role_label), el("h2", "hull__name", capitalise(hull.name)));
  stage.append(canvas, plate, el("span", "hull__cost", `cost ${n(hull.cost)}`));

  const story = el("div", "hull__story");
  if (hull.control_scheme) story.append(el("p", "hull__scheme", hull.control_scheme));
  const notes = el("div", "prose hull__notes");
  for (const s of hull.flying) notes.append(el("p", "", s));
  story.append(notes);

  const stats = el("dl", "stats");
  stat(stats, "Hull", n(hull.hp), "hp");
  stat(stats, "Shield", hull.shield ? n(hull.shield.hp) : "none", hull.shield ? "hp" : "");
  stat(stats, "Mass", n(hull.mass), "kg");
  stat(stats, "Speed cap", n(hull.speed_cap), "m/s");
  stat(stats, "Forward", n(hull.thrust.forward), "m/s²");
  stat(stats, "Sideways", n(hull.thrust.lateral), "m/s²");
  stat(stats, "Turn", n(hull.thrust.turn), "°/s²");
  stat(stats, "Inertia", n(hull.inertia), "kg·m²");
  story.append(stats);

  const tech = el("div", "hull__tech");
  const figure = el("figure", "figure diagram-figure");
  figure.append(el("h3", "figure__title", "Actuators, from above"), actuatorDiagram(hull));
  const legend = el("ul", "legend diagram-legend");
  const strongest = Math.max(...hull.thrusters.map((t) => t.max_force));
  const items: Array<[string, string]> = [
    ["key-thrust", `thruster: pushes at its mount, length ∝ force (longest ${n(strongest)} N)`],
    [hull.turrets.some((t) => t.arc_deg > 0) ? "key-arc" : "key-fixed", hull.turrets.some((t) => t.arc_deg > 0) ? "turret and its firing arc" : "fixed gun, fires along the nose"],
    ["key-footprint", "collision footprint"],
  ];
  if (hull.shield) items.push(["key-shield", `shield bubble, ${n(hull.shield.radius, 1)} m`]);
  for (const [key, text] of items) {
    const li = el("li");
    li.append(el("span", `diagram-key ${key}`), el("span", "", text));
    legend.append(li);
  }
  figure.append(legend);

  const rings = el("div", "rings");
  rings.append(
    ring(hull, hull.armour, "Armour", "weapon hits"),
    ring(hull, hull.impact, "Impact", "collisions"),
  );
  const ringNote = el("p", "figure__caption", "Brighter, thicker segments take more damage. Shields absorb first, so the multipliers apply to the hull only.");

  tech.append(figure, rings, ringNote);
  tech.append(el("h3", "hull__subhead", "Guns"), weaponsTable(hull, weapons));
  tech.append(el("h3", "hull__subhead", "Thrusters"), thrusterTable(hull));
  const source = el("a", "hull__source", `${hull.name}/hull.yaml`);
  source.href = hull.source;
  source.rel = "noopener";
  const sourceLine = el("p", "figure__caption");
  sourceLine.append("Source: ", source, ". Body frame: x forward, y to port, metres.");
  tech.append(sourceLine);

  const lead = el("div", "hull__lead");
  lead.append(stage, story);
  article.append(lead, tech);
  return { node: article, canvas };
}

async function start(): Promise<void> {
  let catalogue: Catalogue;
  try {
    const response = await fetch("/hulls/data/hulls.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`hulls.json: HTTP ${response.status}`);
    catalogue = (await response.json()) as Catalogue;
  } catch (error) {
    main.append(
      el("h1", "", "The hull data is missing"),
      el("p", "lede", `${(error as Error).message}. It is generated by scripts/build_pages_data.sh before the site is built.`),
    );
    return;
  }

  let turntable: Turntable | null = null;
  const cards = catalogue.hulls.map((hull) => card(hull, catalogue.weapons));
  main.append(header((team) => turntable?.setTeam(team)));
  const list = el("div", "hull-list");
  for (const c of cards) list.append(c.node);
  main.append(list);

  const foot = el("footer", "page-footer");
  foot.append(
    "Generated from ",
    Object.assign(el("a", "mono", "assets/hulls"), { href: "https://github.com/tcgarvin/rl-fighter/tree/main/assets/hulls" }),
    " by ",
    Object.assign(el("a", "mono", "tools/build_catalogue.py"), { href: "https://github.com/tcgarvin/rl-fighter/blob/main/tools/build_catalogue.py" }),
    ". The flagship, with turrets and launch bays, joins when the match structure does.",
  );
  main.append(foot);

  try {
    turntable = new Turntable();
    catalogue.hulls.forEach((hull, i) => {
      const c = cards[i];
      if (c) turntable?.add(hull, c.canvas);
    });
    turntable.start();
  } catch (error) {
    if (!(error instanceof TurntableError)) throw error;
    // The diagrams and stats still stand on their own; say why the models are missing.
    for (const c of cards) {
      const stage = c.canvas.parentElement;
      c.canvas.remove();
      stage?.classList.add("hull__stage--flat");
      stage?.append(el("p", "hull__no-gl", `3D view unavailable: ${error.message}`));
    }
  }
}

void start();
