import * as THREE from "three";
import { ScriptedBattle, SIM_DT } from "./sim.js";
import { STYLES } from "./styles/index.js";

const MAX_PROJECTILES = 1024;
const CAMERA_PITCH = (58 * Math.PI) / 180;
const CAMERA_FOV = 32;
const MIN_FRAME_SPAN = 160; // metres across, so a lone duel isn't framed absurdly close
const FRAME_MARGIN = 25;
const FOCUS_MARGIN = 14;
// Keep ships out of the top bar and the bottom switcher: fraction of the half-height usable.
const SAFE_NDC_Y = 0.78;

const params = new URLSearchParams(location.search);
// The style comes from the hash (#enamel) so links work where query strings are stripped;
// ?style= remains for headless screenshots.
const requestedStyle = location.hash.slice(1) || params.get("style");
const styleId = STYLES.some((s) => s.id === requestedStyle) ? requestedStyle : STYLES[0].id;
window.addEventListener("hashchange", () => location.reload());
const seed = Number(params.get("seed") ?? 1);
// Fast-forward this many simulated seconds before the first frame (used for screenshots).
const warmup = Number(params.get("warmup") ?? 0);
// Close-up on one ship id, for judging hull models.
const focusId = params.has("focus") ? Number(params.get("focus")) : null;

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CAMERA_FOV, window.innerWidth / window.innerHeight, 1, 20000);

const style = (await import(`./styles/${styleId}.js`)).default;
applyHud(style);
buildSwitcher();
const addons = {};
style.init({ THREE, scene, renderer, camera, addons });
const projectileView = style.createProjectiles(MAX_PROJECTILES);

const battle = new ScriptedBattle(seed);
for (let i = 0; i < warmup / SIM_DT; i++) battle.step();
const shipViews = new Map();
let viewMatch = -1;
const camState = { x: 0, y: 0, dist: 800, initialized: false };
let previous = snapshot(battle);
let accumulator = 0;
let lastTime = performance.now();
let elapsed = 0;

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  style.onResize?.(window.innerWidth, window.innerHeight);
});

function snapshot(b) {
  return new Map(b.ships.map((s) => [s.id, { x: s.x, y: s.y, heading: s.heading }]));
}

function syncShips() {
  if (viewMatch !== battle.matchIndex) {
    for (const v of shipViews.values()) {
      scene.remove(v.object);
      v.dispose();
    }
    shipViews.clear();
    for (const ship of battle.ships) {
      const v = style.createShip({ id: ship.id, hullName: ship.hullName, hull: ship.hull, team: ship.team });
      scene.add(v.object);
      shipViews.set(ship.id, v);
    }
    viewMatch = battle.matchIndex;
    previous = snapshot(battle);
    showMuster();
  }
}

function lerpAngle(a, b, t) {
  return a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * t;
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
    for (const e of battle.events.muzzles) style.onMuzzle(e);
    for (const e of battle.events.hits) style.onHit(e);
    for (const e of battle.events.explosions) style.onExplosion(e);
    accumulator -= SIM_DT;
  }
  if (phaseBefore !== battle.phase && battle.phase === "intermission") showResult();
  const alpha = accumulator / SIM_DT;
  syncShips();

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const ship of battle.ships) {
    const prev = previous.get(ship.id) ?? ship;
    const view = {
      x: prev.x + (ship.x - prev.x) * alpha,
      y: prev.y + (ship.y - prev.y) * alpha,
      heading: lerpAngle(prev.heading, ship.heading, alpha),
      throttles: ship.throttles,
      turretAngles: ship.turretAngles,
      firing: ship.firing,
      hpFrac: ship.hp / ship.maxHp,
      alive: ship.alive && ship.present,
    };
    shipViews.get(ship.id)?.update(view, dt);
    if (ship.alive) {
      minX = Math.min(minX, view.x);
      maxX = Math.max(maxX, view.x);
      minY = Math.min(minY, view.y);
      maxY = Math.max(maxY, view.y);
    }
  }
  projectileView.update(battle.projectiles, battle.beams, alpha);
  updateCamera(minX, maxX, minY, maxY, dt);
  style.update(dt, elapsed);
  style.render(renderer, scene, camera);
  updateHud();
  requestAnimationFrame(frame);
}

function placeCamera(x, y, dist) {
  camera.position.set(x, Math.sin(CAMERA_PITCH) * dist, -y + Math.cos(CAMERA_PITCH) * dist);
  camera.lookAt(x, 0, -y);
  camera.updateMatrixWorld();
}

const corner = new THREE.Vector3();

/** Distance at which the box [minX..maxX]x[minY..maxY] fits inside the HUD-safe part of the view. */
function fitDistance(cx, cy, minX, maxX, minY, maxY) {
  const probe = Math.max(maxX - minX, maxY - minY, 1) * 2;
  placeCamera(cx, cy, probe);
  let extent = 0;
  for (const [x, y] of [[minX, minY], [minX, maxY], [maxX, minY], [maxX, maxY]]) {
    corner.set(x, 0, -y).project(camera);
    extent = Math.max(extent, Math.abs(corner.x) / 0.92, Math.abs(corner.y) / SAFE_NDC_Y);
  }
  // Under perspective the projected size scales inversely with distance, close enough to linear here.
  return probe * extent;
}

function updateCamera(minX, maxX, minY, maxY, dt) {
  if (focusId !== null) {
    const ship = battle.ships.find((s) => s.id === focusId);
    if (ship) {
      minX = maxX = ship.x;
      minY = maxY = ship.y;
    }
  }
  if (Number.isFinite(minX)) {
    const margin = focusId !== null ? FOCUS_MARGIN : FRAME_MARGIN;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const half = focusId !== null ? 0 : MIN_FRAME_SPAN / 2;
    const needed = fitDistance(
      cx,
      cy,
      Math.min(minX - margin, cx - half),
      Math.max(maxX + margin, cx + half),
      Math.min(minY - margin, cy - half),
      Math.max(maxY + margin, cy + half),
    );
    // Snap on the first frame so screenshots and page loads start framed.
    const k = camState.initialized ? 1 - Math.exp(-dt * 1.5) : 1;
    camState.initialized = true;
    camState.x += (cx - camState.x) * k;
    camState.y += (cy - camState.y) * k;
    camState.dist += (needed - camState.dist) * k;
  }
  placeCamera(camState.x, camState.y, camState.dist);
}

function applyHud(s) {
  for (const [k, v] of Object.entries(s.hud ?? {})) document.documentElement.style.setProperty(k, v);
  for (const href of s.fonts ?? []) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.append(link);
  }
  document.getElementById("blurb").textContent = `${s.name}: ${s.blurb}`;
}

function buildSwitcher() {
  const el = document.getElementById("styles");
  for (const s of STYLES) {
    const a = document.createElement("a");
    a.href = `#${s.id}`;
    a.textContent = s.name;
    if (s.id === styleId) a.className = "active";
    el.append(a);
  }
}

const scoreEl = document.getElementById("score");
const metaEl = document.getElementById("meta");
const bannerEl = document.getElementById("banner");
let bannerTimer = 0;

function updateHud() {
  const a = battle.aliveCount(0);
  const b = battle.aliveCount(1);
  scoreEl.innerHTML = `<span class="team-a">▲ AZURE ${a}</span> &nbsp;·&nbsp; <span class="team-b">${b} EMBER ■</span>`;
  metaEl.textContent = `MATCH ${battle.matchIndex}  ·  T+${battle.time.toFixed(0)}s  ·  SCRIPTED (NO RL)`;
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
    3.5,
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
