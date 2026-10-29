// The live page (docs/M2_PLAN.md §1 Live): a match that loops forever. Each one
// musters both rosters, jumps the fleets in, fights until one side is gone or time
// runs out, holds the result over the burning wreck, and starts the next. The Rust
// sim (WASM) and the champion policy run on the main thread at 30 Hz; rendering
// interpolates between ticks. Every ship is flown by the policy; no script flies one.
//
// URL parameters: seed (pin the match seeds), fleets (duel or NvM; default: a random
// draft), details (open the technical details), warmup (fast-forward that many sim
// seconds into the first match, for screenshots), speed (run time N× faster, for
// soak tests), debug (expose window.rlfLive stats).

import { mountNav } from "../shell/nav";
import "./live.css";
import { mulberry32 } from "./policy.js";
import { fetchManifest, loadBundle, type Bundle, type BundleManifest } from "./bundle.ts";
import { Hud, type Tally } from "./hud.ts";
import { LiveMatch } from "./match.ts";
import { Muster } from "./muster.ts";
import { chooseRoster, parseRosterMode, type Roster } from "./roster.ts";
import { SIM_DT, SIM_HZ } from "./sim.ts";
import { World, hullSpec } from "./world.ts";

const BUNDLE_BASE = "/bundle/";
const MUSTER_SECONDS = 6;
// The wreck burns this long under the result banner before the next match.
const RESULT_HOLD = 3.5;
const BUNDLE_RECHECK_MS = 5 * 60 * 1000;
const BOOT_RETRY_MS = 60 * 1000;
// A stalled tab (or a slow device) drops sim backlog rather than spiralling.
const MAX_TICKS_PER_FRAME = 8;
const HUD_CLEARANCE = 10;
const LAYOUT_INTERVAL_FRAMES = 30;
const ROSTER_SALT = 0x5bd1e995;

type Phase = "muster" | "battle" | "result";

const params = new URLSearchParams(location.search);
const rosterMode = parseRosterMode(params.get("fleets"));
const pinnedSeed = params.has("seed") ? Number(params.get("seed")) : null;
const warmup = Math.max(0, Number(params.get("warmup") ?? 0));
const speed = Math.min(32, Math.max(1, Number(params.get("speed") ?? 1) || 1));
let showDetails = params.has("details");

const nav = mountNav("live", true);
const hud = new Hud();
const muster = new Muster(document.getElementById("muster")!);
const world = new World(document.body);

let bundle: Bundle;
let pending: Bundle | null = null;
let failedBundleId: string | null = null;
let checking = false;
const thumbnails: Record<string, [string, string]> = {};

let match: LiveMatch | null = null;
let roster: Roster | null = null;
let phase: Phase = "muster";
let phaseTime = 0;
let accumulator = 0;
let matchNumber = 0;
let nextSeed = pinnedSeed ?? crypto.getRandomValues(new Uint32Array(1))[0]! % 1_000_000_000;
const tally: Tally = { wins: [0, 0], draws: 0 };
let lastTime = performance.now();
let framesSinceLayout = 0;
let paused = false;
let thrusterCounts: number[] = [];

// ---- Layout: the HUD sits under the nav; the camera frames the band between. ----
function layout(): void {
  const w = window.innerWidth;
  const h = window.innerHeight;
  document.documentElement.style.setProperty("--nav-bottom", `${Math.round(nav.getBoundingClientRect().bottom)}px`);
  const top = hud.top.getBoundingClientRect().bottom + HUD_CLEARANCE;
  const bottom = hud.bottom.getBoundingClientRect().top - HUD_CLEARANCE;
  world.resize(w, h, top, Math.max(top + 100, bottom));
}
window.addEventListener("resize", layout);

// ---- Bundle: load, re-check, swap only between matches. ----
function applyBundle(b: Bundle): void {
  bundle = b;
  const missing = b.catalogue.hulls.map(([name]) => name).filter((n) => !thumbnails[n] && hullSpec(n));
  if (missing.length) Object.assign(thumbnails, world.thumbnails(missing));
  hud.setCaption(b.manifest);
}

/** Load a bundle and check this page can draw every hull it may draft. */
async function loadDrawable(manifest: BundleManifest): Promise<Bundle> {
  const b = await loadBundle(BUNDLE_BASE, manifest);
  const missing = b.manifest.roster.hulls.filter((h) => !hullSpec(h));
  if (missing.length) throw new Error(`bundle ${b.manifest.bundle_id} rosters hulls this page has no model for: ${missing.join(", ")}`);
  return b;
}

/** Look for a new bundle and preload it; a failed load keeps the current one. */
async function checkBundle(retryFailed: boolean): Promise<void> {
  if (checking) return;
  checking = true;
  let id: string | null = null;
  try {
    const manifest = await fetchManifest(BUNDLE_BASE);
    id = manifest.bundle_id;
    const newest = pending?.manifest.bundle_id ?? bundle.manifest.bundle_id;
    if (id === newest || (id === failedBundleId && !retryFailed)) return;
    pending = await loadDrawable(manifest);
    failedBundleId = null;
    console.info(`live: bundle ${id} loaded; it takes over at the next match`);
  } catch (err) {
    failedBundleId = id;
    console.warn(`live: keeping bundle ${bundle.manifest.bundle_id}; the new one failed to load`, err);
  } finally {
    checking = false;
  }
}

