// Throwaway scripted 2D battle for the story demo. Not the real sim (that is Rust); it
// only needs to look plausible and exercise each mission: per-thruster throttle,
// independent turrets, bullets, beams, flak, torpedoes, carrier launches, a capture
// beacon, an immobile station, a power split (shields, engines, weapons), and strike
// craft that return to their carrier for repairs.

import { HULLS, WEAPONS } from "./hulls.js";

const DT = 1 / 30;
const ARENA_RADIUS = 520;
// Jump-in: squads arrive in sequence; ships within a squad are staggered by milliseconds.
const FIRST_SQUAD_DELAY = 1.0;
const SQUAD_INTERVAL = 0.3;
const SHIP_STAGGER_MAX = 0.08;
const ARRIVAL_SPEED_FACTOR = 1.4;
const ARRIVAL_CONTROL_LOCK = 0.7;
const SQUAD_SIZE = 3;
// Carriers launch one ship at a time, alternating bays.
const FIRST_LAUNCH_DELAY = 2.2;
const LAUNCH_INTERVAL = 0.4;
const LAUNCH_SPEED = 30;
const LAUNCH_CONTROL_LOCK = 0.5;
// Torpedoes steer gently toward their target, so only sluggish hulls fail to dodge.
const TORPEDO_TURN_RATE = 0.7;
const CAPITAL_ROLES = new Set(["carrier", "station", "anchor"]);
const SINGLE_SQUAD_HULLS = new Set(["gunship", "carrier", "bomber"]);
// Strike craft fly from carriers and go back to them for repairs.
const STRIKE_CRAFT = new Set(["fighter", "bomber"]);
// Below this hull fraction a strike craft with a living carrier heads home.
const RTB_HULL_FRACTION = 0.6;
// Docking: reach this close to the bay mouth, which sits this far outside the bay.
const DOCK_DISTANCE = 9;
const BAY_APPROACH_OFFSET = 6;
// Hull repaired per second aboard, as a fraction of max hull.
const REPAIR_RATE = 0.15;

// Power: each ship's reactor output is split between its systems: shields, engines and
// weapons, or just engines and weapons on hulls without a shield. Shares sum to 1 and none
// may exceed the hull's max share, so no ship can run everything flat out. A system at an
// even split runs at 1x; starved it falls to POWER_FLOOR, at the cap it reaches ~1.5-1.6x.
// The split slews at POWER_SLEW per second, so a commitment takes time to undo.
export const POWER_SYSTEMS = ["shields", "engines", "weapons"];
const MAX_SHARE_THREE_WAY = 0.6;
const MAX_SHARE_TWO_WAY = 0.8;
const POWER_FLOOR = 0.2;
// Pilots spend most of a fight weapons-heavy; this keeps that near the pre-power fire rate.
const WEAPON_RATE_SCALE = 0.65;
const POWER_SLEW = 0.45;
// Scripted pilots hold a mode at least this long, unless they need shields in a hurry.
const POWER_DWELL = 1.4;
const POWER_PANIC_DWELL = 0.4;
// The scripted pilots' presets. A learned policy would set the split directly.
export const POWER_MODES = {
  balanced: { shields: 1 / 3, engines: 1 / 3, weapons: 1 / 3, label: "BALANCED" },
  attack: { shields: 0.2, engines: 0.2, weapons: 0.6, label: "POWER TO WEAPONS" },
  pursuit: { shields: 0.15, engines: 0.6, weapons: 0.25, label: "POWER TO ENGINES" },
  defend: { shields: 0.6, engines: 0.25, weapons: 0.15, label: "POWER TO SHIELDS" },
  evade: { shields: 0.4, engines: 0.6, weapons: 0, label: "BREAK OFF" },
};

/** Which systems this hull powers, and the most any one of them may draw. */
export function powerProfile(hull) {
  const systems = hull.shield ? POWER_SYSTEMS : ["engines", "weapons"];
  return { systems, maxShare: systems.length === 3 ? MAX_SHARE_THREE_WAY : MAX_SHARE_TWO_WAY };
}

/** Effect multiplier for one of a ship's systems, from its share of reactor output. */
export function systemPower(ship, system) {
  return POWER_FLOOR + (1 - POWER_FLOOR) * ship.powerProfile.systems.length * ship.power[system];
}

// Static hulls burn a fixed share holding station; they split the rest between shields
// and weapons (otherwise the engines' third would be a free bonus).
const STATION_KEEPING_SHARE = 0.2;

/** A mode's split for this hull. */
function modeSplit(mode, hull) {
  const m = POWER_MODES[mode];
  const { maxShare } = powerProfile(hull);
  if (hull.static) {
    const spare = 1 - STATION_KEEPING_SHARE;
    const shields = clamp((spare * m.shields) / (m.shields + m.weapons), spare - maxShare, maxShare);
    return { shields, engines: STATION_KEEPING_SHARE, weapons: spare - shields };
  }
  if (hull.shield) return { shields: m.shields, engines: m.engines, weapons: m.weapons };
  // No shield: the preset's engines-to-weapons ratio over the whole reactor.
  const engines = clamp(m.engines / (m.engines + m.weapons), 1 - maxShare, maxShare);
  return { shields: 0, engines, weapons: 1 - engines };
}

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const deg = (d) => (d * Math.PI) / 180;

