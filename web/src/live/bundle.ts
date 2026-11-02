// The champion bundle (scripts/build_bundle.sh → /bundle/): the sim wasm, the exported
// policy, the pilots the page picks from ship by ship (a bundle without any flies the
// champion alone), the catalogue and manifest.json (rlf.bundle/1). Every file but the manifest
// is fetched with ?v=<bundle_id>, so a new bundle never mixes with a cached old one and
// its wasm instantiates as a fresh module next to the running one.

import { createPolicy, type Policy, type PolicyManifest } from "./policy.js";
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
}

export interface Bundle {
  manifest: BundleManifest;
  sim: SimModule;
  layout: SimLayout;
  /** At least one; the champion alone in a bundle that lists none. */
  pilots: LivePilot[];
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
  return raw as unknown as BundleManifest;
}

/**
 * Put loaded parts together and check they agree: the manifest's sim version against
 * the wasm, every policy against the wasm's layout (createPolicy), and the catalogue by
 * building and freeing a one-ship-a-side match of every rostered hull. `pilotFiles` holds
 * each listed pilot's export by its `dir`, all but the champion's.
 */
export function assembleBundle(
  manifest: BundleManifest,
  sim: SimModule,
  policyManifest: PolicyManifest,
  weights: ArrayBuffer,
  catalogue: Catalogue,
  pilotFiles: Record<string, PolicyFiles> = {},
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
  return { manifest, sim, layout, pilots, catalogue };
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
  const dirs = (manifest.pilots ?? []).map((p) => p.dir).filter((d) => d !== CHAMPION_DIR);
  const [, { pm, weights }, catalogue, pilotFiles] = await Promise.all([
    sim.default({ module_or_path: new URL(`pkg/sim_wasm_bg.wasm${v}`, absolute) }),
    policyFiles(CHAMPION_DIR),
    fetchOk(`${base}catalogue.json${v}`).then((r) => r.json() as Promise<Catalogue>),
    Promise.all(dirs.map(policyFiles)),
  ]);
  const byDir = Object.fromEntries(dirs.map((d, i) => [d, pilotFiles[i]!]));
  return assembleBundle(manifest, sim, pm, weights, catalogue, byDir);
}
