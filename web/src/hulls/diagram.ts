// Top-down actuator diagrams in the body frame (SIM_SPEC §4.1), drawn as SVG.
// The nose points up and port is to the left, as if looking down on the ship.
import type { Arc, Hull, Vec2 } from "./types";

const SVG_NS = "http://www.w3.org/2000/svg";
const WIDTH = 340;
const HEIGHT = 300;
const PAD_PX = 18;
const ARROW_HEAD = 5;

type Attrs = Record<string, string | number>;

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Attrs = {}, parent?: Element): SVGElementTagNameMap[K] {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  parent?.append(node);
  return node;
}

/** Body-frame point (m) to the diagram's "screen" metres: nose up, port left. */
function screen([x, y]: Vec2): Vec2 {
  return [-y, -x];
}

/** Unit vector on screen for a body-frame bearing in degrees. */
function bearing(deg: number): Vec2 {
  const r = (deg * Math.PI) / 180;
  return [-Math.sin(r), -Math.cos(r)];
}

function add(a: Vec2, b: Vec2, s = 1): Vec2 {
  return [a[0] + b[0] * s, a[1] + b[1] * s];
}

/** Length of a thruster's arrow in metres: proportional to its force. */
function arrowLength(hull: Hull, force: number): number {
  const strongest = Math.max(...hull.thrusters.map((t) => t.max_force));
  const longest = Math.max(5, hull.bound_radius * 0.9);
  return (force / strongest) * longest;
}

function turretReach(hull: Hull): number {
  return Math.max(4.5, hull.bound_radius * 0.95);
}

/** Every point the diagram draws, in screen metres, so it can be framed. */
function extents(hull: Hull): Vec2[] {
  const pts: Vec2[] = [];
  const reach = turretReach(hull);
  for (const c of hull.collision) {
    const p = screen(c.pos);
    pts.push(add(p, [c.r, c.r]), add(p, [-c.r, -c.r]));
  }
  if (hull.shield) pts.push([hull.shield.radius, hull.shield.radius], [-hull.shield.radius, -hull.shield.radius]);
  for (const t of hull.thrusters) {
    const p = screen(t.pos);
    pts.push(p, add(p, screen(t.dir), -arrowLength(hull, t.max_force)));
  }
  for (const t of hull.turrets) {
    const p = screen(t.pos);
    const span = t.arc_deg === 0 ? 0 : t.arc_deg / 2;
    for (let d = -span; d <= span; d += Math.max(5, span / 8 || 5)) {
      pts.push(add(p, bearing(t.rest_deg + d), t.arc_deg === 0 ? reach * 1.25 : reach));
    }
    pts.push(add(p, bearing(t.rest_deg + span), reach));
  }
  return pts;
}

function arcPath(centre: Vec2, r: number, fromDeg: number, toDeg: number): string {
  const a = add(centre, bearing(fromDeg), r);
  const b = add(centre, bearing(toDeg), r);
  const large = toDeg - fromDeg > 180 ? 1 : 0;
  // Bearings grow counter-clockwise on screen, which is SVG's sweep-flag 0.
  return `M${a[0].toFixed(2)},${a[1].toFixed(2)}A${r},${r} 0 ${large} 0 ${b[0].toFixed(2)},${b[1].toFixed(2)}`;
}

/**
 * The main actuator diagram: footprint circles, shield, thrusters as arrows that
 * push at their mount (length ∝ max force), and turrets with their firing arcs.
 */