function toWorld(ship, px, py) {
  const c = Math.cos(ship.heading);
  const s = Math.sin(ship.heading);
  return [ship.x + px * c - py * s, ship.y + px * s + py * c];
}

function toBody(ship, wx, wy) {
  const c = Math.cos(ship.heading);
  const s = Math.sin(ship.heading);
  return [wx * c + wy * s, -wx * s + wy * c];
}

/**
 * Greedy thruster allocation: each thruster fires in proportion to how much it helps the
 * desired body-frame force and torque, quantized to the {0, 1/2, 1} throttle levels.
 */
function allocateThrusters(hull, forceBody, torque) {
  const fMag = Math.hypot(forceBody[0], forceBody[1]);
  const fx = fMag > 1e-6 ? forceBody[0] / fMag : 0;
  const fy = fMag > 1e-6 ? forceBody[1] / fMag : 0;
  return hull.thrusters.map((t) => {
    const along = (t.dir[0] * fx + t.dir[1] * fy) * Math.min(fMag, 1);
    const arm = t.pos[0] * t.dir[1] - t.pos[1] * t.dir[0];
    const spin = Math.sign(arm) * torque;
    const score = along + 1.2 * spin;
    if (score > 0.6) return 1;
    if (score > 0.25) return 0.5;
    return 0;
  });
}

function makeShip(id, hullName, team, x, y, heading) {
  const hull = HULLS[hullName];
  return {
    id,
    hullName,
    hull,
    team,
    x,
    y,
    vx: 0,
    vy: 0,
    heading,
    omega: 0,
    hp: hull.hp,
    maxHp: hull.hp,
    alive: true,
    // Not yet jumped in (or still aboard a carrier): invisible, untargetable and not simulated.
    present: false,
    arriveAt: Infinity,
    controlLockedUntil: 0,
    shield: hull.shield?.hp ?? 0,
    maxShield: hull.shield?.hp ?? 0,
    lastHitTime: -Infinity,
    throttles: hull.thrusters.map(() => 0),
    powerProfile: powerProfile(hull),
    power: modeSplit("balanced", hull),
    powerTarget: modeSplit("balanced", hull),
    powerMode: "balanced",
    powerModeSince: -Infinity,
    // Per-pilot nerve: how low the shield gets before it diverts power to it.
    shieldNerve: 0.3,
    turretAngles: hull.turrets.map((t) => deg(t.rest)),
    turretCooldowns: hull.turrets.map(() => 0),
    firing: hull.turrets.map(() => false),
    orbitSign: 1,
    // Bombers alternate between attack runs and breaking away to set up the next one.
    breakingUntil: 0,
    // Returning to base (heading for its carrier's bay to dock and repair).
    rtb: false,
  };
}

export class ScriptedBattle {
  constructor(seed = 1) {
    this.rng = mulberry32(seed);
    this.matchIndex = 0;
    this.events = emptyEvents();
    this.ships = [];
    this.projectiles = [];
    this.beams = [];
    this.phase = "idle";
  }

  /**
   * Start a mission. `rosters[team]` lists hull names; capital ships from
   * `mission.fixed` must already be included (the draft adds them).
   */
  startMatch(mission, rosters) {
    this.mission = mission;
    this.rosters = rosters;
    this.ships = [];
    this.projectiles = [];
    this.beams = [];
    this.time = 0;
    this.phase = "battle";
    this.winner = -1;
    this.outcome = "";
    this.capture = [0, 0];
    this.flagships = [null, null];
    this.station = null;
    // Aboard each carrier: ready to launch (reserves) and under repair (hangar).
    this.reserves = [[], []];
    this.hangar = [[], []];
    this.nextLaunch = [Infinity, Infinity];
    this.nextBay = [0, 0];
    rosters.forEach((roster, team) => this.deployTeam(roster, team));
    this.matchIndex += 1;
  }

  deployTeam(roster, team) {
    const side = team === 0 ? -1 : 1;
    const heading = team === 0 ? 0 : Math.PI;
    const teamOffset = team === 0 ? 0 : 0.5 + this.rng() * 0.6;
    let craft = roster.filter((h) => h !== "station");
    if (roster.includes("station")) {
      // The station is already on the field when the match opens: no jump.
      const station = this.addShip("station", team, side * 250, (this.rng() - 0.5) * 80, heading);
      station.present = true;
      station.arriveAt = 0;
      this.station = station;
    }
    if (this.mission.launchFromBays && craft.includes("carrier")) {
      const carrier = this.addShip("carrier", team, side * 300, (this.rng() - 0.5) * 120, heading);
      carrier.arriveAt = FIRST_SQUAD_DELAY + teamOffset;
      this.flagships[team] = carrier;
      const wing = Object.entries(this.mission.airWing ?? {}).flatMap(([h, n]) => Array(n).fill(h));
      // Interleave so fighters and bombers come out of the bays mixed, not in blocks.
      const strike = [...craft.filter((c) => STRIKE_CRAFT.has(c)), ...wing].sort(() => this.rng() - 0.5);
      // Strike craft wait aboard; created now so ids stay stable for the renderer.
      for (const h of strike) this.reserves[team].push(this.addShip(h, team, carrier.x, carrier.y, heading));
      this.nextLaunch[team] = carrier.arriveAt + FIRST_LAUNCH_DELAY;
      // Escorts jump in alongside, a beat after the carrier.
      craft = craft.filter((c) => c !== "carrier" && !STRIKE_CRAFT.has(c));
      if (!craft.length) return;
    }
    this.deploySquads(craft, team, side, heading, teamOffset);
  }

