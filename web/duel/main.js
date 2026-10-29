// Live duel page: the Rust sim (WASM) and the learned pilot (policy.js) run here on
// the main thread at 30 Hz; rendering interpolates between ticks with the story
// demo's cinematic treatment, hull models and effects (served from the site root).
import * as THREE from "three";
import init, * as sim from "./pkg/sim_wasm.js";
import { createPolicy } from "./policy.js";
import { Duel, MODES, SIM_DT, TICK_BUDGET_MS, simLayout } from "./duel.js";
import { HULLS } from "../hulls.js";
import treatment from "../treatments/cinematic.js";
import * as hullgeo from "../shared/hullgeo.js";
import { createEffects } from "../shared/effects.js";
import { createEnvironment } from "../shared/environment.js";

// Camera (DESIGN §9 camera v1), as in prototypes/story/main.js.
const CAMERA_PITCH = (58 * Math.PI) / 180;
const CAMERA_FOV = 32;
const MIN_FRAME_SPAN = 150; // metres: a merge at point-blank range isn't framed absurdly close
const FRAME_MARGIN = 28;
const HUD_CLEARANCE = 10;
const SAFE_NDC_X = 0.88;
const HUD_MEASURE_INTERVAL = 30;
// Jump-in streak, as in the story.
const JUMP_DISTANCE = 900;
const JUMP_DURATION = 0.055;
// The wreck burns this long under the result banner before the next match.
const RESULT_HOLD = 3.5;
const DEATH_RADIUS_SCALE = 2.5;
const PERF_INTERVAL = 0.25;

const CAPTIONS = {
  "learned-vs-script": `<span class="team-a">Blue</span> is a neural network flying by thruster and trigger, trained overnight; <span class="team-b">orange</span> is the hand-written script.`,
  "learned-vs-learned": `Both ships are the same neural network, flying by thruster and trigger, trained overnight: <span class="team-a">blue</span> against a copy of itself in <span class="team-b">orange</span>.`,
};

const params = new URLSearchParams(location.search);
let mode = MODES[params.get("mode")] ? params.get("mode") : "learned-vs-script";
// A pinned ?seed= replays the same matches; otherwise every visit is fresh.
let nextSeed = params.has("seed") ? Number(params.get("seed")) : crypto.getRandomValues(new Uint32Array(1))[0] % 1_000_000_000;
let showDetails = params.has("details");
// Fast-forward this many simulated seconds into the first match (screenshots).
const warmup = Number(params.get("warmup") ?? 0);

const metaEl = document.getElementById("meta");
const tallyEl = document.getElementById("tally");
const perfEl = document.getElementById("perf");
const bannerEl = document.getElementById("banner");
const captionEl = document.getElementById("caption");
const tagsEl = document.getElementById("tags");

function fail(err) {
  console.error(err);
  metaEl.textContent = `failed to start: ${err.message ?? err}`;
}

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.prepend(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CAMERA_FOV, window.innerWidth / window.innerHeight, 1, 60000);
treatment.init({ THREE, scene, renderer, camera });
const environment = createEnvironment({ THREE, scene, camera, renderer });
const effects = createEffects({ THREE, scene, camera, renderer, palette: treatment.palette });

async function fetchOk(url, kind) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res[kind]();
}

const [, manifest, weights, catalogue] = await Promise.all([
  init({ module_or_path: new URL("./pkg/sim_wasm_bg.wasm", import.meta.url) }),
  fetchOk("./policy/manifest.json", "json"),
  fetchOk("./policy/weights.bin", "arrayBuffer"),
  fetchOk("./assets/catalogue.json", "json"),
]).catch((err) => {
  fail(err);
  throw err;
});
const layout = simLayout(sim);
const policy = createPolicy(manifest, weights, layout);
const hullNames = catalogue.hulls.map(([name]) => name).sort();
const duel = new Duel({ sim, catalogue, policy, matchConfig: manifest.match_config });

