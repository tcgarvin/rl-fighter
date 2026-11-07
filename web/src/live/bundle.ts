// The champion bundle (scripts/build_bundle.sh → /bundle/): the sim wasm, the exported
// policy, the pilots the page picks from ship by ship (a bundle without any flies the
// champion alone), the commanders each side draws from (a bundle without any keeps the
// sim's scripted commander on both), the catalogue and manifest.json (rlf.bundle/1).
// Every file but the manifest is fetched with ?v=<bundle_id>, so a new bundle never
// mixes with a cached old one and its wasm instantiates as a fresh module next to the
// running one.

import { createPolicy, type Policy, type PolicyManifest } from "./policy.js";
import { createCommander, type Commander, type CommanderManifest, type FlatLayoutEntry } from "./commander.js";
import { pilotObsDim, simLayout, type Catalogue, type MatchSettings, type SimLayout, type SimModule } from "./sim.ts";
import type { RosterRules } from "./roster.ts";

export const BUNDLE_SCHEMA = "rlf.bundle/1";

export interface ChampionEval {
  a: string;
  b: string;
  n: number;
  wins: number;
  draws: number;
  losses: number;
  win_rate: number;
  hit_rate: number | null;
}

/** One entry of manifest.pilots: `dir` holds its export, relative to the bundle. */
export interface PilotEntry {
  id: string;
  family: string;
  rating: number;
  dir: string;
  sim_version: number;
  /** A sentence or two for viewers, and the order drill scores 0..1 (empty: never drilled). */
  note?: string;
  follows?: { go_to?: number; attack?: number; defend?: number };
}

/** A pilot ready to fly: its policy and the obs prefix it reads (pilotObsDim). */
export interface LivePilot {
  id: string;
  policy: Policy;
  obsDim: number;
  /** Its manifest entry; null for a champion flying alone in a bundle with no list. */
  entry: PilotEntry | null;
}

/** An exported policy's two files. */
export interface PolicyFiles {
  pm: PolicyManifest;
  weights: ArrayBuffer;
}

export const CHAMPION_DIR = "policy";

/** One entry of manifest.commanders (tools/live_commanders.py): `dir` holds a learned one's export. */
export interface CommanderEntry {
  id: string;
  kind: "scripted" | "learned";
  note: string;
  dir?: string;
  update?: number;
}

/** A commander ready to decide: the sim's script (net null) or a learned net. */
export interface LiveCommander {
  id: string;
  kind: "scripted" | "learned";
  net: Commander | null;
  entry: CommanderEntry;
}

export const SCRIPTED_COMMANDER: LiveCommander = {
  id: "scripted",
  kind: "scripted",
  net: null,
  entry: { id: "scripted", kind: "scripted", note: "" },
};

/** A commander as the page names it: its id, or "scripted". */
export function commanderName(c: LiveCommander): string {
  return c.net ? c.id : "scripted";
}

/** A learned commander's exported files. */
export interface CommanderFiles {
  cm: CommanderManifest;
  weights: ArrayBuffer;
}

export interface BundleManifest {
  schema: string;
  bundle_id: string;
  /** The wasm build's sim version. */
  sim_version: number;
  /** The policy's (training) sim version; absent in bundles before SIM_VERSION 4. */
  pilot_sim_version?: number;
  champion: {
    id: string;
    name: string;
    run: string;
    hulls: string[];
    update: number | null;
    eval: ChampionEval | null;
  };
  match: MatchSettings;
  roster: RosterRules;
  /** The pilots picked from ship by ship; absent: the champion flies every strike craft. */
  pilots?: PilotEntry[];
  /** The logbook entry that introduces them (lab/runs/<id>). */
  pilots_entry?: string;
  /** The commanders each side draws from; absent: both sides scripted. */
  commanders?: CommanderEntry[];
  /** The logbook entry that introduces the learned ones ("" if none). */
  commanders_entry?: string;
}

export interface Bundle {
  manifest: BundleManifest;
  sim: SimModule;
  layout: SimLayout;
  /** At least one; the champion alone in a bundle that lists none. */
  pilots: LivePilot[];
  /** At least one: the scripted commander alone in a bundle that lists none. */
  commanders: LiveCommander[];
  catalogue: Catalogue;
}

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

function need<T>(ok: boolean, what: string, value: T): T {
  if (!ok) throw new Error(`bundle manifest: bad or missing ${what}`);
  return value;
}