  /** Jump a roster in as squads: heavy hulls alone, small craft in groups. */
  deploySquads(craft, team, side, heading, teamOffset) {
    // Squads: heavy hulls jump alone, small craft in groups of up to SQUAD_SIZE.
    const heavy = craft.filter((h) => SINGLE_SQUAD_HULLS.has(h) && h !== "bomber").map((h) => [h]);
    const bombers = craft.filter((h) => h === "bomber");
    const light = craft.filter((h) => !SINGLE_SQUAD_HULLS.has(h));
    const squads = [];
    for (let i = 0; i < light.length; i += SQUAD_SIZE) squads.push(light.slice(i, i + SQUAD_SIZE));
    for (let i = 0; i < bombers.length; i += 2) squads.push(bombers.slice(i, i + 2));
    squads.push(...heavy);
    // Attackers in a station assault jump in further back, out of the station's reach.
    const depth = this.station && this.station.team !== team ? 330 : 230;
    squads.forEach((squad, squadIndex) => {
      const squadY = (squadIndex - (squads.length - 1) / 2) * 70 + (this.rng() - 0.5) * 30;
      const squadX = side * (depth + (squad[0] === "gunship" ? 50 : 0) + this.rng() * 30);
      const squadTime = FIRST_SQUAD_DELAY + teamOffset + squadIndex * SQUAD_INTERVAL * (0.6 + this.rng() * 0.8);
      squad.forEach((hullName, i) => {
        const row = i - (squad.length - 1) / 2;
        const ship = this.addShip(hullName, team, squadX + Math.abs(row) * side * 10, squadY + row * 16, heading);
        ship.arriveAt = squadTime + this.rng() * SHIP_STAGGER_MAX;
      });
    });
  }

  addShip(hullName, team, x, y, heading) {
    const ship = makeShip(this.ships.length, hullName, team, x, y, heading);
    ship.orbitSign = this.rng() < 0.5 ? -1 : 1;
    ship.shieldNerve = 0.2 + this.rng() * 0.3;
    this.ships.push(ship);
    return ship;
  }

  /** Ships still in the fight, including those that haven't jumped in or launched yet. */
  aliveCount(team) {
    return this.ships.filter((s) => s.alive && s.team === team).length;
  }

  reserveCount(team) {
    return this.reserves[team].length;
  }

  nearestEnemy(ship, maxRange = Infinity, filter = null) {
    let best = null;
    let bestD = maxRange;
    for (const other of this.ships) {
      if (!isActive(other) || other.team === ship.team) continue;
      if (filter && !filter(other)) continue;
      const d = Math.hypot(other.x - ship.x, other.y - ship.y);
      if (d < bestD) {
        bestD = d;
        best = other;
      }
    }
    return best;
  }

  step() {
    this.events = emptyEvents();
    if (this.phase === "idle") return;
    // After the result the fight plays on for the outro, but nothing is scored.
    if (this.phase === "battle") this.time += DT;
    this.processArrivals();
    this.processHangars();
    this.processLaunches();
    for (const ship of this.ships) {
      if (isActive(ship)) this.control(ship);
    }
    for (const ship of this.ships) {
      if (isActive(ship)) {
        if (!ship.hull.static) this.integrate(ship);
        this.regenerateShield(ship);
      }
    }
    this.advanceProjectiles();
    this.beams = this.beams.filter((b) => (b.ttl -= DT) > 0);
    if (this.phase !== "battle") return;
    this.updateBeacon();
    this.checkOutcome();
  }

  processArrivals() {
    for (const ship of this.ships) {
      if (ship.present || !ship.alive || this.time < ship.arriveAt) continue;
      ship.present = true;
      const speed = ship.hull.speedCap * ARRIVAL_SPEED_FACTOR;
      ship.vx = Math.cos(ship.heading) * speed;
      ship.vy = Math.sin(ship.heading) * speed;
      ship.controlLockedUntil = this.time + ARRIVAL_CONTROL_LOCK;
      this.events.arrivals.push({ id: ship.id, x: ship.x, y: ship.y, heading: ship.heading, team: ship.team, hullName: ship.hullName });
    }
  }

