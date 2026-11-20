// Render-side hull specs: the look (model, drawn length and beam, plume sizes, turret
// heights) plus copies of the sim's mounts and numbers. The sim's YAML
// (assets/hulls/<name>/hull.yaml) is the source of truth for gameplay numbers and
// mounts; the live page overlays them from the bundle catalogue (web/src/live/world.ts
// mergeSpec), so these copies matter only where no bundle is loaded (the hull
// turntable, the M3 art preview). Aligned with the YAML on 2026-10-30, after WP-S2's
// retune: freighter hp 900 -> 400, cap 14 -> 10.5, mass 260 -> 300, inertia 16000 ->
// 40000, shield 200/10 -> 80/6, mains 3300 -> 3000 N, radius 13.5 -> 12 (its collision
// bound); carrier hp 1500 -> 1000, cap 10 -> 8, mains 7000 -> 300 N, RCS 3500 -> 450 N;
// fighter hp 60 -> 80. The strike craft's mounts already matched.
// Weapon numbers in WEAPONS below are v1's; the sim's are assets/weapons.yaml.
// Body frame: +x forward, +y port (left). Units: metres, kg, seconds.
// Style modules convert mounts with mountToLocal() into three.js local space
// (+X forward, +Y up, +Z starboard).

export const HULLS = {
  // Mount positions follow the art agent's first-draft hull layouts (Codex, gpt-6.1-sol).
  fighter: {
    role: "fighter",
    length: 10,
    beam: 5.6,
    radius: 4.5,
    hp: 80,
    mass: 10,
    inertia: 55,
    speedCap: 60,
    thrusters: [
      // dir is the direction the *force* pushes the ship; exhaust points opposite.
      { id: "thruster.main.0", pos: [-4.6, 0], dir: [1, 0], force: 900, size: 1.0 },
      { id: "thruster.rcs.fl", pos: [2.2, 2.3], dir: [0, -1], force: 160, size: 0.35 },
      { id: "thruster.rcs.fr", pos: [2.2, -2.3], dir: [0, 1], force: 160, size: 0.35 },
      { id: "thruster.rcs.rl", pos: [-2.8, 2.3], dir: [0, -1], force: 160, size: 0.35 },
      { id: "thruster.rcs.rr", pos: [-2.8, -2.3], dir: [0, 1], force: 160, size: 0.35 },
    ],
    turrets: [{ id: "turret.nose", pos: [3.8, 0], height: 0.65, rest: 0, arc: 0, slew: 0, weapon: "gauss" }],
  },
  strafer: {
    role: "skirmisher",
    length: 9,
    beam: 10.5,
    radius: 5.2,
    hp: 70,
    mass: 11,
    inertia: 75,
    speedCap: 50,
    // Shield: absorbs damage first, regenerates after regenDelay seconds without hits.
    shield: { hp: 40, regenRate: 8, regenDelay: 3, radius: 7.5 },
    thrusters: [
      { id: "thruster.main.0", pos: [-4.1, 0], dir: [1, 0], force: 380, size: 0.6 },
      { id: "thruster.lateral.fl", pos: [2.4, 4.7], dir: [0, -1], force: 420, size: 0.7 },
      { id: "thruster.lateral.fr", pos: [2.4, -4.7], dir: [0, 1], force: 420, size: 0.7 },
      { id: "thruster.lateral.rl", pos: [-2.4, 4.7], dir: [0, -1], force: 420, size: 0.7 },
      { id: "thruster.lateral.rr", pos: [-2.4, -4.7], dir: [0, 1], force: 420, size: 0.7 },
    ],
    turrets: [{ id: "turret.nose", pos: [3.4, 0], height: 0.6, rest: 0, arc: 0, slew: 0, weapon: "laser" }],
  },
  gunship: {
    role: "anchor",
    length: 15,
    beam: 10,
    radius: 7.5,
    hp: 320,
    mass: 60,
    inertia: 2200,
    speedCap: 24,
    shield: { hp: 140, regenRate: 12, regenDelay: 4, radius: 11 },
    thrusters: [
      { id: "thruster.main.l", pos: [-7, 2], dir: [1, 0], force: 1700, size: 1.4 },
      { id: "thruster.main.r", pos: [-7, -2], dir: [1, 0], force: 1700, size: 1.4 },
      { id: "thruster.rcs.fl", pos: [4, 4.4], dir: [0, -1], force: 500, size: 0.55 },
      { id: "thruster.rcs.fr", pos: [4, -4.4], dir: [0, 1], force: 500, size: 0.55 },
      { id: "thruster.rcs.rl", pos: [-4.5, 4.6], dir: [0, -1], force: 500, size: 0.55 },
      { id: "thruster.rcs.rr", pos: [-4.5, -4.6], dir: [0, 1], force: 500, size: 0.55 },
    ],
    turrets: [
      { id: "turret.fore", pos: [3.8, 0], height: 1.05, rest: 0, arc: 240, slew: 120, weapon: "flak" },
      { id: "turret.port", pos: [-2.7, 2.8], height: 1.05, rest: 90, arc: 220, slew: 90, weapon: "gauss" },
      { id: "turret.starboard", pos: [-2.7, -2.8], height: 1.05, rest: -90, arc: 220, slew: 90, weapon: "gauss" },
    ],
  },
  bomber: {
    role: "bomber",
    length: 13,
    beam: 8,
    radius: 5.8,
    hp: 110,
    mass: 22,
    inertia: 260,
    speedCap: 34,
    thrusters: [
      { id: "thruster.main.l", pos: [-6, 1.6], dir: [1, 0], force: 900, size: 0.9 },
      { id: "thruster.main.r", pos: [-6, -1.6], dir: [1, 0], force: 900, size: 0.9 },
      { id: "thruster.rcs.fl", pos: [3.5, 3.2], dir: [0, -1], force: 260, size: 0.45 },
      { id: "thruster.rcs.fr", pos: [3.5, -3.2], dir: [0, 1], force: 260, size: 0.45 },
      { id: "thruster.rcs.rl", pos: [-3.5, 3.8], dir: [0, -1], force: 260, size: 0.45 },
      { id: "thruster.rcs.rr", pos: [-3.5, -3.8], dir: [0, 1], force: 260, size: 0.45 },
    ],
    // Fixed forward torpedo rack: slow, heavy shots meant for capital ships.
    turrets: [{ id: "turret.rack", pos: [4.8, 0], height: 0.7, rest: 0, arc: 0, slew: 0, weapon: "torpedo" }],
  },
  carrier: {
    role: "carrier",
    length: 40,
    beam: 18,
    radius: 15,
    hp: 1000,
    mass: 600,
    inertia: 90000,
    speedCap: 8,
    shield: { hp: 260, regenRate: 15, regenDelay: 5, radius: 24 },
    thrusters: [
      { id: "thruster.main.l", pos: [-19.5, 4.5], dir: [1, 0], force: 300, size: 2.6 },
      { id: "thruster.main.c", pos: [-20, 0], dir: [1, 0], force: 300, size: 2.6 },
      { id: "thruster.main.r", pos: [-19.5, -4.5], dir: [1, 0], force: 300, size: 2.6 },
      { id: "thruster.rcs.fl", pos: [15, 8], dir: [0, -1], force: 450, size: 1.1 },
      { id: "thruster.rcs.fr", pos: [15, -8], dir: [0, 1], force: 450, size: 1.1 },
      { id: "thruster.rcs.rl", pos: [-14, 8.5], dir: [0, -1], force: 450, size: 1.1 },
      { id: "thruster.rcs.rr", pos: [-14, -8.5], dir: [0, 1], force: 450, size: 1.1 },
    ],
    turrets: [
      { id: "turret.flak.fore", pos: [12, 0], height: 2.2, rest: 0, arc: 270, slew: 90, weapon: "flak" },
      { id: "turret.flak.port", pos: [-6, 7], height: 2.2, rest: 90, arc: 200, slew: 90, weapon: "flak" },
      { id: "turret.flak.starboard", pos: [-6, -7], height: 2.2, rest: -90, arc: 200, slew: 90, weapon: "flak" },
    ],
    // Launch bays: ships appear at pos already moving along dir (body frame).
    bays: [
      { id: "bay.port", pos: [4, 9], dir: [0.5, 0.87] },
      { id: "bay.starboard", pos: [4, -9], dir: [0.5, -0.87] },
    ],
  },
  // Civilian convoy hauler, the transport role's freighter look: unarmed, slow, flown
  // straight to the jump point. The four RCS are small heading-hold puffers.
  freighter: {
    role: "transport",
    model: "freighter",
    length: 26,
    beam: 9,
    radius: 12,
    hp: 400,
    mass: 300,
    inertia: 40000,
    speedCap: 10.5,
    shield: { hp: 80, regenRate: 6, regenDelay: 5, radius: 15 },
    collision: [
      { pos: [8, 0], r: 4 },
      { pos: [0, 0], r: 4.5 },
      { pos: [-8, 0], r: 4.2 },
    ],
    thrusters: [
      { id: "thruster.main.l", pos: [-13, 2], dir: [1, 0], force: 3000, size: 1.75 },
      { id: "thruster.main.r", pos: [-13, -2], dir: [1, 0], force: 3000, size: 1.75 },
      { id: "thruster.rcs.fl", pos: [9, 4.2], dir: [0, -1], force: 300, size: 0.3 },
      { id: "thruster.rcs.fr", pos: [9, -4.2], dir: [0, 1], force: 300, size: 0.3 },
      { id: "thruster.rcs.rl", pos: [-9, 4.4], dir: [0, -1], force: 300, size: 0.3 },
      { id: "thruster.rcs.rr", pos: [-9, -4.4], dir: [0, 1], force: 300, size: 0.3 },
    ],
    turrets: [],
  },
  station: {
    role: "station",
    length: 44,
    beam: 44,
    radius: 19,
    hp: 2800,
    mass: 5000,
    inertia: 1e6,
    speedCap: 0,
    // Immobile: no thrusters. A ring of flak and gauss turrets covers every approach.
    static: true,
    shield: { hp: 300, regenRate: 20, regenDelay: 5, radius: 27 },
    thrusters: [],
    turrets: [
      { id: "turret.flak.0", pos: [16, 0], height: 3, rest: 0, arc: 220, slew: 90, weapon: "flak" },
      { id: "turret.flak.1", pos: [-8, 13.9], height: 3, rest: 120, arc: 220, slew: 90, weapon: "flak" },
      { id: "turret.flak.2", pos: [-8, -13.9], height: 3, rest: -120, arc: 220, slew: 90, weapon: "flak" },
      { id: "turret.gauss.0", pos: [8, 13.9], height: 3, rest: 60, arc: 220, slew: 120, weapon: "gauss" },
      { id: "turret.gauss.1", pos: [-16, 0], height: 3, rest: 180, arc: 220, slew: 120, weapon: "gauss" },
      { id: "turret.gauss.2", pos: [8, -13.9], height: 3, rest: -60, arc: 220, slew: 120, weapon: "gauss" },
    ],
  },
  // SIM_VERSION 10 (lab/runs/2026-11-19-citadel-dreadnought/plan.md is the contract for
  // every mount below). The citadel: a core and six modules on spokes, open gaps
  // between the modules, twelve turrets that can be shot off one by one, four bays on
  // the core facing the gaps. Static, role carrier in the sim; drawn with the station's
  // turret scale and its own look.
  citadel: {
    role: "station",
    model: "citadel",
    length: 100,
    beam: 100,
    radius: 49,
    hp: 3000,
    mass: 5000,
    inertia: 1e6,
    speedCap: 0,
    static: true,
    shield: { hp: 600, regenRate: 30, regenDelay: 5, radius: 56 },
    collision: citadelCollision(),
    thrusters: [],
    turrets: citadelTurrets(),
    bays: [30, 150, 210, 330].map((deg, i) => {
      const a = (deg * Math.PI) / 180;
      return { id: `bay.${i}`, pos: [22 * Math.cos(a), 22 * Math.sin(a)], dir: [Math.cos(a), Math.sin(a)] };
    }),
  },
  // The dreadnought: a 62 m gun ship (role line), armoured wedge bow, soft stern, two
  // heavy rail turrets on the spine, no bays.
  dreadnought: {
    role: "line",
    model: "dreadnought",
    length: 62,
    beam: 20,
    radius: 31,
    hp: 1800,
    mass: 900,
    inertia: 150000,
    speedCap: 7,
    shield: { hp: 350, regenRate: 18, regenDelay: 5, radius: 36 },
    collision: [
      { pos: [20, 0], r: 7 },
      { pos: [6, 0], r: 9 },
      { pos: [-10, 0], r: 9 },
      { pos: [-24, 0], r: 7 },
    ],
    thrusters: [
      { id: "thruster.main.l", pos: [-31, 5], dir: [1, 0], force: 420, size: 3.1 },
      { id: "thruster.main.c", pos: [-31, 0], dir: [1, 0], force: 420, size: 3.1 },
      { id: "thruster.main.r", pos: [-31, -5], dir: [1, 0], force: 420, size: 3.1 },
      { id: "thruster.rcs.fl", pos: [22, 7], dir: [0, -1], force: 600, size: 1.2 },
      { id: "thruster.rcs.fr", pos: [22, -7], dir: [0, 1], force: 600, size: 1.2 },
      { id: "thruster.rcs.rl", pos: [-22, 8], dir: [0, -1], force: 600, size: 1.2 },
      { id: "thruster.rcs.rr", pos: [-22, -8], dir: [0, 1], force: 600, size: 1.2 },
    ],
    turrets: [
      { id: "turret.rail.fore", pos: [14, 0], height: 3.4, rest: 0, arc: 300, slew: 25, weapon: "rail" },
      { id: "turret.rail.aft", pos: [-14, 0], height: 3.4, rest: 180, arc: 300, slew: 25, weapon: "rail" },
      { id: "turret.flak.port", pos: [0, 9], height: 2.2, rest: 90, arc: 200, slew: 90, weapon: "flak" },
      { id: "turret.flak.starboard", pos: [0, -9], height: 2.2, rest: -90, arc: 200, slew: 90, weapon: "flak" },
      { id: "turret.gauss.bow", pos: [26, 0], height: 2, rest: 0, arc: 180, slew: 120, weapon: "gauss" },
    ],
  },
};

