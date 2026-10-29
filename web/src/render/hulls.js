// Prototype hull specs shared by the scripted sim and every style module.
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
    hp: 60,
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
    hp: 1500,
    mass: 600,
    inertia: 90000,
    speedCap: 10,
    shield: { hp: 260, regenRate: 15, regenDelay: 5, radius: 24 },
    thrusters: [
      { id: "thruster.main.l", pos: [-19.5, 4.5], dir: [1, 0], force: 7000, size: 2.6 },
      { id: "thruster.main.c", pos: [-20, 0], dir: [1, 0], force: 7000, size: 2.6 },
      { id: "thruster.main.r", pos: [-19.5, -4.5], dir: [1, 0], force: 7000, size: 2.6 },
      { id: "thruster.rcs.fl", pos: [15, 8], dir: [0, -1], force: 3500, size: 1.1 },
      { id: "thruster.rcs.fr", pos: [15, -8], dir: [0, 1], force: 3500, size: 1.1 },
      { id: "thruster.rcs.rl", pos: [-14, 8.5], dir: [0, -1], force: 3500, size: 1.1 },
      { id: "thruster.rcs.rr", pos: [-14, -8.5], dir: [0, 1], force: 3500, size: 1.1 },
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
};

export const WEAPONS = {
  gauss: { kind: "bullet", speed: 240, range: 300, damage: 6, interval: 0.16 },
  laser: { kind: "beam", speed: 0, range: 180, damage: 3, interval: 0.1 },
  flak: { kind: "flak", speed: 180, range: 230, damage: 4, interval: 0.09 },
  // Torpedoes hit hard but are slow enough that only big, sluggish targets fail to dodge.
  torpedo: { kind: "torpedo", speed: 95, range: 340, damage: 55, interval: 3.2 },
};

/** Convert a body-frame [x, y] to three.js hull-local [x, y, z] (y = height). */
export function mountToLocal(pos, height = 0) {
  return [pos[0], height, -pos[1]];
}

/** Body-frame angle (degrees, CCW from +x) to a three.js rotation.y in radians. */
export function bodyAngleToRotY(deg) {
  return (deg * Math.PI) / 180;
}