  processLaunches() {
    for (const team of [0, 1]) {
      const carrier = this.flagships[team];
      if (!carrier || !isActive(carrier) || this.time < this.nextLaunch[team] || !this.reserves[team].length) continue;
      const ship = this.reserves[team].shift();
      const bays = carrier.hull.bays;
      const bay = bays[this.nextBay[team]++ % bays.length];
      const [x, y] = toWorld(carrier, bay.pos[0], bay.pos[1]);
      const heading = carrier.heading + Math.atan2(bay.dir[1], bay.dir[0]);
      const repaired = ship.docked === true;
      Object.assign(ship, { x, y, heading, present: true, arriveAt: this.time, docked: false, rtb: false, breakingUntil: 0 });
      ship.vx = carrier.vx + Math.cos(heading) * LAUNCH_SPEED;
      ship.vy = carrier.vy + Math.sin(heading) * LAUNCH_SPEED;
      ship.controlLockedUntil = this.time + LAUNCH_CONTROL_LOCK;
      this.events.launches.push({ id: ship.id, x, y, heading, team, repaired });
      this.nextLaunch[team] = this.time + LAUNCH_INTERVAL;
    }
  }

  /** The bay mouth a returning ship should aim for: the nearer of its carrier's bays. */
  bayApproach(ship, carrier) {
    let best = null;
    for (const bay of carrier.hull.bays) {
      const [bx, by] = toWorld(carrier, bay.pos[0] + bay.dir[0] * BAY_APPROACH_OFFSET, bay.pos[1] + bay.dir[1] * BAY_APPROACH_OFFSET);
      const d = Math.hypot(bx - ship.x, by - ship.y);
      if (!best || d < best.dist) best = { x: bx, y: by, dist: d };
    }
    return best;
  }

  /** Take a returning ship aboard: out of the fight until repaired, then back in the launch queue. */
  dock(ship, carrier) {
    ship.present = false;
    ship.docked = true;
    ship.rtb = false;
    ship.throttles = ship.throttles.map(() => 0);
    this.hangar[ship.team].push(ship);
    this.events.docks.push({ id: ship.id, x: ship.x, y: ship.y, heading: Math.atan2(ship.vy, ship.vx), team: ship.team, carrierId: carrier.id });
  }

  /** Repair docked ships; fully repaired ones join the launch queue. */
  processHangars() {
    for (const team of [0, 1]) {
      const carrier = this.flagships[team];
      if (!carrier) continue;
      const stillRepairing = [];
      for (const ship of this.hangar[team]) {
        ship.hp = Math.min(ship.maxHp, ship.hp + ship.maxHp * REPAIR_RATE * DT);
        // Ride along with the carrier, so a camera following a docked ship stays put.
        ship.x = carrier.x;
        ship.y = carrier.y;
        if (ship.hp < ship.maxHp) stillRepairing.push(ship);
        else {
          ship.power = modeSplit("balanced", ship.hull);
          ship.powerTarget = modeSplit("balanced", ship.hull);
          ship.powerMode = "balanced";
          this.reserves[team].push(ship);
          if (this.time >= this.nextLaunch[team]) this.nextLaunch[team] = this.time;
        }
      }
      this.hangar[team] = stillRepairing;
    }
  }

  updateBeacon() {
    const beacon = this.mission.beacon;
    if (!beacon) return;
    const inside = [0, 0];
    for (const ship of this.ships) {
      if (isActive(ship) && Math.hypot(ship.x - beacon.x, ship.y - beacon.y) < beacon.radius) inside[ship.team] += 1;
    }
    this.beaconInside = inside;
    // Only an uncontested ring charges.
    for (const team of [0, 1]) {
      if (inside[team] > 0 && inside[1 - team] === 0) {
        this.capture[team] = Math.min(100, this.capture[team] + (beacon.rate + beacon.perShip * inside[team]) * DT);
      }
    }
  }

  checkOutcome() {
    const m = this.mission;
    const alive = [this.aliveCount(0), this.aliveCount(1)];
    const finish = (winner, outcome) => {
      this.winner = winner;
      this.outcome = outcome;
      this.phase = "over";
    };
    if (m.id === "flagship") {
      const dead = this.flagships.map((f) => f && !f.alive);
      if (dead[0] || dead[1]) return finish(dead[0] && dead[1] ? -1 : dead[0] ? 1 : 0, "FLAGSHIP DESTROYED");
    }
    if (m.id === "station") {
      if (!this.station.alive) return finish(m.attacker, "STATION DESTROYED");
      const attackers = alive[m.attacker];
      if (attackers === 0) return finish(1 - m.attacker, "ASSAULT REPELLED");
      if (this.time > m.timeLimit) return finish(1 - m.attacker, "THE STATION HELD");
      return;
    }
    if (m.beacon) {
      for (const team of [0, 1]) if (this.capture[team] >= 100) return finish(team, "BEACON CHARGED");
    }
    if (alive[0] === 0 || alive[1] === 0) return finish(alive[0] === alive[1] ? -1 : alive[0] > 0 ? 0 : 1, "FLEET ANNIHILATED");
    if (this.time > m.timeLimit) {
      // Tiebreak at the time limit: objective progress, then remaining fleet value.
      let score = [this.fleetValue(0), this.fleetValue(1)];
      if (m.beacon) score = this.capture;
      if (m.id === "flagship") score = this.flagships.map((f) => (f.hp + f.shield) / (f.maxHp + f.maxShield));
      const winner = Math.abs(score[0] - score[1]) < 1e-3 ? -1 : score[0] > score[1] ? 0 : 1;
      finish(winner, "TIME — ON POINTS");
    }
  }

