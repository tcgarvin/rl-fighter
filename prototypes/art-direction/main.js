import * as THREE from "three";
import { ScriptedBattle, SIM_DT } from "./sim.js";
import { TREATMENTS } from "./treatments/index.js";

const CAMERA_PITCH = (58 * Math.PI) / 180;
const CAMERA_FOV = 32;
const MIN_FRAME_SPAN = 160; // metres across, so a lone duel isn't framed absurdly close
const FRAME_MARGIN = 25;
const FOCUS_MARGIN = 14;
// Tap-to-follow keeps some surroundings in frame, and accepts taps this close to a ship.
const FOLLOW_MARGIN = 45;
const TAP_RADIUS_PX = 36;
// Gap kept between the action and the HUD bars, in CSS pixels.
const HUD_CLEARANCE = 10;
const SAFE_NDC_X = 0.92;
// Re-measure the HUD this often (frames); measuring every frame would force a layout.
const HUD_MEASURE_INTERVAL = 30;
// Jump-in: the hull streaks in from this far behind its arrival point over this long.
const JUMP_DISTANCE = 900;
const JUMP_DURATION = 0.055;

const params = new URLSearchParams(location.search);
const treatmentId = TREATMENTS[0].id;
const seed = Number(params.get("seed") ?? 1);
// Fast-forward this many simulated seconds before the first frame (used for screenshots).
const warmup = Number(params.get("warmup") ?? 0);
// Close-up on one ship id, for judging hull models. Tapping a ship sets followId instead.
const focusId = params.has("focus") ? Number(params.get("focus")) : null;
let followId = null;
let followReleaseAt = null;
let showDetails = params.has("details");

/** Import a shared module, falling back to its stub so one broken module can't blank the page. */
async function importShared(name) {
  try {
    return await import(`./shared/${name}.js`);
  } catch (err) {
    console.error(`shared/${name}.js failed to load; using stub`, err);
    return import(`./shared/stubs/${name}.js`);
  }
}

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
// Phones report DPR 3; 2 is visually indistinguishable at these sizes and much cheaper.
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CAMERA_FOV, window.innerWidth / window.innerHeight, 1, 60000);

const [treatmentModule, hullgeo, environmentModule, effectsModule] = await Promise.all([
  import(`./treatments/${treatmentId}.js`),
  importShared("hullgeo"),
  importShared("environment"),
  importShared("effects"),
]);
const treatment = treatmentModule.default;
applyHud(treatment);
treatment.init({ THREE, scene, renderer, camera });
const environment = environmentModule.createEnvironment({ THREE, scene, camera, renderer });
const effects = effectsModule.createEffects({ THREE, scene, camera, renderer, palette: treatment.palette });

const battle = new ScriptedBattle(seed);
buildSwitcher();
for (let i = 0; i < warmup / SIM_DT; i++) battle.step();
const shipViews = new Map();
let viewMatch = -1;
const camState = { x: 0, y: 0, dist: 800, extent: 300, initialized: false };
let previous = snapshot(battle);
let accumulator = 0;
let lastTime = performance.now();
let elapsed = 0;

// The vertical band of the screen not covered by HUD, in NDC (top > bottom).
const safeBand = { top: 0.8, bottom: -0.8 };