/** Check the manifest's shape at the boundary; throws on anything the page relies on. */
export function parseManifest(raw: unknown): BundleManifest {
  if (!isRecord(raw)) throw new Error("bundle manifest is not an object");
  need(raw.schema === BUNDLE_SCHEMA, `schema (got ${String(raw.schema)}, want ${BUNDLE_SCHEMA})`, 0);
  const { champion, match, roster } = raw;
  need(typeof raw.bundle_id === "string" && raw.bundle_id.length > 0, "bundle_id", 0);
  need(Number.isInteger(raw.sim_version), "sim_version", 0);
  need(raw.pilot_sim_version === undefined || Number.isInteger(raw.pilot_sim_version), "pilot_sim_version", 0);
  need(isRecord(champion) && typeof champion.id === "string" && typeof champion.run === "string", "champion", 0);
  need(isRecord(champion) && Array.isArray(champion.hulls) && champion.hulls.length > 0, "champion.hulls", 0);
  need(isRecord(match) && [match.arena_radius, match.time_limit_ticks, match.reaction_ticks].every((v) => typeof v === "number"), "match", 0);
  need(isRecord(roster) && Array.isArray(roster.hulls) && roster.hulls.length > 0, "roster.hulls", 0);
  need(isRecord(roster) && [roster.min_per_side, roster.max_per_side, roster.budget].every(Number.isInteger), "roster sizes", 0);
  const { pilots } = raw;
  need(
    pilots === undefined || (Array.isArray(pilots) && pilots.length > 0 && pilots.every((p) => isRecord(p) && typeof p.id === "string" && typeof p.dir === "string")),
    "pilots",
    0,
  );
  const { commanders } = raw;
  need(
    commanders === undefined ||
      (Array.isArray(commanders) &&
        commanders.length > 0 &&
        commanders.every((c) => isRecord(c) && typeof c.id === "string" && (c.kind === "scripted" || (c.kind === "learned" && typeof c.dir === "string")))),
    "commanders",
    0,
  );
  return raw as unknown as BundleManifest;
}

/** The learned commander's interface of this wasm, which every learned commander must match. */
function commanderExpect(sim: SimModule): { ioVersion: number; featuresLen: number; actionDim: number; flatLayout: FlatLayoutEntry[] } {
  if (typeof sim.commanderIoJson !== "function" || typeof sim.COMMANDER_IO_VERSION !== "function") {
    throw new Error("bundle lists a learned commander, but its wasm has no learned commander interface");
  }
  const io = JSON.parse(sim.commanderIoJson()) as { flat_layout: FlatLayoutEntry[] };
  return { ioVersion: sim.COMMANDER_IO_VERSION(), featuresLen: sim.COMMANDER_FEATURES_LEN!(), actionDim: sim.COMMANDER_ACTION_DIM!(), flatLayout: io.flat_layout };
}

/** The bundle's commanders, each learned one checked against the wasm (createCommander). */
function assembleCommanders(manifest: BundleManifest, sim: SimModule, files: Record<string, CommanderFiles>): LiveCommander[] {
  const entries = manifest.commanders ?? [];
  if (entries.length === 0) return [SCRIPTED_COMMANDER];
  const expect = entries.some((e) => e.kind === "learned") ? commanderExpect(sim) : null;
  return entries.map((entry) => {
    if (entry.kind === "scripted") return { id: entry.id, kind: "scripted", net: null, entry };
    const f = files[entry.dir!];
    if (!f) throw new Error(`bundle lists commander ${entry.id}, but ${entry.dir} was not loaded`);
    return { id: entry.id, kind: "learned", net: createCommander(f.cm, f.weights, expect!), entry };
  });
}

/** The `dir` of every learned commander the manifest lists. */
export function commanderDirs(manifest: BundleManifest): string[] {
  return (manifest.commanders ?? []).flatMap((c) => (c.kind === "learned" && c.dir ? [c.dir] : []));
}

/**
 * Put loaded parts together and check they agree: the manifest's sim version against
 * the wasm, every policy against the wasm's layout (createPolicy), every learned
 * commander against its commander interface (createCommander), and the catalogue by
 * building and freeing a one-ship-a-side match of every rostered hull. `pilotFiles` holds
 * each listed pilot's export by its `dir`, all but the champion's; `commanderFiles` each
 * learned commander's.
 */