  fleetValue(team) {
    return this.ships.filter((s) => s.alive && s.team === team).reduce((sum, s) => sum + s.maxHp * (s.hp / s.maxHp), 0);
  }

  regenerateShield(ship) {
    const spec = ship.hull.shield;
    if (!spec) return;
    const boost = systemPower(ship, "shields");
    if (this.time - ship.lastHitTime < spec.regenDelay / boost) return;
    ship.shield = Math.min(ship.maxShield, ship.shield + spec.regenRate * boost * DT);
  }

  /** Scripted power management: pick a mode from the situation, then slew toward it. */
  managePower(ship, target, goal) {
    const hull = ship.hull;
    const range = Math.max(...hull.turrets.map((t) => WEAPONS[t.weapon].range));
    const dist = target ? Math.hypot(target.x - ship.x, target.y - ship.y) : Infinity;
    const underFire = this.time - ship.lastHitTime < 1.2;
    const hurt = ship.hp / ship.maxHp < 0.45 && !hull.static && hull.role !== "carrier";
    let want = "balanced";
    if (ship.maxShield > 0 && underFire && ship.shield / ship.maxShield < ship.shieldNerve) want = hurt ? "evade" : "defend";
    // Without a shield the only defence is speed, so a badly hurt ship runs.
    else if (ship.maxShield === 0 && underFire && hurt) want = "evade";
    else if (ship.rtb) want = "evade";
    else if (hull.role === "bomber" && this.time < ship.breakingUntil) want = "pursuit";
    else if (dist < range) want = "attack";
    else if (!hull.static && (goal || dist > range * 1.5)) want = "pursuit";
    const held = this.time - ship.powerModeSince;
    const panic = want === "defend" || want === "evade";
    if (want !== ship.powerMode && held > (panic ? POWER_PANIC_DWELL : POWER_DWELL)) {
      ship.powerMode = want;
      ship.powerModeSince = this.time;
      ship.powerTarget = modeSplit(want, hull);
      this.events.powerShifts.push({ id: ship.id, mode: want });
    }
    // Move every share toward its target at the same rate, which keeps the sum at 1.
    const gap = Math.max(...POWER_SYSTEMS.map((k) => Math.abs(ship.powerTarget[k] - ship.power[k])));
    const k = gap > 0 ? Math.min(1, (POWER_SLEW * DT) / gap) : 0;
    for (const sys of POWER_SYSTEMS) ship.power[sys] += (ship.powerTarget[sys] - ship.power[sys]) * k;
  }

  /** Who this ship wants to fight, by hull role and mission. */
  pickTarget(ship) {
    const role = ship.hull.role;
    if (role === "bomber") {
      return this.nearestEnemy(ship, Infinity, (o) => CAPITAL_ROLES.has(o.hull.role)) ?? this.nearestEnemy(ship);
    }
    if (role === "fighter") {
      return this.nearestEnemy(ship, 260, (o) => o.hull.role === "bomber") ?? this.nearestEnemy(ship);
    }
    return this.nearestEnemy(ship);
  }