/** Measure the HUD and shift the projection so the camera target sits mid-band. */
function measureSafeBand() {
  const h = window.innerHeight;
  const topPx = document.getElementById("topbar").getBoundingClientRect().bottom + HUD_CLEARANCE;
  const bottomEls = ["styles"].map((id) => document.getElementById(id)).filter((el) => el.offsetParent !== null);
  const bottomPx = Math.min(h, ...bottomEls.map((el) => el.getBoundingClientRect().top)) - HUD_CLEARANCE;
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
onResize();
let framesSinceMeasure = 0;

window.addEventListener("keydown", (e) => {
  if (e.key === "d" || e.key === "D") toggleDetails();
});

const tapPoint = new THREE.Vector3();

/** Tap a ship to follow it; tap empty space to go back to framing the whole battle. */
renderer.domElement.addEventListener("pointerdown", (e) => {
  let best = null;
  let bestDist = TAP_RADIUS_PX;
  for (const ship of battle.ships) {
    if (!ship.alive || !ship.present) continue;
    tapPoint.set(ship.x, 0, -ship.y).project(camera);
    const sx = ((tapPoint.x + 1) / 2) * window.innerWidth;
    const sy = ((1 - tapPoint.y) / 2) * window.innerHeight;
    const d = Math.hypot(sx - e.clientX, sy - e.clientY);
    if (d < bestDist) {
      bestDist = d;
      best = ship.id;
    }
  }
  followId = best;
  followReleaseAt = null;
});

function snapshot(b) {
  return new Map(b.ships.map((s) => [s.id, { x: s.x, y: s.y, heading: s.heading }]));
}

function disposeShipViews() {
  for (const v of shipViews.values()) {
    scene.remove(v.model.object);
    v.damage.dispose();
    v.model.dispose();
  }
  shipViews.clear();
}

function syncShips() {
  if (viewMatch === battle.matchIndex) return;
  disposeShipViews();
  for (const ship of battle.ships) {
    const model = hullgeo.buildHull(ship.hull, ship.team, treatment.materials(ship.team));
    model.object.visible = false;
    scene.add(model.object);
    // Ships already present (e.g. after a warmup) count as having finished their jump.
    shipViews.set(ship.id, { model, damage: effects.attachDamage(model), jumpStart: -Infinity });
  }
  viewMatch = battle.matchIndex;
  followId = null;
  previous = snapshot(battle);
  environment.newMatch(seed * 1000 + battle.matchIndex);
  showMuster();
}

function lerpAngle(a, b, t) {
  return a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * t;
}

function dispatchEvents() {
  const ev = battle.events;
  for (const e of ev.arrivals) {
    const ship = battle.ships[e.id];
    const view = shipViews.get(e.id);
    if (view) view.jumpStart = elapsed;
    effects.arrival({ ...e, size: ship.hull.length, duration: JUMP_DURATION });
  }
  for (const e of ev.muzzles) effects.muzzle(e);
  for (const e of ev.hits) effects.hit(e);
  for (const e of ev.shieldHits) effects.shieldHit({ ...e, radius: battle.ships[e.targetId].hull.shield.radius });
  for (const e of ev.explosions) effects.explosion(e);
}

function frame(now) {
  const dt = Math.min(0.1, (now - lastTime) / 1000);
  lastTime = now;
  elapsed += dt;
  accumulator += dt;
  const phaseBefore = battle.phase;
  while (accumulator >= SIM_DT) {
    previous = snapshot(battle);
    battle.step();
    syncShips();
    dispatchEvents();
    accumulator -= SIM_DT;
  }
  if (phaseBefore !== battle.phase && battle.phase === "intermission") showResult();
  const alpha = accumulator / SIM_DT;
  syncShips();

  const bounds = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
  for (const ship of battle.ships) {
    const v = shipViews.get(ship.id);
    if (!v) continue;
    const prev = previous.get(ship.id) ?? ship;
    let x = prev.x + (ship.x - prev.x) * alpha;
    let y = prev.y + (ship.y - prev.y) * alpha;
    const heading = lerpAngle(prev.heading, ship.heading, alpha);
    const jumpT = (elapsed - v.jumpStart) / JUMP_DURATION;
    if (jumpT < 1) {
      // Streak in along the heading, decelerating hard into the arrival point.
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
    v.model.turrets.forEach((pivot, i) => (pivot.rotation.y = ship.turretAngles[i]));
    v.damage.update(ship.hp / ship.maxHp, visible, dt);
    if (ship.alive) {
      // Ships yet to jump in still count, so the empty field is framed where they'll appear.
      bounds.minX = Math.min(bounds.minX, ship.x);
      bounds.maxX = Math.max(bounds.maxX, ship.x);
      bounds.minY = Math.min(bounds.minY, ship.y);
      bounds.maxY = Math.max(bounds.maxY, ship.y);
    }
  }
  effects.updateProjectiles(battle.projectiles, battle.beams, alpha);
  if (++framesSinceMeasure >= HUD_MEASURE_INTERVAL) {
    framesSinceMeasure = 0;
    measureSafeBand();
  }
  updateCamera(bounds, dt);
  environment.update(dt, { centerX: camState.x, centerY: camState.y, extent: camState.extent });
  effects.update(dt, elapsed);
  treatment.render(renderer, scene, camera, dt);
  updateHud();
  if (showDetails) updateDetails();
  requestAnimationFrame(frame);
}

function placeCamera(x, y, dist) {
  camera.position.set(x, Math.sin(CAMERA_PITCH) * dist, -y + Math.cos(CAMERA_PITCH) * dist);
  camera.lookAt(x, 0, -y);
  camera.updateMatrixWorld();
}

const corner = new THREE.Vector3();

/** Distance at which the box fits inside the HUD-safe band of the view. */
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
  // Under perspective the projected size scales inversely with distance, close enough to linear here.
  return probe * extent;
}

function updateCamera(b, dt) {
  let { minX, maxX, minY, maxY } = b;
  const targetId = focusId ?? followId;
  const target = targetId === null ? null : battle.ships.find((s) => s.id === targetId);
  if (target && !target.alive && followId !== null) {
    // The followed ship died: hold on its wreck briefly, then release.
    followReleaseAt ??= battle.time + 1.5;
    if (battle.time > followReleaseAt) followId = null;
  }
  if (target) {
    minX = maxX = target.x;
    minY = maxY = target.y;
  }
  if (Number.isFinite(minX)) {
    const margin = focusId !== null ? FOCUS_MARGIN : target ? FOLLOW_MARGIN : FRAME_MARGIN;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const half = target ? 0 : MIN_FRAME_SPAN / 2;
    const box = [
      Math.min(minX - margin, cx - half),
      Math.max(maxX + margin, cx + half),
      Math.min(minY - margin, cy - half),
      Math.max(maxY + margin, cy + half),
    ];
    const needed = fitDistance(cx, cy, ...box);
    // Snap on the first frame so screenshots and page loads start framed.
    const k = camState.initialized ? 1 - Math.exp(-dt * 1.5) : 1;
    camState.initialized = true;
    camState.x += (cx - camState.x) * k;
    camState.y += (cy - camState.y) * k;
    camState.dist += (needed - camState.dist) * k;
    camState.extent = Math.max(box[1] - box[0], box[3] - box[2]) / 2;
  }
  placeCamera(camState.x, camState.y, camState.dist);
}

function applyHud(t) {
  for (const [k, v] of Object.entries(t.hud ?? {})) document.documentElement.style.setProperty(k, v);
  for (const href of t.fonts ?? []) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.append(link);
  }
}