const tallies = Object.fromEntries(Object.keys(MODES).map((k) => [k, { 0: 0, 1: 0, draw: 0 }]));
const views = [];
let previous = [];
let matchNumber = 0;
let resultAt = null;
let accumulator = 0;
let lastTime = performance.now();
let elapsed = 0;
let beams = [];
const camState = { x: 0, y: 0, dist: 800, extent: 300, initialized: false };
const perf = { fps: 60, nextUpdate: 0 };

// ---- Arena edge: a faint ring at the arena radius (leaving it drains hull). ----
{
  const r = manifest.match_config.arena_radius;
  const pts = [];
  for (let i = 0; i <= 256; i++) {
    const a = (i / 256) * Math.PI * 2;
    pts.push(new THREE.Vector3(Math.cos(a) * r, 0, -Math.sin(a) * r));
  }
  const ring = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: 0x8c99a8, transparent: true, opacity: 0.18, depthWrite: false }),
  );
  scene.add(ring);
}

// ---- HUD layout: keep the action in the band between the top bar and the bottom panel. ----
const safeBand = { top: 0.8, bottom: -0.8 };
function measureSafeBand() {
  const h = window.innerHeight;
  const topPx = document.getElementById("topbar").getBoundingClientRect().bottom + HUD_CLEARANCE;
  const bottomPx = document.getElementById("bottom").getBoundingClientRect().top - HUD_CLEARANCE;
  safeBand.top = 1 - (2 * topPx) / h;
  safeBand.bottom = 1 - (2 * bottomPx) / h;
  const bandCenterPx = (topPx + bottomPx) / 2;
  camera.setViewOffset(window.innerWidth, h, 0, h / 2 - bandCenterPx, window.innerWidth, h);
}
function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  renderer.setSize(window.innerWidth, window.innerHeight);
  measureSafeBand();
  camera.updateProjectionMatrix();
  treatment.onResize?.(window.innerWidth, window.innerHeight);
}
window.addEventListener("resize", onResize);
let framesSinceMeasure = 0;

// ---- Controls ----
const modesEl = document.getElementById("modes");
for (const [key, m] of Object.entries(MODES)) {
  const b = document.createElement("button");
  b.type = "button";
  b.dataset.mode = key;
  b.textContent = m.label;
  b.addEventListener("click", () => {
    if (key === mode) return;
    mode = key;
    syncControls();
    startMatch();
  });
  modesEl.append(b);
}
const detailsBtn = document.getElementById("details-toggle");
detailsBtn.addEventListener("click", () => {
  showDetails = !showDetails;
  syncControls();
});
function syncControls() {
  for (const b of modesEl.children) b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
  detailsBtn.setAttribute("aria-pressed", String(showDetails));
  captionEl.innerHTML = CAPTIONS[mode];
  const u = new URL(location.href);
  u.searchParams.set("mode", mode);
  history.replaceState(null, "", u);
}

// ---- Match lifecycle ----
function controllerName(k) {
  return MODES[mode].controllers[k] === "learned" ? "LEARNED" : "SCRIPT";
}

function startMatch() {
  for (const v of views) {
    v.damage.dispose();
    v.model.dispose();
    v.tag.remove();
  }
  views.length = 0;
  matchNumber += 1;
  duel.start(mode, nextSeed);
  nextSeed = (nextSeed + 1) % 1_000_000_000;
  for (const ship of duel.ships) {
    const hull = HULLS[hullNames[ship.hull]];
    const model = hullgeo.buildHull(hull, ship.team, treatment.materials(ship.team));
    model.object.visible = false;
    scene.add(model.object);
    const tag = document.createElement("div");
    tag.className = `tag ${ship.team === 0 ? "team-a" : "team-b"}`;
    tagsEl.append(tag);
    views.push({ model, hull, damage: effects.attachDamage(model), jumpStart: -Infinity, tag, label: controllerName(ship.id) });
  }
  previous = snapshot();
  environment.newMatch(duel.seed);
  resultAt = null;
  beams = [];
  bannerEl.classList.remove("show");
  accumulator = 0;
}

