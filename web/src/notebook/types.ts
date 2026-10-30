// Shapes of the JSON that tools/build_notebook.py writes to public/notebook/data/.

export type Verdict = "PASS" | "PARTIAL" | "FAIL" | "shipped";

export interface ChampionRef {
  id: string;
  name: string;
  sim_version: number;
  hulls: string[];
  promoted: string;
  current: boolean;
  /** The live page can fly it: the current champion, or a past one of its sim season. */
  watchable: boolean;
  /** "/" for the current champion, "/?champion=<id>" for a past one. */
  href: string;
}

export interface RunMeta {
  id: string;
  date: string;
  title: string;
  summary: string;
  verdict: Verdict | null;
  status: "done" | "in progress";
  sim_version: number | null;
  champions: ChampionRef[];
}

export interface IndexRun extends RunMeta {
  has_plan: boolean;
  n_charts: number;
  n_artefacts: number;
}

export interface NotebookIndex {
  schema: string;
  runs: IndexRun[];
  current_champion: (ChampionRef & { run: string }) | null;
}

/** `[update, value]`; value is null where a bin had no data. */
export type Point = [number, number | null];

export interface ChartSeries {
  arm: string;
  points: Point[];
  smoothed?: Point[];
  smoothing_updates?: number;
}

export interface ChartData {
  id: string;
  title: string;
  key: string;
  format: "pct" | "num";
  y_min: number | null;
  y_max: number | null;
  series: ChartSeries[];
}

export interface Arm {
  id: string;
  updates: number;
  samples: number;
  wall_hours: number | null;
  log: string;
  href: string;
}

export type ArtefactKind = "duel" | "survey" | "bc" | "dagger" | "matrix" | "other";

export interface Artefact {
  path: string;
  href: string;
  group: string;
  kind: ArtefactKind;
  label: string;
  a: string;
  b: string;
  argmax: boolean;
  metrics: Record<string, number | null>;
}

export interface RunPage extends RunMeta {
  schema: string;
  results_html: string | null;
  plan_title: string | null;
  plan_html: string | null;
  charts: ChartData[];
  arms: Arm[];
  artefacts: Artefact[];
  source: { dir: string; results: string | null; plan: string | null };
}