// ---- Match lifecycle ----
function startMatch(): void {
  if (pending) {
    applyBundle(pending);
    pending = null;
  }
  const seed = nextSeed;
  nextSeed = (nextSeed + 1) % 1_000_000_000;
  roster = chooseRoster(rosterMode, bundle.manifest.roster, bundle.catalogue.info, mulberry32(seed ^ ROSTER_SALT));
  const next = new LiveMatch({ ...bundle, settings: bundle.manifest.match, fleets: roster.fleets, seed });
  world.setArena(next.arenaRadius);
  world.beginMatch(next);
  match?.free();
  match = next;
  thrusterCounts = next.hullNames.map((n) => hullSpec(n)?.thrusters.length ?? 0);
  hud.resetMarkers(next.nShips);
  hud.hideResult();
  matchNumber += 1;
  phase = "muster";
  phaseTime = 0;
  muster.show({ number: matchNumber, roster, info: bundle.catalogue.info, thumbnails, duration: MUSTER_SECONDS });
}

function beginBattle(): void {
  muster.hide();
  phase = "battle";
  phaseTime = 0;
  accumulator = 0;
}

function finishMatch(m: LiveMatch): void {
  phase = "result";
  phaseTime = 0;
  const w = m.winner;
  if (w === 0 || w === 1) tally.wins[w] += 1;
  else tally.draws += 1;
  hud.setTally(tally);
  hud.showResult(m);
  void checkBundle(false);
}

function stepSim(m: LiveMatch, quiet: boolean): void {
  world.beforeStep();
  m.step();
  world.dispatch(m.events, quiet);
}

/** Silently play the first `seconds` of the current match (screenshots). */
function fastForward(seconds: number): void {
  if (!match) return;
  beginBattle();
  for (let i = 0; i < seconds * SIM_HZ && !match.over; i++) {
    stepSim(match, true);
    world.advanceWrecks(SIM_DT);
  }
  world.settle();
  if (match.over) finishMatch(match);
}

// ---- Frame loop ----
function statusLine(m: LiveMatch): string {
  const size = `${m.fleets[0].length}v${m.fleets[1].length}`;
  let text: string;
  if (phase === "muster") text = `${size} · jumping in`;
  else if (phase === "battle") text = `${size} · ${Math.max(0, (m.settings.time_limit_ticks - m.tick) / SIM_HZ).toFixed(0)} s left`;
  else text = `next match in ${Math.max(0, Math.ceil(RESULT_HOLD - phaseTime))} s`;
  return `MATCH ${matchNumber} · ${text}`;
}

function frame(now: number): void {
  const realDt = Math.min(0.1, (now - lastTime) / 1000);
  lastTime = now;
  // A paused page (debug hook, for screenshots) keeps drawing the same instant.
  const dt = paused ? 0 : realDt * speed;
  phaseTime += dt;
  const m = match;
  if (m && phase === "muster") {
    if (muster.update(phaseTime)) beginBattle();
  } else if (m && phase === "battle") {
    accumulator += dt;
    let ticks = 0;
    while (accumulator >= SIM_DT && !m.over && ticks < MAX_TICKS_PER_FRAME * speed) {
      stepSim(m, false);
      accumulator -= SIM_DT;
      ticks += 1;
    }
    if (accumulator >= SIM_DT) accumulator = 0;
    if (m.over) finishMatch(m);
  } else if (phase === "result" && phaseTime >= RESULT_HOLD) {
    startMatch();
  }
  const alpha = phase === "battle" ? Math.min(1, accumulator / SIM_DT) : 1;
  if (++framesSinceLayout >= LAYOUT_INTERVAL_FRAMES) {
    framesSinceLayout = 0;
    layout();
  }
  world.frame(dt, alpha, phase === "result");
  if (match) {
    hud.updateMarkers(match, showDetails, (i) => world.shipOnScreen(i, window.innerWidth, window.innerHeight), thrusterCounts);
    hud.setMeta(statusLine(match), `seed ${match.seed} · ${bundle.manifest.champion.name} · ${bundle.manifest.bundle_id.slice(0, 8)}`);
  }
  hud.updatePerf(dt, realDt, match, showDetails);
  requestAnimationFrame(frame);
}

// ---- Controls ----
function setDetails(on: boolean): void {
  showDetails = on;
  hud.setDetails(on);
  const u = new URL(location.href);
  if (on) u.searchParams.set("details", "");
  else u.searchParams.delete("details");
  history.replaceState(null, "", u);
}
hud.detailsBtn.addEventListener("click", () => setDetails(!showDetails));

// Meant to be left running; keep the screen awake where the browser allows.
function keepAwake(): void {
  navigator.wakeLock?.request("screen").catch((err: Error) => console.info("live: wake lock unavailable:", err.message));
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") keepAwake();
});

if (params.has("debug")) {
  (window as unknown as { rlfLive: unknown }).rlfLive = {
    stats: () => ({
      matches: matchNumber,
      phase,
      phaseTime,
      tick: match?.tick ?? 0,
      tally: { ...tally, wins: [...tally.wins] },
      bundle: bundle?.manifest.bundle_id,
      gpu: world.gpuStats(),
    }),
    pause: (on = true) => {
      paused = on;
    },
  };
}

async function boot(): Promise<void> {
  hud.setDetails(showDetails);
  hud.setTally(tally);
  layout();
  try {
    const manifest = await fetchManifest(BUNDLE_BASE);
    applyBundle(await loadDrawable(manifest));
  } catch (err) {
    console.error(err);
    hud.fail(`Could not load the pilot: ${err instanceof Error ? err.message : String(err)}. Retrying in a minute.`);
    setTimeout(() => location.reload(), BOOT_RETRY_MS);
    return;
  }
  startMatch();
  if (warmup > 0) fastForward(warmup);
  layout();
  keepAwake();
  setInterval(() => void checkBundle(true), BUNDLE_RECHECK_MS);
  lastTime = performance.now();
  requestAnimationFrame(frame);
}

void boot();