function snapshot() {
  return duel.ships.map((s) => ({ x: s.x, y: s.y, heading: s.heading }));
}

function dispatchEvents() {
  beams = [];
  for (const e of duel.events) {
    const shooter = duel.ships[e.b];
    switch (e.kind) {
      case "fire":
        effects.muzzle({ x: e.x, y: e.y, angle: e.extra, team: duel.ships[e.a].team, weapon: "gauss" });
        break;
      case "beam":
        beams.push({ x1: e.x, y1: e.y, x2: e.f5, y2: e.f6, team: duel.ships[e.a].team, ttl: 0.06 });
        break;
      case "hit":
        effects.hit({ x: e.x, y: e.y, team: shooter?.team ?? 0, targetId: e.a });
        break;
      case "shieldHit":
        effects.shieldHit({ x: e.x, y: e.y, nx: e.f5, ny: e.f6, team: shooter?.team ?? 0, depleted: e.extra > 0.5, radius: views[e.a].hull.shield?.radius ?? 8 });
        break;
      case "burst":
        effects.explosion({ x: e.x, y: e.y, radius: e.extra, team: e.a, kind: "flak" });
        break;
      case "death":
        effects.explosion({ x: e.x, y: e.y, radius: views[e.a].hull.radius * DEATH_RADIUS_SCALE, team: duel.ships[e.a].team, kind: "death" });
        break;
      case "arrival":
        views[e.a].jumpStart = elapsed;
        effects.arrival({ x: e.x, y: e.y, heading: e.extra, team: duel.ships[e.a].team, size: views[e.a].hull.length, duration: JUMP_DURATION });
        break;
    }
  }
}

function stepSim() {
  previous = snapshot();
  duel.step();
  dispatchEvents();
  if (duel.over) finishMatch();
}

function finishMatch() {
  resultAt = elapsed;
  const w = duel.winner;
  const tally = tallies[mode];
  tally[w === -1 ? "draw" : w] += 1;
  let title;
  if (w === -1) title = "DRAW";
  else if (mode === "learned-vs-script") title = w === 0 ? `<span class="team-a">LEARNED PILOT WINS</span>` : `<span class="team-b">SCRIPT WINS</span>`;
  else title = w === 0 ? `<span class="team-a">BLUE WINS</span>` : `<span class="team-b">ORANGE WINS</span>`;
  const sub = w === -1 ? "time ran out" : `in ${(duel.tick / 30).toFixed(0)} s · next match shortly`;
  bannerEl.innerHTML = `<div class="title">${title}</div><div class="sub">${sub}</div>`;
  bannerEl.classList.add("show");
}

// ---- Frame loop ----
function lerpAngle(a, b, t) {
  return a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * t;
}

const tagPos = new THREE.Vector3();