  control(ship) {
    const hull = ship.hull;
    if (this.time < ship.controlLockedUntil) {
      // Coasting out of the jump or the bay: no thrust, guns cold.
      ship.throttles = hull.thrusters.map(() => 0);
      ship.firing = hull.turrets.map(() => false);
      return;
    }
    if (hull.static) {
      this.managePower(ship, this.nearestEnemy(ship), false);
      this.aimTurrets(ship);
      return;
    }
    const carrier = this.flagships?.[ship.team];
    const carrierUp = carrier && isActive(carrier);
    if (!ship.rtb && carrierUp && STRIKE_CRAFT.has(hull.role) && ship.hp / ship.maxHp < RTB_HULL_FRACTION) {
      ship.rtb = true;
      this.events.rtb.push({ id: ship.id });
    }
    if (ship.rtb && !carrierUp) ship.rtb = false;
    if (ship.rtb) {
      this.returnToBase(ship, carrier);
      return;
    }
    let target = this.pickTarget(ship);
    let goal = false;
    const beacon = this.mission.beacon;
    if (beacon && hull.role !== "bomber") {
      // Beacon: go and sit in the ring unless an enemy is close enough to brawl with.
      const near = target && Math.hypot(target.x - ship.x, target.y - ship.y) < 170;
      if (!near) {
        const inRing = Math.hypot(beacon.x - ship.x, beacon.y - ship.y) < beacon.radius * 0.6;
        this.managePower(ship, target, !inRing);
        target = { x: beacon.x, y: beacon.y, vx: 0, vy: 0 };
        goal = true;
      }
    }
    if (!goal) this.managePower(ship, target, false);
    let force = [0, 0];
    let desiredHeading = ship.heading;
    if (hull.role === "carrier") {
      [force, desiredHeading] = this.carrierManoeuvre(ship, target);
    } else if (target) {
      const dx = target.x - ship.x;
      const dy = target.y - ship.y;
      const dist = Math.max(1e-3, Math.hypot(dx, dy));
      const bulletSpeed = 240;
      const tLead = goal ? 0 : dist / bulletSpeed;
      const ax = dx + (target.vx - ship.vx) * tLead;
      const ay = dy + (target.vy - ship.vy) * tLead;
      desiredHeading = Math.atan2(ay, ax);
      if (goal) {
        // Drift into the ring and hold station near its middle.
        const err = Math.abs(wrap(desiredHeading - ship.heading));
        const go = dist > beacon.radius * 0.45 ? 1 : 0;
        force = [go * (err < 0.9 ? 0.8 : 0.1), 0];
        if (dist < beacon.radius * 0.45) desiredHeading = ship.heading;
      } else if (hull.role === "fighter") {
        const err = Math.abs(wrap(desiredHeading - ship.heading));
        const go = dist > 60 || err > 1.2 ? 1 : 0.3;
        force = [go * (err < 0.9 ? 1 : 0.2), 0];
      } else if (hull.role === "bomber") {
        [force, desiredHeading] = this.bomberRun(ship, target, dist, desiredHeading);
      } else if (hull.role === "skirmisher") {
        const orbitR = 120;
        const rx = -dx / dist;
        const ry = -dy / dist;
        const tx = -ry * ship.orbitSign;
        const ty = rx * ship.orbitSign;
        const radialErr = (dist - orbitR) / orbitR;
        const vdx = tx * 45 - rx * radialErr * 45 - ship.vx;
        const vdy = ty * 45 - ry * radialErr * 45 - ship.vy;
        const body = toBody(ship, vdx, vdy);
        force = [clamp(body[0] / 20, -1, 1), clamp(body[1] / 20, -1, 1)];
        desiredHeading = Math.atan2(dy, dx);
      } else {
        const standoff = 170;
        const go = dist > standoff ? 0.8 : dist < standoff * 0.7 ? -0.3 : 0;
        // Gunships present their broadside to bring both side turrets to bear.
        desiredHeading = Math.atan2(dy, dx) + (dist < standoff * 1.2 ? Math.PI / 2 : 0);
        force = [go, 0];
      }
    }
    // Arena edge: steer back toward the centre.
    const r = Math.hypot(ship.x, ship.y);
    if (r > ARENA_RADIUS * 0.85) {
      desiredHeading = Math.atan2(-ship.y, -ship.x);
      force = [1, 0];
    }
    const err = wrap(desiredHeading - ship.heading);
    const torque = clamp(2.5 * err - 1.6 * ship.omega, -1, 1);
    ship.throttles = allocateThrusters(hull, force, torque);
    this.aimTurrets(ship);
  }

  /** Fly to the carrier's nearest bay mouth, slowing near it, and dock on arrival. Guns stay live. */
  returnToBase(ship, carrier) {
    const bay = this.bayApproach(ship, carrier);
    if (bay.dist < DOCK_DISTANCE) {
      this.dock(ship, carrier);
      return;
    }
    this.managePower(ship, bay, true);
    // Aim where the bay will be: the carrier is slow but not still.
    const lead = bay.dist / Math.max(20, ship.hull.speedCap);
    const desired = Math.atan2(bay.y + carrier.vy * lead - ship.y, bay.x + carrier.vx * lead - ship.x);
    const err = wrap(desired - ship.heading);
    const go = bay.dist > 50 ? 1 : 0.5;
    const force = [Math.abs(err) < 0.8 ? go : 0.15, 0];
    const torque = clamp(2.5 * err - 1.6 * ship.omega, -1, 1);
    ship.throttles = allocateThrusters(ship.hull, force, torque);
    this.aimTurrets(ship);
  }

  /** Carriers hold back on their own side and turn their flank to bring flak to bear. */
  carrierManoeuvre(ship, target) {
    const side = ship.team === 0 ? -1 : 1;
    const holdX = side * 230;
    const dx = holdX - ship.x;
    const go = Math.abs(dx) > 30 ? 0.6 : 0;
    let heading = Math.atan2(0, dx);
    if (target && Math.abs(dx) <= 30) heading = Math.atan2(target.y - ship.y, target.x - ship.x) + Math.PI / 2;
    return [[go * Math.cos(wrap(heading - ship.heading)), 0], heading];
  }

  /** Line up, close to torpedo range, fire, then peel away and come round again. */
  bomberRun(ship, target, dist, aimHeading) {
    if (this.time < ship.breakingUntil) {
      const away = Math.atan2(ship.y - target.y, ship.x - target.x) + ship.orbitSign * 0.9;
      return [[1, 0], away];
    }
    if (dist < 110) {
      ship.breakingUntil = this.time + 3.5;
      ship.orbitSign = -ship.orbitSign;
    }
    const err = Math.abs(wrap(aimHeading - ship.heading));
    return [[err < 0.7 ? 1 : 0.25, 0], aimHeading];
  }

