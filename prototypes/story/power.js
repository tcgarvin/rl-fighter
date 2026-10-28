// Shows each ship's shields/engines/weapons power split. In the world, a shield bubble
// glows when shields are fed (engine plumes are scaled in main.js). In the HUD, one
// featured ship (the followed one, else an automatic pick) gets a panel with the split,
// where it is slewing to, and what each system is worth; power shifts by the featured ship,
// carriers and stations pop up as short callouts next to the hull.

import { POWER_SYSTEMS, systemPower } from "./sim.js";

const SYSTEM_LABELS = { shields: "SHD", engines: "ENG", weapons: "WPN" };
const CALLOUTS = {
  balanced: "BALANCED",
  attack: "▲ WEAPONS",
  pursuit: "▲ ENGINES",
  defend: "▲ SHIELDS",
  evade: "BREAK OFF",
};
const MODE_NAMES = {
  balanced: "BALANCED",
  attack: "WEAPONS",
  pursuit: "ENGINES",
  defend: "SHIELDS",
  evade: "BREAK OFF",
};
const CALLOUT_SECONDS = 1.4;
const CAPITAL_ROLES = new Set(["carrier", "station", "anchor"]);
// Besides the featured ship, only these announce their power shifts; more is noise.
const ANNOUNCING_ROLES = new Set(["carrier", "station"]);
// Bubble glow is zero below this shield share and full at the cap.
const BUBBLE_SHARE_FLOOR = 0.3;
// Squash the shield sphere toward the plane so it reads as a bubble around a flat hull.
const BUBBLE_FLATTEN = 0.45;

const bubbleVertex = `
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }`;
const bubbleFragment = `
  uniform vec3 color;
  uniform float strength;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float rim = pow(1.0 - abs(dot(normalize(vNormal), normalize(vView))), 2.4);
    gl_FragColor = vec4(color * (0.08 + rim) * strength, 1.0);
  }`;