function frame(now) {
  const dt = Math.min(0.1, (now - lastTime) / 1000);
  lastTime = now;
  elapsed += dt;
  if (resultAt === null) {
    accumulator += dt;
    while (accumulator >= SIM_DT && resultAt === null) {
      stepSim();
      accumulator -= SIM_DT;
    }
  } else if (elapsed - resultAt > RESULT_HOLD) {
    startMatch();
  }
  const alpha = resultAt === null ? accumulator / SIM_DT : 1;

  const bounds = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
  duel.ships.forEach((ship, i) => {
    const v = views[i];
    const prev = previous[i] ?? ship;
    let x = prev.x + (ship.x - prev.x) * alpha;
    let y = prev.y + (ship.y - prev.y) * alpha;
    const heading = lerpAngle(prev.heading, ship.heading, alpha);
    const jumpT = (elapsed - v.jumpStart) / JUMP_DURATION;
    if (jumpT < 1) {
      const back = JUMP_DISTANCE * (1 - jumpT) ** 3;
      x -= Math.cos(heading) * back;
      y -= Math.sin(heading) * back;
    }
    const visible = ship.alive && ship.present;
    const obj = v.model.object;
    obj.visible = visible;
    obj.position.set(x, 0, -y);
    obj.rotation.y = heading;
    obj.updateMatrixWorld();
    v.model.setThrottles(ship.throttles, dt);
    v.model.turrets.forEach((pivot, k) => (pivot.rotation.y = ship.turretAngles[k]));
    v.damage.update(Math.max(0, ship.hp) / duel.maxHp[i], visible, dt);
    // Ships yet to jump in count too, so the empty field is framed where they'll appear.
    if (ship.alive) {
      bounds.minX = Math.min(bounds.minX, ship.x);
      bounds.maxX = Math.max(bounds.maxX, ship.x);
      bounds.minY = Math.min(bounds.minY, ship.y);
      bounds.maxY = Math.max(bounds.maxY, ship.y);
    }
  });
  if (!Number.isFinite(bounds.minX)) Object.assign(bounds, { minX: -60, maxX: 60, minY: -60, maxY: 60 });

  // Projectiles are at the current tick and ships are drawn between the previous and
  // current one, so back the shots up by a tick to keep them on the muzzles.
  effects.updateProjectiles(duel.projectiles, beams, alpha - 1);
  if (++framesSinceMeasure >= HUD_MEASURE_INTERVAL) {
    framesSinceMeasure = 0;
    measureSafeBand();
  }
  updateCamera(bounds, dt);
  environment.update(dt, { centerX: camState.x, centerY: camState.y, extent: camState.extent });
  effects.update(dt, elapsed);
  treatment.render(renderer, scene, camera, dt);
  updateTags();
  updateHud(dt);
  requestAnimationFrame(frame);
}

// Portrait screens turn the camera 90° so the teams' approach axis (sim x) runs up the
// screen instead of across its narrow width (as in the story).
function placeCamera(x, y, dist) {
  const back = Math.cos(CAMERA_PITCH) * dist;
  const portrait = window.innerHeight > window.innerWidth;
  if (portrait) camera.position.set(x - back, Math.sin(CAMERA_PITCH) * dist, -y);
  else camera.position.set(x, Math.sin(CAMERA_PITCH) * dist, -y + back);
  camera.lookAt(x, 0, -y);
  camera.updateMatrixWorld();
}

const corner = new THREE.Vector3();
function fitDistance(cx, cy, minX, maxX, minY, maxY) {
  const probe = Math.max(maxX - minX, maxY - minY, 1) * 2;
  placeCamera(cx, cy, probe);
  const bandCenter = (safeBand.top + safeBand.bottom) / 2;
  const bandHalf = Math.max(0.2, (safeBand.top - safeBand.bottom) / 2);
  let extent = 0;
  for (const [x, y] of [[minX, minY], [minX, maxY], [maxX, minY], [maxX, maxY]]) {
    corner.set(x, 0, -y).project(camera);
    extent = Math.max(extent, Math.abs(corner.x) / SAFE_NDC_X, Math.abs(corner.y - bandCenter) / bandHalf);
  }
  return probe * extent;
}

function updateCamera(b, dt) {
  const cx = (b.minX + b.maxX) / 2;
  const cy = (b.minY + b.maxY) / 2;
  const half = MIN_FRAME_SPAN / 2;
  const box = [
    Math.min(b.minX - FRAME_MARGIN, cx - half),
    Math.max(b.maxX + FRAME_MARGIN, cx + half),
    Math.min(b.minY - FRAME_MARGIN, cy - half),
    Math.max(b.maxY + FRAME_MARGIN, cy + half),
  ];
  const needed = fitDistance(cx, cy, ...box);
  const k = camState.initialized ? 1 - Math.exp(-dt * 1.5) : 1;
  camState.initialized = true;
  camState.x += (cx - camState.x) * k;
  camState.y += (cy - camState.y) * k;
  camState.dist += (needed - camState.dist) * k;
  camState.extent = Math.max(box[1] - box[0], box[3] - box[2]) / 2;
  placeCamera(camState.x, camState.y, camState.dist);
}

