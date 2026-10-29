// The experiment notebook (DESIGN §10): an index of every lab run, newest first and
// grouped by sim season, and one entry per run. Data comes from
// tools/build_notebook.py; routes are hashes so /notebook/#<run-id> deep-links work
// (#<run-id>/plan opens the plan).
import { mountNav } from "../shell/nav";
import { formatValue, lineChart } from "./chart";
import type { Artefact, ArtefactKind, ChampionRef, IndexRun, NotebookIndex, RunPage, Verdict } from "./types";
import "./notebook.css";

const DATA = "/notebook/data";
const TITLE = "RL Fighter · Notebook";

mountNav("notebook");
const main = document.createElement("main");
main.className = "page notebook";
main.id = "main";
document.body.append(main);

const runCache = new Map<string, Promise<RunPage>>();
let index: NotebookIndex | null = null;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function link(href: string, text: string, className = ""): HTMLAnchorElement {
  const a = el("a", className, text);
  a.href = href;
  if (href.startsWith("http")) a.rel = "noopener";
  return a;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return (await response.json()) as T;
}

function loadRun(id: string): Promise<RunPage> {
  let pending = runCache.get(id);
  if (!pending) {
    pending = fetchJson<RunPage>(`${DATA}/${encodeURIComponent(id)}.json`);
    // A failed fetch must not stick: the next visit tries again.
    pending.catch(() => runCache.delete(id));
    runCache.set(id, pending);
  }
  return pending;
}

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function formatDate(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? iso : DATE_FORMAT.format(date);
}

function verdictBadge(verdict: Verdict | null, status: IndexRun["status"]): HTMLElement {
  if (verdict === null) {
    return el("span", "badge badge--quiet", status === "in progress" ? "In progress" : "No verdict");
  }
  const badge = el("span", `badge badge--${verdict.toLowerCase()}`, verdict === "shipped" ? "Shipped" : verdict);
  badge.title = verdict === "shipped" ? "A pilot from this run went live" : `Verdict: ${verdict}`;
  return badge;
}

function watchButton(champion: ChampionRef): HTMLAnchorElement {
  const a = link(champion.href, "", "button");
  a.append(el("span", "button__live"), document.createTextNode(champion.current ? "Watch this pilot" : `Watch ${champion.name}`));
  a.title = champion.current ? `${champion.name} is flying on the live page now` : `Replay ${champion.name}, a past champion`;
  return a;
}

