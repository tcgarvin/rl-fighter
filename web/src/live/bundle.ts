// The champion bundle (scripts/build_bundle.sh → /bundle/): the sim wasm, the exported
// policy, the catalogue and manifest.json (rlf.bundle/1). Every file but the manifest
// is fetched with ?v=<bundle_id>, so a new bundle never mixes with a cached old one and
// its wasm instantiates as a fresh module next to the running one.

import { createPolicy, type Policy, type PolicyManifest } from "./policy.js";
import { simLayout, type Catalogue, type MatchSettings, type SimLayout, type SimModule } from "./sim.ts";
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

export interface BundleManifest {
  schema: string;
  bundle_id: string;
  sim_version: number;
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
}

export interface Bundle {
  manifest: BundleManifest;
  sim: SimModule;
  layout: SimLayout;
  policy: Policy;
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
  need(isRecord(champion) && typeof champion.id === "string" && typeof champion.run === "string", "champion", 0);
  need(isRecord(champion) && Array.isArray(champion.hulls) && champion.hulls.length > 0, "champion.hulls", 0);
  need(isRecord(match) && [match.arena_radius, match.time_limit_ticks, match.reaction_ticks].every((v) => typeof v === "number"), "match", 0);
  need(isRecord(roster) && Array.isArray(roster.hulls) && roster.hulls.length > 0, "roster.hulls", 0);
  need(isRecord(roster) && [roster.min_per_side, roster.max_per_side, roster.budget].every(Number.isInteger), "roster sizes", 0);
  return raw as unknown as BundleManifest;
}

/**
 * Put loaded parts together and check they agree: the manifest's sim version against
 * the wasm, the policy against the wasm's layout (createPolicy), and the catalogue by
 * building and freeing a one-ship-a-side match of every rostered hull.
 */
export function assembleBundle(
  manifest: BundleManifest,
  sim: SimModule,
  policyManifest: PolicyManifest,
  weights: ArrayBuffer,
  catalogue: Catalogue,
): Bundle {
  const layout = simLayout(sim);
  if (layout.simVersion !== manifest.sim_version) throw new Error(`bundle says sim_version ${manifest.sim_version}, its wasm is ${layout.simVersion}`);
  const policy = createPolicy(policyManifest, weights, layout);
  for (const hull of manifest.roster.hulls) {
    if (!catalogue.info[hull]) throw new Error(`roster hull ${hull} is not in the catalogue`);
    const probe = new sim.WasmMatch(catalogue.hulls, catalogue.weapons, JSON.stringify({ seed: 0, ...manifest.match, fleets: [[hull], [hull]] }));
    probe.free();
  }
  return { manifest, sim, layout, policy, catalogue };
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
  const policyFiles = fetchOk(`${base}policy/manifest.json${v}`)
    .then((r) => r.json() as Promise<PolicyManifest>)
    .then(async (pm) => ({ pm, weights: await (await fetchOk(`${base}policy/${pm.weights_file}${v}`)).arrayBuffer() }));
  const [, { pm, weights }, catalogue] = await Promise.all([
    sim.default({ module_or_path: new URL(`pkg/sim_wasm_bg.wasm${v}`, absolute) }),
    policyFiles,
    fetchOk(`${base}catalogue.json${v}`).then((r) => r.json() as Promise<Catalogue>),
  ]);
  return assembleBundle(manifest, sim, pm, weights, catalogue);
}