  aimTurrets(ship) {
    const hull = ship.hull;
    hull.turrets.forEach((turret, i) => {
      const weapon = WEAPONS[turret.weapon];
      const [mx, my] = toWorld(ship, turret.pos[0], turret.pos[1]);
      const probe = { ...ship, x: mx, y: my };
      // Torpedo racks only waste ordnance on capital ships if one is in reach.
      const target =
        weapon.kind === "torpedo"
          ? (this.nearestEnemy(probe, weapon.range, (o) => CAPITAL_ROLES.has(o.hull.role)) ?? this.nearestEnemy(probe, weapon.range * 0.5))
          : this.nearestEnemy(probe, weapon.range * 1.4);
      ship.turretCooldowns[i] = Math.max(0, ship.turretCooldowns[i] - DT * WEAPON_RATE_SCALE * systemPower(ship, "weapons"));
      ship.firing[i] = false;
      if (!target) return;
      const worldAngle = Math.atan2(target.y - my, target.x - mx);
      const rel = wrap(worldAngle - ship.heading);
      if (turret.arc > 0) {
        const half = deg(turret.arc) / 2;
        const fromRest = clamp(wrap(rel - deg(turret.rest)), -half, half);
        const want = deg(turret.rest) + fromRest;
        const delta = clamp(wrap(want - ship.turretAngles[i]), -deg(turret.slew) * DT, deg(turret.slew) * DT);
        ship.turretAngles[i] = wrap(ship.turretAngles[i] + delta);
      }
      const aimErr = Math.abs(wrap(rel - ship.turretAngles[i]));
      const dist = Math.hypot(target.x - mx, target.y - my);
      const tolerance = weapon.kind === "torpedo" ? 0.35 : turret.arc > 0 ? 0.06 : 0.1;
      if (aimErr < tolerance && dist < weapon.range && ship.turretCooldowns[i] === 0) {
        this.fire(ship, turret, i, mx, my, target);
      }
    });
  }

  fire(ship, turret, index, mx, my, target) {
    const weapon = WEAPONS[turret.weapon];
    ship.turretCooldowns[index] = weapon.interval * (0.85 + this.rng() * 0.3);
    ship.firing[index] = true;
    const spread = weapon.kind === "flak" ? (this.rng() - 0.5) * 0.12 : (this.rng() - 0.5) * 0.02;
    const angle = ship.heading + ship.turretAngles[index] + spread;
    this.events.muzzles.push({ x: mx, y: my, angle, team: ship.team, weapon: turret.weapon });
    if (weapon.kind === "beam") {
      this.fireBeam(ship, weapon, mx, my, angle);
      return;
    }
    const torpedo = weapon.kind === "torpedo";
    this.projectiles.push({
      x: mx,
      y: my,
      // Torpedoes leave the rack at their own speed; the launcher's velocity would let them outrun the turn.
      vx: (torpedo ? 0 : ship.vx) + Math.cos(angle) * weapon.speed,
      vy: (torpedo ? 0 : ship.vy) + Math.sin(angle) * weapon.speed,
      life: (weapon.range / weapon.speed) * (weapon.kind === "flak" ? 0.6 + this.rng() * 0.4 : torpedo ? 1.3 : 1),
      team: ship.team,
      kind: weapon.kind,
      damage: weapon.damage,
      targetId: torpedo ? target.id : -1,
      speed: weapon.speed,
    });
  }

  fireBeam(ship, weapon, x, y, angle) {
    const dx = Math.cos(angle);
    const dy = Math.sin(angle);
    let hitShip = null;
    let hitT = weapon.range;
    for (const other of this.ships) {
      if (!isActive(other) || other.team === ship.team) continue;
      const ox = other.x - x;
      const oy = other.y - y;
      const along = ox * dx + oy * dy;
      if (along < 0 || along > hitT) continue;
      const perp = Math.abs(ox * dy - oy * dx);
      if (perp < other.hull.radius) {
        hitT = along;
        hitShip = other;
      }
    }
    this.beams.push({ x1: x, y1: y, x2: x + dx * hitT, y2: y + dy * hitT, team: ship.team, ttl: 0.06 });
    if (hitShip) this.damage(hitShip, weapon.damage, x + dx * hitT, y + dy * hitT, ship.team);
  }

