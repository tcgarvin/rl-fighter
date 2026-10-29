// Hand-drawn SVG line charts for the learning curves (no chart library).
// Marks follow the dataviz rules: 2px lines, hairline recessive grid, one y-axis,
// legend for two or more series, a crosshair tooltip, and a table view.
import type { ChartData, ChartSeries, Point } from "./types";

const SVG_NS = "http://www.w3.org/2000/svg";
const SERIES_VARS = ["--series-1", "--series-2", "--series-3"] as const;
const MARGIN = { top: 10, right: 14, bottom: 26, left: 44 };
const END_LABEL_ROOM = 92;
const END_LABEL_MIN_WIDTH = 560;

/** The CSS colour for an arm, fixed by its position in the run (never by rank). */
export function seriesColor(armIndex: number): string {
  const slot = SERIES_VARS[Math.min(armIndex, SERIES_VARS.length - 1)] ?? SERIES_VARS[0];
  return `var(${slot})`;
}

function svg<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | number>,
  parent?: Element,
): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  parent?.append(el);
  return el;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function niceStep(range: number, count: number): number {
  const raw = range / Math.max(1, count);
  const power = Math.pow(10, Math.floor(Math.log10(raw)));
  const unit = raw / power;
  const nice = unit < 1.5 ? 1 : unit < 3 ? 2 : unit < 7 ? 5 : 10;
  return nice * power;
}

function ticks(min: number, max: number, count: number): number[] {
  const step = niceStep(max - min, count);
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-6; v += step) {
    out.push(Math.abs(v) < step * 1e-6 ? 0 : v);
  }
  return out;
}

function decimalsFor(step: number): number {
  return Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
}

/** Axis label for a value, given the tick spacing. */
function formatTick(v: number, format: ChartData["format"], step: number): string {
  if (format === "pct") return `${Math.round(v * 100)}%`;
  if (v === 0) return "0";
  return v.toFixed(decimalsFor(step));
}

/** Tooltip/table value: three significant figures, or a whole percentage. */
export function formatValue(v: number | null, format: ChartData["format"]): string {
  if (v === null) return "–";
  if (format === "pct") return `${(v * 100).toFixed(v >= 0.995 || v <= 0.005 ? 0 : 1)}%`;
  if (v === 0) return "0";
  return Math.abs(v) >= 1 ? v.toFixed(2) : v.toPrecision(3);
}

/** The line a series draws as its main mark: the smoothed curve when there is one. */
function mainPoints(s: ChartSeries): Point[] {
  return s.smoothed ?? s.points;
}

function domain(chart: ChartData): { x0: number; x1: number; y0: number; y1: number } {
  let x1 = 0;
  let lo = Infinity;
  let hi = -Infinity;
  for (const s of chart.series) {
    for (const [u, v] of [...s.points, ...(s.smoothed ?? [])]) {
      x1 = Math.max(x1, u);
      if (v === null) continue;
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    }
  }
  if (!Number.isFinite(lo)) {
    lo = 0;
    hi = 1;
  }
  let y0 = chart.y_min ?? lo;
  let y1 = chart.y_max ?? hi;
  if (chart.y_min === null || chart.y_max === null) {
    const pad = (hi - lo || Math.abs(hi) || 1) * 0.08;
    if (chart.y_min === null) y0 = lo - pad;
    if (chart.y_max === null) y1 = hi + pad;
    // Keep zero on the axis when the data sits near it, so sign reads correctly.
    if (chart.y_min === null && lo >= 0 && lo < (hi - lo) * 0.5) y0 = 0;
  }
  const step = niceStep(y1 - y0, 4);
  if (chart.y_min === null) y0 = Math.floor(y0 / step) * step;
  if (chart.y_max === null) y1 = Math.ceil(y1 / step) * step;
  return { x0: 0, x1: Math.max(1, x1), y0, y1: y1 > y0 ? y1 : y0 + 1 };
}