function buildSwitcher() {
  const el = document.getElementById("styles");
  const details = document.createElement("button");
  details.id = "details-toggle";
  details.type = "button";
  details.textContent = "Technical details";
  details.setAttribute("aria-pressed", String(showDetails));
  details.addEventListener("click", toggleDetails);
  el.append(details);

  // Replays the jump-in without waiting for the match to end.
  const restart = document.createElement("button");
  restart.type = "button";
  restart.textContent = "Restart match";
  restart.addEventListener("click", () => battle.startMatch());
  el.prepend(restart);
}

function toggleDetails() {
  showDetails = !showDetails;
  document.getElementById("details-toggle").setAttribute("aria-pressed", String(showDetails));
  detailsLayer.hidden = !showDetails;
}

const scoreEl = document.getElementById("score");
const metaEl = document.getElementById("meta");
const bannerEl = document.getElementById("banner");
const detailsLayer = document.getElementById("details");
detailsLayer.hidden = !showDetails;
const detailLabels = [];
const labelPos = new THREE.Vector3();
let bannerTimer = 0;

function updateHud() {
  const a = battle.aliveCount(0);
  const b = battle.aliveCount(1);
  scoreEl.innerHTML = `<span class="team-a">▲ AZURE ${a}</span> &nbsp;·&nbsp; <span class="team-b">${b} EMBER ■</span>`;
  const following = followId === null ? "" : `  ·  FOLLOWING ${battle.ships[followId].hullName.toUpperCase()} #${followId}`;
  metaEl.textContent = `MATCH ${battle.matchIndex}  ·  T+${battle.time.toFixed(0)}s  ·  SCRIPTED (NO RL)${following}`;
}