  integrate(ship) {
    const hull = ship.hull;
    let fx = 0;
    let fy = 0;
    let torque = 0;
    const engines = systemPower(ship, "engines");
    hull.thrusters.forEach((t, i) => {
      const f = t.force * ship.throttles[i] * engines;
      if (f === 0) return;
      const bx = t.dir[0] * f;
      const by = t.dir[1] * f;
      torque += t.pos[0] * by - t.pos[1] * bx;
      const c = Math.cos(ship.heading);
      const s = Math.sin(ship.heading);
      fx += bx * c - by * s;
      fy += bx * s + by * c;
    });
    const r = Math.hypot(ship.x, ship.y);
    if (r > ARENA_RADIUS) {
      fx -= (ship.x / r) * hull.mass * 40;
      fy -= (ship.y / r) * hull.mass * 40;
    }
    ship.vx += (fx / hull.mass) * DT;
    ship.vy += (fy / hull.mass) * DT;
    ship.omega += (torque / hull.inertia) * DT;
    ship.vx *= 0.995;
    ship.vy *= 0.995;
    ship.omega *= 0.94;
    const speed = Math.hypot(ship.vx, ship.vy);
    const speedCap = hull.speedCap * (0.6 + 0.4 * engines);
    if (speed > speedCap) {
      const k = 1 - Math.min(0.08, (speed - speedCap) / speed);
      ship.vx *= k;
      ship.vy *= k;
    }
    ship.x += ship.vx * DT;
    ship.y += ship.vy * DT;
    ship.heading = wrap(ship.heading + ship.omega * DT);
  }

  steerTorpedo(p) {
    const target = this.ships[p.targetId];
    if (!target || !isActive(target)) return;
    const want = Math.atan2(target.y - p.y, target.x - p.x);
    const have = Math.atan2(p.vy, p.vx);
    const next = have + clamp(wrap(want - have), -TORPEDO_TURN_RATE * DT, TORPEDO_TURN_RATE * DT);
    p.vx = Math.cos(next) * p.speed;
    p.vy = Math.sin(next) * p.speed;
  }

  advanceProjectiles() {
    const survivors = [];
    for (const p of this.projectiles) {
      if (p.kind === "torpedo") this.steerTorpedo(p);
      const nx = p.x + p.vx * DT;
      const ny = p.y + p.vy * DT;
      p.life -= DT;
      let consumed = false;
      for (const ship of this.ships) {
        if (!isActive(ship) || ship.team === p.team) continue;
        if (segmentHitsCircle(p.x, p.y, nx, ny, ship.x, ship.y, ship.hull.radius)) {
          this.damage(ship, p.damage, nx, ny, p.team);
          if (p.kind === "torpedo") this.events.explosions.push({ x: nx, y: ny, radius: 14, team: p.team, kind: "flak" });
          consumed = true;
          break;
        }
      }
      if (!consumed && p.life <= 0 && p.kind === "flak") {
        this.flakBurst(nx, ny, p.team, p.damage);
        consumed = true;
      }
      if (consumed || p.life <= 0) continue;
      p.x = nx;
      p.y = ny;
      survivors.push(p);
    }
    this.projectiles = survivors;
  }

  flakBurst(x, y, team, damage) {
    this.events.explosions.push({ x, y, radius: 10, team, kind: "flak" });
    for (const ship of this.ships) {
      if (!isActive(ship) || ship.team === team) continue;
      if (Math.hypot(ship.x - x, ship.y - y) < 14 + ship.hull.radius) {
        this.damage(ship, damage, x, y, team);
      }
    }
  }

  damage(ship, amount, x, y, sourceTeam) {
    ship.lastHitTime = this.time;
    if (ship.shield > 0) {
      // The shield takes the hit on a bubble around the hull; report where and facing which way.
      // A well-fed shield also shrugs off part of each hit.
      ship.shield = Math.max(0, ship.shield - amount / (0.7 + 0.3 * systemPower(ship, "shields")));
      let nx = x - ship.x;
      let ny = y - ship.y;
      const len = Math.hypot(nx, ny) || 1;
      nx /= len;
      ny /= len;
      const r = ship.hull.shield.radius;
      this.events.shieldHits.push({ x: ship.x + nx * r, y: ship.y + ny * r, nx, ny, targetId: ship.id, team: sourceTeam, depleted: ship.shield === 0 });
      return;
    }
    ship.hp -= amount;
    this.events.hits.push({ x, y, team: sourceTeam, targetId: ship.id });
    if (ship.hp <= 0 && ship.alive) {
      ship.alive = false;
      ship.hp = 0;
      ship.throttles = ship.throttles.map(() => 0);
      this.events.explosions.push({ x: ship.x, y: ship.y, radius: ship.hull.radius * 2.5, team: ship.team, kind: "death" });
      // A carrier that dies takes its unlaunched wing with it.
      if (ship === this.flagships[ship.team]) {
        for (const s of [...this.reserves[ship.team], ...this.hangar[ship.team]]) s.alive = false;
        this.reserves[ship.team] = [];
        this.hangar[ship.team] = [];
      }
    }
  }
}

function emptyEvents() {
  return { hits: [], shieldHits: [], explosions: [], muzzles: [], arrivals: [], launches: [], powerShifts: [], docks: [], rtb: [] };
}

export function isActive(ship) {
  return ship.alive && ship.present;
}

function segmentHitsCircle(x1, y1, x2, y2, cx, cy, r) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  const t = len2 > 0 ? clamp(((cx - x1) * dx + (cy - y1) * dy) / len2, 0, 1) : 0;
  const px = x1 + dx * t - cx;
  const py = y1 + dy * t - cy;
  return px * px + py * py < r * r;
}

export const SIM_DT = DT;
export { ARENA_RADIUS };