/** The citadel's six module discs and its core (plan: core r 20, modules r 11 at 38 m). */
function citadelCollision() {
  const out = [{ pos: [0, 0], r: 20 }];
  for (let k = 0; k < 6; k++) {
    const a = (k * Math.PI) / 3;
    out.push({ pos: [38 * Math.cos(a), 38 * Math.sin(a)], r: 11 });
  }
  return out;
}

/**
 * The citadel's twelve turrets in the contract's order: per module (0, 60, ..., 300 deg)
 * a lance at r 44 on the module angle (0 and 180) or a gauss at r 42, +8 deg, and a flak
 * at r 42, -8 deg; every one rests facing outward along its module's angle.
 */
function citadelTurrets() {
  const counts = { lance: 0, flak: 0, gauss: 0 };
  const out = [];
  const add = (weapon, r, deg, moduleDeg) => {
    const a = (deg * Math.PI) / 180;
    const spec = weapon === "lance" ? { arc: 240, slew: 20, height: 4 } : weapon === "flak" ? { arc: 200, slew: 90, height: 3.2 } : { arc: 200, slew: 120, height: 3.2 };
    const rest = moduleDeg > 180 ? moduleDeg - 360 : moduleDeg;
    out.push({ id: `turret.${weapon}.${counts[weapon]++}`, pos: [r * Math.cos(a), r * Math.sin(a)], height: spec.height, rest, arc: spec.arc, slew: spec.slew, weapon });
  };
  for (let k = 0; k < 6; k++) {
    const m = k * 60;
    if (m === 0 || m === 180) {
      add("lance", 44, m, m);
      add("flak", 42, m - 8, m);
    } else {
      add("flak", 42, m - 8, m);
      add("gauss", 42, m + 8, m);
    }
  }
  return out;
}

export const WEAPONS = {
  gauss: { kind: "bullet", speed: 240, range: 300, damage: 6, interval: 0.16 },
  laser: { kind: "beam", speed: 0, range: 180, damage: 3, interval: 0.1 },
  flak: { kind: "flak", speed: 180, range: 230, damage: 4, interval: 0.09 },
  // Torpedoes hit hard but are slow enough that only big, sluggish targets fail to dodge.
  torpedo: { kind: "torpedo", speed: 95, range: 340, damage: 55, interval: 3.2 },
  // v10 capital guns (plan *start* numbers): the dreadnought's rail and the citadel's
  // lance, which only capital ships stop.
  rail: { kind: "bullet", speed: 260, range: 380, damage: 40, interval: 1.6 },
  lance: { kind: "bullet", speed: 300, range: 430, damage: 55, interval: 2.2, capitalOnly: true },
};

/** Convert a body-frame [x, y] to three.js hull-local [x, y, z] (y = height). */
export function mountToLocal(pos, height = 0) {
  return [pos[0], height, -pos[1]];
}

/** Body-frame angle (degrees, CCW from +x) to a three.js rotation.y in radians. */
export function bodyAngleToRotY(deg) {
  return (deg * Math.PI) / 180;
}