/** Per-ship readouts for the "Technical details" toggle: HP, shield and throttles. */
function updateDetails() {
  battle.ships.forEach((ship, i) => {
    let el = detailLabels[i];
    if (!el) {
      el = document.createElement("div");
      detailsLayer.append(el);
      detailLabels[i] = el;
    }
    const v = shipViews.get(ship.id);
    if (!v || !ship.alive || !ship.present) {
      el.hidden = true;
      return;
    }
    labelPos.setFromMatrixPosition(v.model.object.matrixWorld).project(camera);
    el.hidden = false;
    // Keep labels on screen: flip to the ship's left when they'd run off the right edge.
    const sx = ((labelPos.x + 1) / 2) * window.innerWidth;
    const sy = ((1 - labelPos.y) / 2) * window.innerHeight;
    const width = el.offsetWidth || 120;
    const lx = sx + 14 + width > window.innerWidth ? sx - 14 - width : sx + 14;
    el.style.transform = `translate(${Math.max(4, lx)}px, ${sy - 10}px)`;
    const throttles = ship.throttles.map((t) => (t === 1 ? "█" : t > 0 ? "▄" : "·")).join("");
    const shield = ship.maxShield > 0 ? ` · SH ${Math.ceil(ship.shield)}/${ship.maxShield}` : "";
    el.className = `ship-label ${ship.team === 0 ? "team-a" : "team-b"}`;
    el.textContent = `${ship.hullName.toUpperCase()} #${ship.id}\nHP ${Math.ceil(ship.hp)}/${ship.maxHp}${shield}\nTHR ${throttles}`;
  });
  for (let i = battle.ships.length; i < detailLabels.length; i++) detailLabels[i].hidden = true;
}

function rosterText(roster) {
  const counts = {};
  for (const h of roster) counts[h] = (counts[h] ?? 0) + 1;
  return Object.entries(counts)
    .map(([h, n]) => `${n}× ${h.toUpperCase()}`)
    .join("<br>");
}

function showBanner(html, seconds) {
  bannerEl.innerHTML = html;
  bannerEl.classList.add("show");
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => bannerEl.classList.remove("show"), seconds * 1000);
}

function showMuster() {
  showBanner(
    `MATCH ${battle.matchIndex} — MUSTER<div class="rosters"><div class="team-a">${rosterText(battle.rosters[0])}</div><div class="team-b">${rosterText(battle.rosters[1])}</div></div>`,
    2.2,
  );
}

function showResult() {
  const w = battle.winner;
  const text = w === 0 ? `<span class="team-a">AZURE HOLDS THE FIELD</span>` : w === 1 ? `<span class="team-b">EMBER HOLDS THE FIELD</span>` : "STALEMATE";
  showBanner(text, 3.5);
}

// The demo is meant to be left running on a screen; keep it awake where the browser allows.
navigator.wakeLock?.request("screen").catch((err) => console.info("Wake lock unavailable:", err.message));

syncShips();
requestAnimationFrame(frame);