function seasonLabel(simVersion: number | null): string {
  return simVersion === null ? "Sim season unknown" : `Sim season ${simVersion}`;
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function setView(...nodes: Node[]): void {
  main.classList.remove("is-index");
  main.replaceChildren(...nodes);
}

function message(title: string, body: string, back = true): HTMLElement {
  const box = el("section", "nb-message");
  box.append(el("h1", "", title), el("p", "lede", body));
  if (back) box.append(link("#", "← All entries", "nb-back"));
  return box;
}

// ---------------------------------------------------------------------------
// Index
// ---------------------------------------------------------------------------

function renderIndex(data: NotebookIndex): void {
  document.title = TITLE;
  const head = el("header", "nb-head");
  head.append(
    el("p", "kicker", "Experiment notebook"),
    el("h1", "", "The lab journal"),
    el(
      "p",
      "lede",
      "Every training run on this project, newest first: what it asked, how it was run, and what it found. Runs that failed are published too. A change to the physics starts a new sim season, and pilots only compete within one.",
    ),
  );
  const current = data.current_champion;
  if (current) {
    const card = el("div", "nb-champion");
    const text = el("p", "nb-champion__text");
    text.append(el("span", "kicker", "Flying now"), el("strong", "", current.name), document.createTextNode(" · from "));
    text.append(link(`#${current.run}`, current.run, "mono"));
    card.append(text, watchButton(current));
    head.append(card);
  }

  const list = el("div", "nb-index");
  let season: HTMLOListElement | null = null;
  let seasonVersion: number | null | undefined;
  for (const run of data.runs) {
    if (season === null || run.sim_version !== seasonVersion) {
      seasonVersion = run.sim_version;
      const count = data.runs.filter((r) => r.sim_version === run.sim_version).length;
      const divider = el("h2", "nb-season");
      divider.append(el("span", "nb-season__name", seasonLabel(run.sim_version)), el("span", "nb-season__count", plural(count, "run")));
      season = el("ol", "nb-list");
      list.append(divider, season);
    }
    season.append(indexItem(run));
  }
  if (data.runs.length === 0) list.append(el("p", "lede", "No runs yet."));
  setView(head, list, footer());
  main.classList.add("is-index");
}

function indexItem(run: IndexRun): HTMLLIElement {
  const li = el("li", "nb-item");
  const a = link(`#${run.id}`, "", "nb-item__link");
  const meta = el("div", "nb-item__meta");
  const time = el("time", "", formatDate(run.date));
  time.dateTime = run.date;
  meta.append(time, verdictBadge(run.verdict, run.status));
  a.append(meta, el("h3", "nb-item__title", run.title));
  if (run.summary) a.append(el("p", "nb-item__summary", run.summary));
  const facts = [run.has_plan ? "plan" : "", run.n_charts ? plural(run.n_charts, "chart") : "", run.n_artefacts ? plural(run.n_artefacts, "eval file") : ""].filter(Boolean);
  const foot = el("p", "nb-item__foot");
  foot.append(el("span", "mono", run.id));
  if (facts.length) foot.append(document.createTextNode(` · ${facts.join(" · ")}`));
  a.append(foot);
  li.append(a);
  for (const champion of run.champions) li.append(watchButton(champion));
  return li;
}

function footer(): HTMLElement {
  const f = el("footer", "page-footer");
  f.append(
    document.createTextNode("Generated from "),
    link("https://github.com/tcgarvin/rl-fighter/tree/main/lab/runs", "lab/runs", "mono"),
    document.createTextNode(" by "),
    link("https://github.com/tcgarvin/rl-fighter/blob/main/tools/build_notebook.py", "tools/build_notebook.py", "mono"),
    document.createTextNode(". Each entry is the run's own write-up, unedited."),
  );
  return f;
}

// ---------------------------------------------------------------------------
// Entry
// ---------------------------------------------------------------------------

function renderRun(run: RunPage, openPlan: boolean): void {
  document.title = `${run.title} · Notebook`;
  const crumbs = el("nav", "nb-crumbs");
  crumbs.setAttribute("aria-label", "Notebook");
  crumbs.append(link("#", "← All entries", "nb-back"));

  const head = el("header", "nb-entry-head");
  const kicker = el("p", "kicker");
  const time = el("time", "", formatDate(run.date));
  time.dateTime = run.date;
  kicker.append(time, document.createTextNode(` · ${seasonLabel(run.sim_version)}`));
  const badges = el("div", "nb-entry-head__badges");
  badges.append(verdictBadge(run.verdict, run.status), el("span", "mono muted", run.id));
  head.append(kicker, el("h1", "", run.title), badges);
  if (run.champions.length) {
    const actions = el("div", "nb-entry-head__actions");
    for (const c of run.champions) actions.append(watchButton(c));
    head.append(actions);
  }

  const article = el("article", "prose nb-article");
  if (run.results_html !== null) {
    article.innerHTML = run.results_html;
  } else {
    article.append(el("p", "pending", "Results pending: this run has a plan but no write-up yet."));
  }
  placeCharts(article, run);

  const extras = el("section", "nb-extras");
  if (run.artefacts.length) extras.append(artefactsBlock(run.artefacts));
  if (run.plan_html !== null) extras.append(planBlock(run, openPlan));
  extras.append(sourceLinks(run));

  setView(crumbs, head, article, extras, pager(run.id), footer());
  if (openPlan) document.getElementById("plan")?.scrollIntoView({ block: "start" });
}

/** Put the learning curves where the write-up talks about results. */
function placeCharts(article: HTMLElement, run: RunPage): void {
  if (!run.charts.length) return;
  const section = el("section", "wide nb-charts");
  const arms = run.arms.map((a) => a.id);
  const grid = el("div", "nb-chart-grid");
  for (const chart of run.charts) grid.append(lineChart(chart, { armOrder: arms }));
  const note = el("p", "figure__caption nb-charts__note");
  note.append(document.createTextNode("From the training logs: "));
  run.arms.forEach((arm, i) => {
    if (i) note.append(document.createTextNode("; "));
    note.append(link(arm.href, arm.id, "mono"));
    const samples = arm.samples >= 1e6 ? `${(arm.samples / 1e6).toFixed(1)} M` : arm.samples.toLocaleString("en-GB");
    note.append(document.createTextNode(`, ${arm.updates.toLocaleString("en-GB")} updates, ${samples} samples`));
  });
  note.append(document.createTextNode(". Hover or drag across a chart to read values."));

  const headings = [...article.querySelectorAll("h2, h3")];
  const curves = headings.find((h) => /learning curve/i.test(h.textContent ?? ""));
  if (curves) {
    section.append(grid, note);
    curves.after(section);
    return;
  }
  section.append(el("h2", "", "Learning curves"), grid, note);
  const h2s = headings.filter((h) => h.tagName === "H2");
  const resultsAt = h2s.findIndex((h) => /results|gates/i.test(h.textContent ?? ""));
  const after = resultsAt >= 0 ? h2s[resultsAt + 1] : h2s.find((h) => /looked like|learned|next/i.test(h.textContent ?? ""));
  if (after) after.before(section);
  else article.append(section);
}

function planBlock(run: RunPage, open: boolean): HTMLElement {
  const details = el("details", "disclosure nb-plan");
  details.id = "plan";
  details.open = open;
  const summary = el("summary");
  summary.append(el("span", "disclosure__title", "The plan"), el("span", "disclosure__meta", "written before the run"));
  const body = el("div", "disclosure__body");
  if (run.plan_title) body.append(el("p", "nb-plan__title", run.plan_title));
  const prose = el("div", "prose");
  prose.innerHTML = run.plan_html ?? "";
  body.append(prose);
  details.append(summary, body);
  return details;
}

interface Column {
  label: string;
  value: (a: Artefact) => string;
  num?: boolean;
}

const pct = (key: string): Column["value"] => (a) => formatValue(a.metrics[key] ?? null, "pct");
const fixed = (key: string, digits: number, unit = ""): Column["value"] => (a) => {
  const v = a.metrics[key];
  return v === null || v === undefined ? "–" : `${v.toFixed(digits)}${unit}`;
};

const COLUMNS: Partial<Record<ArtefactKind, { title: string; columns: Column[] }>> = {
  duel: {
    title: "Duels",
    columns: [
      { label: "a", value: (a) => a.a },
      { label: "b", value: (a) => a.b },
      { label: "n", value: fixed("n", 0), num: true },
      { label: "a wins", value: pct("win"), num: true },
      { label: "draws", value: pct("draw"), num: true },
      { label: "a hit rate", value: pct("hit_rate"), num: true },
      { label: "b hit rate", value: pct("opp_hit_rate"), num: true },
      { label: "median length", value: fixed("length_s", 1, " s"), num: true },
      { label: "passes", value: fixed("passes", 2), num: true },
      { label: "sim", value: fixed("sim_version", 0), num: true },
    ],
  },
  survey: {
    title: "Contact surveys",
    columns: [
      { label: "a", value: (a) => a.a },
      { label: "b", value: (a) => a.b },
      { label: "n", value: fixed("n", 0), num: true },
      { label: "a wins", value: pct("win"), num: true },
      { label: "contacts / match", value: fixed("contacts_per_match", 2), num: true },
      { label: "closing p50", value: fixed("closing_p50", 0, " m/s"), num: true },
      { label: "head-on", value: pct("head_on_share"), num: true },
      { label: "crash deaths", value: pct("crash_death_share"), num: true },
    ],
  },
  bc: {
    title: "Behaviour cloning",
    columns: [
      { label: "file", value: (a) => a.label },
      { label: "rows", value: fixed("rows", 0), num: true },
      { label: "throttle agreement", value: pct("throttle"), num: true },
      { label: "fire agreement", value: pct("fire"), num: true },
      { label: "power agreement", value: pct("power"), num: true },
    ],
  },
  dagger: {
    title: "DAgger",
    columns: [
      { label: "file", value: (a) => a.label },
      { label: "rounds", value: fixed("rounds", 0), num: true },
      { label: "best round", value: fixed("best_round", 0), num: true },
      { label: "best round's win rate", value: pct("best_win"), num: true },
    ],
  },
};

function artefactsBlock(artefacts: Artefact[]): HTMLElement {
  const details = el("details", "disclosure nb-artefacts");
  const summary = el("summary");
  summary.append(el("span", "disclosure__title", "Eval files"), el("span", "disclosure__meta", plural(artefacts.length, "file")));
  const body = el("div", "disclosure__body");
  body.append(el("p", "figure__caption", "Headline numbers from every JSON the run wrote. Side a is the pilot under test; sides swap halfway so neither starts with an advantage. Names link to the raw file."));
  const kinds: ArtefactKind[] = ["duel", "survey", "bc", "dagger"];
  for (const kind of kinds) {
    const spec = COLUMNS[kind];
    const rows = artefacts.filter((a) => a.kind === kind);
    if (!spec || !rows.length) continue;
    // Drop columns no file of this kind fills (e.g. crash counts before sim v3).
    const columns = spec.columns.filter((c) => c.num !== true || rows.some((r) => c.value(r) !== "–"));
    body.append(el("h4", "nb-artefacts__kind", spec.title));
    const wrap = el("div", "table-scroll");
    const table = el("table");
    const tr = el("tr");
    for (const c of columns) tr.append(el("th", c.num ? "num" : "", c.label));
    const thead = el("thead");
    thead.append(tr);
    const tbody = el("tbody");
    for (const row of rows) {
      const r = el("tr");
      columns.forEach((c, i) => {
        const td = el("td", c.num ? "num" : "mono");
        if (i === 0) td.append(link(row.href, c.value(row)));
        else td.textContent = c.value(row);
        r.append(td);
      });
      tbody.append(r);
    }
    table.append(thead, tbody);
    wrap.append(table);
    body.append(wrap);
  }
  const others = artefacts.filter((a) => !kinds.includes(a.kind));
  if (others.length) {
    body.append(el("h4", "nb-artefacts__kind", "Other files"));
    const ul = el("ul", "nb-files");
    for (const a of others) {
      const li = el("li");
      li.append(link(a.href, a.path, "mono"));
      ul.append(li);
    }
    body.append(ul);
  }
  details.append(summary, body);
  return details;
}

function sourceLinks(run: RunPage): HTMLElement {
  const p = el("p", "nb-source");
  p.append(el("span", "kicker", "Source"));
  const links: Array<[string | null, string]> = [
    [run.source.results, "results.md"],
    [run.source.plan, "plan.md"],
    [run.source.dir, "run directory"],
  ];
  for (const [href, label] of links) if (href) p.append(link(href, label));
  return p;
}

function pager(id: string): HTMLElement {
  const nav = el("nav", "nb-pager");
  nav.setAttribute("aria-label", "Older and newer entries");
  const runs = index?.runs ?? [];
  const at = runs.findIndex((r) => r.id === id);
  const newer = at > 0 ? runs[at - 1] : undefined;
  const older = at >= 0 ? runs[at + 1] : undefined;
  for (const [run, label, cls] of [
    [newer, "Newer", "nb-pager__newer"],
    [older, "Older", "nb-pager__older"],
  ] as const) {
    if (!run) {
      nav.append(el("span", cls));
      continue;
    }
    const a = link(`#${run.id}`, "", `nb-pager__link ${cls}`);
    a.append(el("span", "kicker", label), el("span", "nb-pager__title", run.title));
    nav.append(a);
  }
  return nav;
}

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

function parseHash(): { id: string; plan: boolean } {
  const raw = decodeURIComponent(location.hash.replace(/^#/, ""));
  const [id = "", section = ""] = raw.split("/");
  return { id, plan: section === "plan" };
}

let routeToken = 0;

async function route(): Promise<void> {
  const token = ++routeToken;
  const { id, plan } = parseHash();
  if (!index) return;
  if (!id) {
    renderIndex(index);
    window.scrollTo(0, 0);
    return;
  }
  if (!index.runs.some((r) => r.id === id)) {
    document.title = TITLE;
    setView(message("No such entry", `There is no notebook entry called "${id}".`), footer());
    return;
  }
  main.setAttribute("aria-busy", "true");
  try {
    const run = await loadRun(id);
    if (token !== routeToken) return;
    renderRun(run, plan);
    if (!plan) window.scrollTo(0, 0);
  } catch (error) {
    if (token !== routeToken) return;
    setView(message("Couldn't load this entry", `${(error as Error).message}. Try reloading the page.`));
  } finally {
    main.removeAttribute("aria-busy");
  }
}

async function start(): Promise<void> {
  try {
    index = await fetchJson<NotebookIndex>(`${DATA}/index.json`);
  } catch (error) {
    setView(
      message(
        "The notebook data is missing",
        `${(error as Error).message}. The data is generated by scripts/build_pages_data.sh before the site is built.`,
        false,
      ),
    );
    return;
  }
  window.addEventListener("hashchange", () => void route());
  await route();
}

void start();