export function assembleBundle(
  manifest: BundleManifest,
  sim: SimModule,
  policyManifest: PolicyManifest,
  weights: ArrayBuffer,
  catalogue: Catalogue,
  pilotFiles: Record<string, PolicyFiles> = {},
  commanderFiles: Record<string, CommanderFiles> = {},
): Bundle {
  const layout = simLayout(sim);
  if (layout.simVersion !== manifest.sim_version) throw new Error(`bundle says sim_version ${manifest.sim_version}, its wasm is ${layout.simVersion}`);
  const pilot = manifest.pilot_sim_version ?? manifest.sim_version;
  if (!layout.pilotCompat.includes(pilot)) throw new Error(`bundle pilot is for sim_version ${pilot}; this wasm flies pilots of ${layout.pilotCompat.join(", ")}`);
  if (policyManifest.sim_version !== pilot) throw new Error(`bundle says pilot_sim_version ${pilot}, its policy is for ${policyManifest.sim_version}`);
  // A v3/v4 pilot in a v5 wasm reads the first 385 obs floats (SIM_SPEC §0.3).
  const obsDim = pilotObsDim(layout, pilot);
  const champion = createPolicy(policyManifest, weights, { ...layout, obsDim });
  const pilots: LivePilot[] = (manifest.pilots ?? []).map((entry) => {
    if (entry.dir === CHAMPION_DIR) return { id: entry.id, policy: champion, obsDim, entry };
    const files = pilotFiles[entry.dir];
    if (!files) throw new Error(`bundle lists pilot ${entry.id}, but ${entry.dir} was not loaded`);
    const dim = pilotObsDim(layout, files.pm.sim_version);
    return { id: entry.id, policy: createPolicy(files.pm, files.weights, { ...layout, obsDim: dim }), obsDim: dim, entry };
  });
  if (pilots.length === 0) pilots.push({ id: manifest.champion.id, policy: champion, obsDim, entry: null });
  for (const hull of manifest.roster.hulls) {
    if (!catalogue.info[hull]) throw new Error(`roster hull ${hull} is not in the catalogue`);
    const probe = new sim.WasmMatch(catalogue.hulls, catalogue.weapons, JSON.stringify({ seed: 0, ...manifest.match, fleets: [[hull], [hull]] }));
    probe.free();
  }
  const commanders = assembleCommanders(manifest, sim, commanderFiles);
  return { manifest, sim, layout, pilots, commanders, catalogue };
}

async function fetchOk(url: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res;
}

/** The current manifest, bypassing the HTTP cache. */
export async function fetchManifest(base: string): Promise<BundleManifest> {
  const res = await fetchOk(`${base}manifest.json`, { cache: "no-store" });
  return parseManifest(await res.json());
}

/** Load and check every file of the bundle `manifest` describes (browser). */
export async function loadBundle(base: string, manifest: BundleManifest): Promise<Bundle> {
  const v = `?v=${encodeURIComponent(manifest.bundle_id)}`;
  const absolute = new URL(base, location.href);
  const sim = (await import(/* @vite-ignore */ new URL(`pkg/sim_wasm.js${v}`, absolute).href)) as SimModule;
  const policyFiles = async (dir: string): Promise<PolicyFiles> => {
    const pm = (await (await fetchOk(`${base}${dir}/manifest.json${v}`)).json()) as PolicyManifest;
    return { pm, weights: await (await fetchOk(`${base}${dir}/${pm.weights_file}${v}`)).arrayBuffer() };
  };
  const commanderFiles = async (dir: string): Promise<CommanderFiles> => {
    const cm = (await (await fetchOk(`${base}${dir}/manifest.json${v}`)).json()) as CommanderManifest;
    return { cm, weights: await (await fetchOk(`${base}${dir}/${cm.weights_file}${v}`)).arrayBuffer() };
  };
  const dirs = (manifest.pilots ?? []).map((p) => p.dir).filter((d) => d !== CHAMPION_DIR);
  const cdirs = commanderDirs(manifest);
  const [, { pm, weights }, catalogue, pilotFiles, cfiles] = await Promise.all([
    sim.default({ module_or_path: new URL(`pkg/sim_wasm_bg.wasm${v}`, absolute) }),
    policyFiles(CHAMPION_DIR),
    fetchOk(`${base}catalogue.json${v}`).then((r) => r.json() as Promise<Catalogue>),
    Promise.all(dirs.map(policyFiles)),
    Promise.all(cdirs.map(commanderFiles)),
  ]);
  const byDir = Object.fromEntries(dirs.map((d, i) => [d, pilotFiles[i]!]));
  const byCommanderDir = Object.fromEntries(cdirs.map((d, i) => [d, cfiles[i]!]));
  return assembleBundle(manifest, sim, pm, weights, catalogue, byDir, byCommanderDir);
}