export function createPowerView({ THREE, scene, palette, hud, camera }) {
  const sphere = new THREE.SphereGeometry(1, 32, 16);
  const shieldColors = palette.shield.map((c) => new THREE.Color(c));
  let bubbles = new Map();
  let featuredId = null;
  const callouts = [];
  const screen = new THREE.Vector3();

  const panel = document.createElement("div");
  panel.id = "power";
  panel.hidden = true;
  panel.innerHTML = `<div class="pw-head"><span class="pw-ship"></span><span class="pw-mode"></span></div>${POWER_SYSTEMS.map(
    (sys) =>
      `<div class="pw-row" data-sys="${sys}"><span class="pw-name">${SYSTEM_LABELS[sys]}</span><div class="pw-bar"><i class="pw-fill"></i><i class="pw-target"></i><i class="pw-even"></i></div><span class="pw-mult"></span></div>`,
  ).join("")}`;
  hud.append(panel);
  const rows = Object.fromEntries(POWER_SYSTEMS.map((sys) => [sys, panel.querySelector(`[data-sys="${sys}"]`)]));
  const marker = document.createElement("div");
  marker.className = "pw-marker";
  marker.hidden = true;
  hud.append(marker);

  function toScreen(object) {
    screen.setFromMatrixPosition(object.matrixWorld).project(camera);
    return [((screen.x + 1) / 2) * window.innerWidth, ((1 - screen.y) / 2) * window.innerHeight];
  }

  function clearBubbles() {
    for (const b of bubbles.values()) {
      scene.remove(b.mesh);
      b.mesh.material.dispose();
    }
    bubbles = new Map();
  }

  /** Rebuild per-ship visuals for a new match. */
  function newMatch(battle) {
    clearBubbles();
    featuredId = null;
    for (const c of callouts.splice(0)) c.el.remove();
    for (const ship of battle.ships) {
      if (!ship.hull.shield) continue;
      const material = new THREE.ShaderMaterial({
        uniforms: { color: { value: shieldColors[ship.team] }, strength: { value: 0 } },
        vertexShader: bubbleVertex,
        fragmentShader: bubbleFragment,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(sphere, material);
      const r = ship.hull.shield.radius;
      mesh.scale.set(r, r * BUBBLE_FLATTEN, r);
      mesh.visible = false;
      scene.add(mesh);
      bubbles.set(ship.id, { mesh, flash: 0 });
    }
  }

  function callout(ship, view, text) {
    const existing = callouts.findIndex((c) => c.id === ship.id);
    if (existing >= 0) callouts.splice(existing, 1)[0].el.remove();
    const el = document.createElement("div");
    el.className = `pw-callout ${ship.team === 0 ? "team-a" : "team-b"}`;
    el.textContent = text;
    hud.append(el);
    callouts.push({ id: ship.id, el, view, age: 0 });
  }

  /** Keep a featured ship: the followed one, else the current pick while it lives. */
  function pickFeatured(battle, followId) {
    if (followId !== null) return followId;
    const current = battle.ships[featuredId];
    if (current && current.alive && current.present) return featuredId;
    const candidates = battle.ships.filter((s) => s.alive && s.present && !CAPITAL_ROLES.has(s.hull.role));
    if (!candidates.length) return null;
    return candidates[Math.floor(Math.random() * candidates.length)].id;
  }

  function updatePanel(ship, view) {
    if (!ship || !view) {
      panel.hidden = true;
      marker.hidden = true;
      return;
    }
    panel.hidden = false;
    panel.className = ship.team === 0 ? "team-a" : "team-b";
    panel.querySelector(".pw-ship").textContent = `${ship.hullName.toUpperCase()} #${ship.id}`;
    panel.querySelector(".pw-mode").textContent = ship.rtb ? "RTB" : MODE_NAMES[ship.powerMode];
    // Bars run from 0 to this hull's cap; the tick marks an even split.
    const { systems, maxShare } = ship.powerProfile;
    for (const sys of POWER_SYSTEMS) {
      const row = rows[sys];
      // Shieldless hulls split two ways; static hulls' engine share only holds station.
      const absent = !systems.includes(sys);
      const unused = absent || (sys === "engines" && Boolean(ship.hull.static));
      row.classList.toggle("unused", unused);
      row.querySelector(".pw-fill").style.width = `${(100 * ship.power[sys]) / maxShare}%`;
      row.querySelector(".pw-target").style.left = `${(100 * ship.powerTarget[sys]) / maxShare}%`;
      row.querySelector(".pw-target").hidden = absent;
      row.querySelector(".pw-even").style.left = `${(100 / systems.length / maxShare).toFixed(1)}%`;
      row.querySelector(".pw-even").hidden = absent;
      row.querySelector(".pw-mult").textContent = absent ? "NONE" : unused ? "—" : `${systemPower(ship, sys).toFixed(1)}×`;
    }
    const [x, y] = toScreen(view.model.object);
    marker.hidden = !ship.alive;
    marker.className = `pw-marker ${ship.team === 0 ? "team-a" : "team-b"}`;
    marker.style.transform = `translate(${x}px, ${y}px)`;
  }

  return {
    newMatch,

    /** Call after each sim step with that step's power shifts. */
    onShifts(battle, shipViews, shifts) {
      for (const e of shifts) {
        const ship = battle.ships[e.id];
        const view = shipViews.get(e.id);
        if (!view) continue;
        if (e.mode === "defend" || e.mode === "evade") {
          const bubble = bubbles.get(e.id);
          if (bubble) bubble.flash = 1;
        }
        if (e.id === featuredId) callout(ship, view, CALLOUTS[e.mode]);
        else if (ANNOUNCING_ROLES.has(ship.hull.role) && e.mode !== "balanced") callout(ship, view, CALLOUTS[e.mode]);
      }
    },

    /** A one-off callout next to a ship (returning to base, back from repairs). */
    notice(ship, view, text) {
      if (view) callout(ship, view, text);
    },

    update(battle, shipViews, dt, followId, active) {
      for (const ship of battle.ships) {
        const bubble = bubbles.get(ship.id);
        const view = shipViews.get(ship.id);
        if (!bubble || !view) continue;
        bubble.flash = Math.max(0, bubble.flash - dt * 2.5);
        const fed = Math.min(1, Math.max(0, (ship.power.shields - BUBBLE_SHARE_FLOOR) / (ship.powerProfile.maxShare - BUBBLE_SHARE_FLOOR)));
        const charge = ship.maxShield > 0 ? ship.shield / ship.maxShield : 0;
        const strength = fed * (0.25 + 0.75 * charge) * 0.8 + bubble.flash;
        bubble.mesh.visible = view.model.object.visible && ship.shield > 0 && strength > 0.01;
        bubble.mesh.position.copy(view.model.object.position);
        bubble.mesh.material.uniforms.strength.value = strength;
      }
      featuredId = active ? pickFeatured(battle, followId) : null;
      updatePanel(featuredId === null ? null : battle.ships[featuredId], shipViews.get(featuredId));
      for (let i = callouts.length - 1; i >= 0; i--) {
        const c = callouts[i];
        c.age += dt;
        if (c.age > CALLOUT_SECONDS || !c.view.model.object.visible) {
          c.el.remove();
          callouts.splice(i, 1);
          continue;
        }
        const [sx, y] = toScreen(c.view.model.object);
        // Centred over the hull, but never clipped by the screen edge.
        const half = c.el.offsetWidth / 2 + 6;
        const x = Math.min(window.innerWidth - half, Math.max(half, sx));
        const t = c.age / CALLOUT_SECONDS;
        c.el.style.transform = `translate(-50%, ${y - 26 - t * 18}px) translateX(${x}px)`;
        c.el.style.opacity = String(t < 0.7 ? 1 : 1 - (t - 0.7) / 0.3);
      }
    },
  };
}