// ---- HUD ----
function throttleBar(t) {
  return Array.from(t.subarray(0, 5), (v) => (v > 0.66 ? "█" : v > 0.01 ? "▄" : "·")).join("");
}

function updateTags() {
  const w = window.innerWidth;
  duel.ships.forEach((ship, i) => {
    const v = views[i];
    const el = v.tag;
    // Under the result banner the survivor needs no label.
    if (!ship.alive || !ship.present || resultAt !== null) {
      el.hidden = true;
      return;
    }
    tagPos.setFromMatrixPosition(v.model.object.matrixWorld).project(camera);
    el.hidden = false;
    const sx = ((tagPos.x + 1) / 2) * w;
    const sy = ((1 - tagPos.y) / 2) * window.innerHeight;
    const text = showDetails
      ? `${v.label}<span class="stats">HP ${Math.ceil(ship.hp)}/${duel.maxHp[i]}\nTHR ${throttleBar(ship.throttles)}\nPWR E${Math.round(ship.power[1] * 100)} W${Math.round(ship.power[2] * 100)}</span>`
      : v.label;
    if (el._text !== text) {
      el.innerHTML = text;
      el._text = text;
    }
    // Below-right of the ship; flip left near the right edge.
    const width = el.offsetWidth || 60;
    const lx = sx + 16 + width > w - 8 ? sx - 16 - width : sx + 16;
    el.style.transform = `translate(${Math.round(Math.max(4, lx))}px, ${Math.round(sy + 6)}px)`;
  });
}

function updateHud(dt) {
  if (dt > 0) perf.fps += (1 / dt - perf.fps) * Math.min(1, dt * 2);
  if (elapsed < perf.nextUpdate) return;
  perf.nextUpdate = elapsed + PERF_INTERVAL;
  const t = tallies[mode];
  const [a, b] = mode === "learned-vs-script" ? ["LEARNED", "SCRIPT"] : ["BLUE", "ORANGE"];
  tallyEl.innerHTML = `<span class="team-a">${a} ${t[0]}</span> · <span class="team-b">${t[1]} ${b}</span>`;
  const left = Math.max(0, (manifest.match_config.time_limit_ticks - duel.tick) / 30);
  const pilot = manifest.source.update != null ? `pilot: update ${manifest.source.update}` : `pilot: ${manifest.source.kind ?? "policy"}`;
  metaEl.textContent = `MATCH ${matchNumber} · ${left.toFixed(0)} s left · ${t.draw} draw${t.draw === 1 ? "" : "s"}${showDetails ? ` · ${pilot} · seed ${duel.seed}` : ""}`;
  const tick = duel.timing.sim + duel.timing.nn;
  const free = Math.max(0, 100 * (1 - tick / TICK_BUDGET_MS));
  const split = showDetails ? `\nsim ${duel.timing.sim.toFixed(2)} · nn ${duel.timing.nn.toFixed(2)} ms` : "";
  perfEl.textContent = `tick ${tick.toFixed(1)} ms\n${free.toFixed(0)}% free · ${perf.fps.toFixed(0)} fps${split}`;
}

// Meant to be left running; keep the screen awake where the browser allows.
navigator.wakeLock?.request("screen").catch((err) => console.info("Wake lock unavailable:", err.message));

syncControls();
onResize();
startMatch();
// Silent warm-up: replaying every event at once would pile up seconds of effects.
for (let i = 0; i < warmup * 30 && !duel.over; i++) duel.step();
previous = snapshot();
for (const v of views) v.jumpStart = -Infinity;
if (duel.over) finishMatch();
requestAnimationFrame(frame);