export function actuatorDiagram(hull: Hull): SVGSVGElement {
  const pts = extents(hull);
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const k = Math.min((WIDTH - 2 * PAD_PX) / (x1 - x0), (HEIGHT - 2 * PAD_PX - 14) / (y1 - y0));
  const ox = WIDTH / 2 - ((x0 + x1) / 2) * k;
  const oy = (HEIGHT - 14) / 2 - ((y0 + y1) / 2) * k + 6;
  const px = (p: Vec2): Vec2 => [ox + p[0] * k, oy + p[1] * k];
  const P = (body: Vec2) => px(screen(body));

  const root = svg("svg", { viewBox: `0 0 ${WIDTH} ${HEIGHT}`, class: "diagram", role: "img" });
  root.setAttribute("aria-label", `${hull.name}: thrusters, turrets and footprint, seen from above, nose up`);

  // Nose marker and a 5 m scale bar so the drawing has units.
  const top = svg("text", { x: WIDTH / 2, y: 12, class: "diagram__label", "text-anchor": "middle" }, root);
  top.textContent = "nose ▲";
  const bar = 5 * k;
  const by = HEIGHT - 10;
  svg("path", { d: `M10,${by - 4}V${by}H${10 + bar}V${by - 4}`, class: "diagram__scale" }, root);
  const scaleLabel = svg("text", { x: 14 + bar, y: by, class: "diagram__label" }, root);
  scaleLabel.textContent = "5 m";

  if (hull.shield) {
    const c = P([0, 0]);
    svg("circle", { cx: c[0], cy: c[1], r: hull.shield.radius * k, class: "diagram__shield" }, root);
  }

  const reach = turretReach(hull);
  const arcs = svg("g", { class: "diagram__arcs" }, root);
  for (const t of hull.turrets) {
    const centre = screen(t.pos);
    if (t.arc_deg === 0) {
      const a = px(centre);
      const b = px(add(centre, bearing(t.rest_deg), reach * 1.25));
      svg("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "diagram__fixed" }, arcs);
      continue;
    }
    const from = t.rest_deg - t.arc_deg / 2;
    const to = t.rest_deg + t.arc_deg / 2;
    const c = px(centre);
    const d = `M${c[0].toFixed(2)},${c[1].toFixed(2)}L${arcPath(px(centre), reach * k, from, to).slice(1)}Z`;
    svg("path", { d, class: "diagram__arc" }, arcs);
    const rest = px(add(centre, bearing(t.rest_deg), reach));
    svg("line", { x1: c[0], y1: c[1], x2: rest[0], y2: rest[1], class: "diagram__rest" }, arcs);
  }

  const body = svg("g", { class: "diagram__body" }, root);
  for (const circle of hull.collision) {
    const c = P(circle.pos);
    svg("circle", { cx: c[0], cy: c[1], r: circle.r * k, class: "diagram__footprint" }, body);
  }

  const thrust = svg("g", { class: "diagram__thrusters" }, root);
  for (const t of hull.thrusters) {
    const mount = screen(t.pos);
    const dir = screen(t.dir);
    const tail = px(add(mount, dir, -arrowLength(hull, t.max_force)));
    const head = px(mount);
    const len = Math.hypot(head[0] - tail[0], head[1] - tail[1]);
    const ux = (head[0] - tail[0]) / len;
    const uy = (head[1] - tail[1]) / len;
    const base: Vec2 = [head[0] - ux * ARROW_HEAD * 1.4, head[1] - uy * ARROW_HEAD * 1.4];
    const g = svg("g", { class: "diagram__thruster" }, thrust);
    svg("title", {}, g).textContent = `${t.id}: ${t.max_force} N`;
    svg("line", { x1: tail[0], y1: tail[1], x2: base[0], y2: base[1], class: "diagram__shaft" }, g);
    svg(
      "path",
      {
        d: `M${head[0]},${head[1]}L${base[0] - uy * ARROW_HEAD},${base[1] + ux * ARROW_HEAD}L${base[0] + uy * ARROW_HEAD},${base[1] - ux * ARROW_HEAD}Z`,
        class: "diagram__head",
      },
      g,
    );
  }

  const guns = svg("g", { class: "diagram__turrets" }, root);
  for (const t of hull.turrets) {
    const c = P(t.pos);
    const g = svg("g", {}, guns);
    svg("title", {}, g).textContent = `${t.id}: ${t.weapon}, ${t.arc_deg === 0 ? "fixed" : `${t.arc_deg}° arc`}`;
    svg("circle", { cx: c[0], cy: c[1], r: 3.5, class: "diagram__turret" }, g);
  }
  return root;
}

const RING_SIZE = 168;
const RING_R = 52;
const LABEL_R = 70;

/** Opacity and width grow with the multiplier: brighter and thicker take more damage. */
function ringStyle(mult: number): { opacity: number; width: number } {
  return { opacity: Math.min(0.95, Math.max(0.14, 0.5 + 0.85 * (mult - 1))), width: 3 + 4 * mult };
}

function fmtMult(m: number): string {
  return `×${Number.isInteger(m) ? m.toFixed(0) : String(m)}`;
}

/** A small ring of damage multipliers by bearing around the hull's footprint. */
export function multiplierRing(hull: Hull, arcs: Arc[], label: string): SVGSVGElement {
  const c: Vec2 = [RING_SIZE / 2, RING_SIZE / 2];
  const root = svg("svg", { viewBox: `0 0 ${RING_SIZE} ${RING_SIZE}`, class: "ring", role: "img" });
  root.setAttribute("aria-label", `${label}: ${arcs.map((a) => `${a.name} ${fmtMult(a.mult)}`).join(", ")}`);
  const k = 30 / Math.max(hull.bound_radius, 1);
  for (const circle of hull.collision) {
    const p = add(c, screen(circle.pos), k);
    svg("circle", { cx: p[0], cy: p[1], r: circle.r * k, class: "diagram__footprint" }, root);
  }
  svg("path", { d: `M${c[0]},${c[1] - 34}l-3,5h6z`, class: "ring__nose" }, root);
  const gapDeg = (2 / RING_R) * (180 / Math.PI);
  for (const arc of arcs) {
    const span = (((arc.to_deg - arc.from_deg) % 360) + 360) % 360 || 360;
    const style = ringStyle(arc.mult);
    const attrs = { class: "ring__arc", "stroke-width": style.width, "stroke-opacity": style.opacity };
    if (span >= 359.9) {
      svg("circle", { cx: c[0], cy: c[1], r: RING_R, ...attrs }, root);
    } else {
      const from = arc.from_deg + gapDeg / 2;
      const d = arcPath(c, RING_R, from, from + span - gapDeg);
      svg("path", { d, ...attrs }, root);
    }
    const mid = span >= 359.9 ? 180 : arc.from_deg + span / 2;
    const at = add(c, bearing(mid), LABEL_R);
    const t = svg("text", { x: at[0], y: at[1], class: "ring__label", "text-anchor": "middle", "dominant-baseline": "middle" }, root);
    t.textContent = fmtMult(arc.mult);
  }
  return root;
}