function pathFor(points: Point[], x: (u: number) => number, y: (v: number) => number): string {
  let d = "";
  let pen = false;
  for (const [u, v] of points) {
    if (v === null) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${x(u).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  }
  return d;
}

function nearest(points: Point[], update: number): Point | null {
  let best: Point | null = null;
  let bestGap = Infinity;
  for (const p of points) {
    if (p[1] === null) continue;
    const gap = Math.abs(p[0] - update);
    if (gap < bestGap) {
      best = p;
      bestGap = gap;
    }
  }
  return best;
}

interface ChartOptions {
  /** Every arm of the run, in run order, so colours follow the arm. */
  armOrder: string[];
  height?: number;
}

/** Build a self-contained figure (title, legend, plot, caption, table toggle). */
export function lineChart(chart: ChartData, options: ChartOptions): HTMLElement {
  const figure = el("figure", "figure chart");
  figure.append(el("h4", "figure__title", chart.title));
  const color = (s: ChartSeries) => seriesColor(Math.max(0, options.armOrder.indexOf(s.arm)));

  if (chart.series.length > 1) {
    const legend = el("ul", "legend");
    for (const s of chart.series) {
      const li = el("li");
      const key = el("span", "legend__key");
      key.style.background = color(s);
      li.append(key, el("span", "mono", s.arm));
      legend.append(li);
    }
    figure.append(legend);
  }

  const plot = el("div", "chart__plot");
  const tip = el("div", "chart__tip");
  tip.hidden = true;
  tip.setAttribute("aria-hidden", "true");
  plot.append(tip);
  figure.append(plot);

  const smoothing = chart.series.find((s) => s.smoothing_updates)?.smoothing_updates;
  const caption = el("p", "figure__caption");
  caption.textContent = smoothing
    ? `Rollout games against the scripted pilot, averaged over the last ${smoothing} updates; the faint line is the raw per-update rate.`
    : "Per training update, averaged into bins of a few updates.";
  const tableButton = el("button", "text-button chart__table-toggle", "Show as table");
  tableButton.type = "button";
  tableButton.setAttribute("aria-pressed", "false");
  caption.append(" ", tableButton);
  figure.append(caption);

  const table = buildTable(chart);
  table.hidden = true;
  figure.append(table);
  tableButton.addEventListener("click", () => {
    const show = table.hidden;
    table.hidden = !show;
    tableButton.setAttribute("aria-pressed", String(show));
    tableButton.textContent = show ? "Hide table" : "Show as table";
  });

  let drawnWidth = 0;
  const draw = () => {
    const width = Math.round(plot.clientWidth);
    if (width === 0 || width === drawnWidth) return;
    drawnWidth = width;
    plot.querySelector("svg")?.remove();
    plot.prepend(drawPlot(chart, width, options.height ?? 190, color, tip));
  };
  new ResizeObserver(draw).observe(plot);
  return figure;
}

function drawPlot(
  chart: ChartData,
  width: number,
  height: number,
  color: (s: ChartSeries) => string,
  tip: HTMLElement,
): SVGSVGElement {
  const endLabels = width >= END_LABEL_MIN_WIDTH && chart.series.length <= 4;
  const m = { ...MARGIN, right: MARGIN.right + (endLabels ? END_LABEL_ROOM : 0) };
  const pw = width - m.left - m.right;
  const ph = height - m.top - m.bottom;
  const { x0, x1, y0, y1 } = domain(chart);
  const x = (u: number) => m.left + ((u - x0) / (x1 - x0)) * pw;
  const y = (v: number) => m.top + (1 - (v - y0) / (y1 - y0)) * ph;

  const root = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" });
  root.setAttribute("aria-label", `${chart.title}, by training update`);

  const grid = svg("g", { class: "chart__grid" }, root);
  const yTicks = ticks(y0, y1, ph < 150 ? 3 : 4);
  const yStep = yTicks.length > 1 ? (yTicks[1] ?? 1) - (yTicks[0] ?? 0) : 1;
  for (const v of yTicks) {
    const gy = Math.round(y(v)) + 0.5;
    svg("line", { x1: m.left, x2: m.left + pw, y1: gy, y2: gy, class: v === 0 ? "chart__zero" : "" }, grid);
    const label = svg("text", { x: m.left - 8, y: gy, class: "chart__tick", "text-anchor": "end", "dominant-baseline": "middle" }, grid);
    label.textContent = formatTick(v, chart.format, yStep);
  }
  const xTicks = ticks(x0, x1, Math.max(2, Math.floor(pw / 90)));
  for (const u of xTicks) {
    // The axis name sits at the right end; ticks too close to it are left out.
    if (x(u) > m.left + pw - 84) continue;
    const label = svg("text", { x: x(u), y: m.top + ph + 18, class: "chart__tick", "text-anchor": "middle" }, grid);
    label.textContent = String(u);
  }
  const axisLabel = svg("text", { x: m.left + pw, y: m.top + ph + 18, class: "chart__tick chart__axis-label", "text-anchor": "end" }, grid);
  axisLabel.textContent = `update ${Math.round(x1)}`;

  const lines = svg("g", { class: "chart__lines", fill: "none" }, root);
  for (const s of chart.series) {
    if (s.smoothed) {
      const raw = svg("path", { d: pathFor(s.points, x, y), class: "chart__raw" }, lines);
      raw.style.stroke = color(s);
    }
    const main = svg("path", { d: pathFor(mainPoints(s), x, y), class: "chart__line" }, lines);
    main.style.stroke = color(s);
  }

  // End markers and direct labels, dropped when they would collide.
  const ends = chart.series
    .map((s) => {
      const pts = mainPoints(s).filter((p) => p[1] !== null);
      const lastPoint = pts[pts.length - 1];
      return lastPoint ? { s, px: x(lastPoint[0]), py: y(lastPoint[1] as number) } : null;
    })
    .filter((e): e is { s: ChartSeries; px: number; py: number } => e !== null);
  const marks = svg("g", { class: "chart__ends" }, root);
  for (const e of ends) {
    const dot = svg("circle", { cx: e.px, cy: e.py, r: 4, class: "chart__dot" }, marks);
    dot.style.fill = color(e.s);
  }
  if (endLabels) {
    const sorted = [...ends].sort((a, b) => a.py - b.py);
    const clash = sorted.some((e, i) => i > 0 && e.py - (sorted[i - 1]?.py ?? -Infinity) < 14);
    if (!clash) {
      for (const e of ends) {
        const t = svg("text", { x: e.px + 9, y: e.py, class: "chart__end-label", "dominant-baseline": "middle" }, marks);
        t.textContent = e.s.arm;
      }
    }
  }

  // Crosshair + tooltip; the whole plot area is the hit target.
  const cross = svg("line", { y1: m.top, y2: m.top + ph, class: "chart__cross", visibility: "hidden" }, root);
  const hoverDots = chart.series.map((s) => {
    const d = svg("circle", { r: 4, class: "chart__dot", visibility: "hidden" }, root);
    d.style.fill = color(s);
    return d;
  });
  const hit = svg("rect", { x: m.left, y: 0, width: pw, height: m.top + ph + 6, class: "chart__hit" }, root);
  const hide = () => {
    cross.setAttribute("visibility", "hidden");
    hoverDots.forEach((d) => d.setAttribute("visibility", "hidden"));
    tip.hidden = true;
  };
  const show = (clientX: number) => {
    const rect = root.getBoundingClientRect();
    const px = Math.min(m.left + pw, Math.max(m.left, clientX - rect.left));
    const update = x0 + ((px - m.left) / pw) * (x1 - x0);
    const hits = chart.series.map((s) => nearest(mainPoints(s), update));
    const anchor = hits.reduce<Point | null>(
      (best, p) => (p && (!best || Math.abs(p[0] - update) < Math.abs(best[0] - update)) ? p : best),
      null,
    );
    if (!anchor) return hide();
    const cx = x(anchor[0]);
    cross.setAttribute("x1", String(cx));
    cross.setAttribute("x2", String(cx));
    cross.setAttribute("visibility", "visible");
    tip.replaceChildren(el("div", "chart__tip-head", `update ${Math.round(anchor[0])}`));
    hits.forEach((p, i) => {
      const s = chart.series[i];
      const dot = hoverDots[i];
      if (!s || !dot) return;
      if (!p) {
        dot.setAttribute("visibility", "hidden");
        return;
      }
      dot.setAttribute("cx", String(x(p[0])));
      dot.setAttribute("cy", String(y(p[1] as number)));
      dot.setAttribute("visibility", "visible");
      const row = el("div", "chart__tip-row");
      const key = el("span", "legend__key");
      key.style.background = color(s);
      row.append(key, el("strong", "", formatValue(p[1], chart.format)), el("span", "mono muted", s.arm));
      tip.append(row);
    });
    tip.hidden = false;
    const tw = tip.offsetWidth;
    const left = cx + 12 + tw > width ? cx - 12 - tw : cx + 12;
    tip.style.left = `${Math.max(0, left)}px`;
    tip.style.top = `${m.top}px`;
  };
  hit.addEventListener("pointermove", (ev) => show(ev.clientX));
  hit.addEventListener("pointerdown", (ev) => show(ev.clientX));
  hit.addEventListener("pointerleave", hide);
  return root;
}

/** The table view: values at about a dozen evenly spaced updates. */
function buildTable(chart: ChartData): HTMLElement {
  const wrap = el("div", "table-scroll chart__table");
  const table = el("table");
  const head = el("tr");
  head.append(el("th", "", "update"));
  for (const s of chart.series) head.append(el("th", "num mono", s.arm));
  const thead = el("thead");
  thead.append(head);
  const tbody = el("tbody");
  const reference = chart.series.reduce<ChartSeries | undefined>(
    (a, s) => (!a || mainPoints(s).length > mainPoints(a).length ? s : a),
    undefined,
  );
  const pts = reference ? mainPoints(reference) : [];
  const every = Math.max(1, Math.ceil(pts.length / 12));
  const rows = pts.filter((_, i) => i % every === every - 1 || i === pts.length - 1);
  for (const [u] of rows) {
    const tr = el("tr");
    tr.append(el("td", "mono", String(Math.round(u))));
    for (const s of chart.series) {
      const p = nearest(mainPoints(s), u);
      tr.append(el("td", "num", p && Math.abs(p[0] - u) < 1e-6 ? formatValue(p[1], chart.format) : "–"));
    }
    tbody.append(tr);
  }
  table.append(thead, tbody);
  wrap.append(table);
  return wrap;
}
