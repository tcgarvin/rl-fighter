// Throwaway scripted 2D battle for art-direction demos. Not the real sim (that is Rust);
// it only needs to look plausible and exercise every visual: per-thruster throttle,
// independent turrets, bullets, beams, flak, hits and explosions.

import { HULLS, WEAPONS } from "./hulls.js";

const DT = 1 / 30;
const ARENA_RADIUS = 520;
const MATCH_TIME_LIMIT = 120;
const INTERMISSION = 4;
// Jump-in: squads arrive in sequence; ships within a squad are staggered by milliseconds.
const FIRST_SQUAD_DELAY = 1.0;
const SQUAD_INTERVAL = 0.3;
const SHIP_STAGGER_MAX = 0.08;
const ARRIVAL_SPEED_FACTOR = 1.4;
const ARRIVAL_CONTROL_LOCK = 0.7;
const SQUAD_SIZE = 3;

function mulberry32(seed) {
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
    // Not yet jumped in: invisible, untargetable and not simulated.
    present: false,
    arriveAt: 0,
    controlLockedUntil: 0,
    shield: hull.shield?.hp ?? 0,
    maxShield: hull.shield?.hp ?? 0,
    lastHitTime: -Infinity,
    throttles: hull.thrusters.map(() => 0),
    turretAngles: hull.turrets.map((t) => deg(t.rest)),
    turretCooldowns: hull.turrets.map(() => 0),
    firing: hull.turrets.map(() => false),
    orbitSign: 1,
  };
}

const ROSTER_TEMPLATES = [
  ["fighter", "fighter", "fighter", "strafer", "strafer", "gunship"],
  ["fighter", "fighter", "fighter", "fighter", "gunship"],
  ["strafer", "strafer", "strafer", "fighter", "fighter", "gunship"],
  ["fighter", "fighter", "strafer", "strafer", "gunship", "gunship"],
];

export class ScriptedBattle {
  constructor(seed = 1) {
    this.rng = mulberry32(seed);
    this.matchIndex = 0;
    this.events = emptyEvents();
    this.startMatch();
  }

  startMatch() {
    this.ships = [];
    this.projectiles = [];
    this.beams = [];
    this.time = 0;
    this.phase = "battle";
    this.intermission = 0;
    this.winner = -1;
    const rosterA = ROSTER_TEMPLATES[Math.floor(this.rng() * ROSTER_TEMPLATES.length)];
    const rosterB = ROSTER_TEMPLATES[Math.floor(this.rng() * ROSTER_TEMPLATES.length)];
    this.rosters = [rosterA, rosterB];
    let id = 0;
    [rosterA, rosterB].forEach((roster, team) => {
      const side = team === 0 ? -1 : 1;
      const heading = team === 0 ? 0 : Math.PI;
      // Squads: gunships jump alone, small craft in groups of up to SQUAD_SIZE.
      const heavy = roster.filter((h) => h === "gunship").map((h) => [h]);
      const light = roster.filter((h) => h !== "gunship");
      const squads = [];
      for (let i = 0; i < light.length; i += SQUAD_SIZE) squads.push(light.slice(i, i + SQUAD_SIZE));
      squads.push(...heavy);
      const teamOffset = team === 0 ? 0 : 0.5 + this.rng() * 0.6;
      squads.forEach((squad, squadIndex) => {
        const squadY = (squadIndex - (squads.length - 1) / 2) * 70 + (this.rng() - 0.5) * 30;
        const squadX = side * (230 + (squad[0] === "gunship" ? 50 : 0) + this.rng() * 30);
        const squadTime = FIRST_SQUAD_DELAY + teamOffset + squadIndex * SQUAD_INTERVAL * (0.6 + this.rng() * 0.8);
        squad.forEach((hullName, i) => {
          const row = i - (squad.length - 1) / 2;
          const x = squadX + Math.abs(row) * side * 10;
          const y = squadY + row * 16;
          const ship = makeShip(id++, hullName, team, x, y, heading);
          ship.orbitSign = this.rng() < 0.5 ? -1 : 1;
          ship.arriveAt = squadTime + this.rng() * SHIP_STAGGER_MAX;
          this.ships.push(ship);
        });
      });
    });
    this.matchIndex += 1;
  }

  /** Ships still in the fight, including those that haven't jumped in yet. */
  aliveCount(team) {
    return this.ships.filter((s) => s.alive && s.team === team).length;
  }

  nearestEnemy(ship, maxRange = Infinity) {
    let best = null;
    let bestD = maxRange;
    for (const other of this.ships) {
      if (!isActive(other) || other.team === ship.team) continue;
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
    if (this.phase === "intermission") {
      this.intermission -= DT;
      this.advanceProjectiles();
      if (this.intermission <= 0) this.startMatch();
      return;
    }
    this.time += DT;
    this.processArrivals();
    for (const ship of this.ships) {
      if (isActive(ship)) this.control(ship);
    }
    for (const ship of this.ships) {
      if (isActive(ship)) {
        this.integrate(ship);
        this.regenerateShield(ship);
      }
    }
    this.advanceProjectiles();
    this.beams = this.beams.filter((b) => (b.ttl -= DT) > 0);
    const a = this.aliveCount(0);
    const b = this.aliveCount(1);
    if (a === 0 || b === 0 || this.time > MATCH_TIME_LIMIT) {
      this.winner = a === b ? -1 : a > b ? 0 : 1;
      this.phase = "intermission";
      this.intermission = INTERMISSION;
    }
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

  regenerateShield(ship) {
    const spec = ship.hull.shield;
    if (!spec || this.time - ship.lastHitTime < spec.regenDelay) return;
    ship.shield = Math.min(ship.maxShield, ship.shield + spec.regenRate * DT);
  }

  control(ship) {
    const hull = ship.hull;
    if (this.time < ship.controlLockedUntil) {
      // Coasting out of the jump: no thrust, guns cold.
      ship.throttles = hull.thrusters.map(() => 0);
      ship.firing = hull.turrets.map(() => false);
      return;
    }
    const target = this.nearestEnemy(ship);
    let force = [0, 0];
    let desiredHeading = ship.heading;
    if (target) {
      const dx = target.x - ship.x;
      const dy = target.y - ship.y;
      const dist = Math.hypot(dx, dy);
      const bulletSpeed = 240;
      const tLead = dist / bulletSpeed;
      const ax = dx + (target.vx - ship.vx) * tLead;
      const ay = dy + (target.vy - ship.vy) * tLead;
      desiredHeading = Math.atan2(ay, ax);
      if (ship.hullName === "fighter") {
        const err = Math.abs(wrap(desiredHeading - ship.heading));
        const go = dist > 60 || err > 1.2 ? 1 : 0.3;
        force = [go * (err < 0.9 ? 1 : 0.2), 0];
      } else if (ship.hullName === "strafer") {
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

  aimTurrets(ship) {
    const hull = ship.hull;
    hull.turrets.forEach((turret, i) => {
      const weapon = WEAPONS[turret.weapon];
      const [mx, my] = toWorld(ship, turret.pos[0], turret.pos[1]);
      const target = this.nearestEnemy({ ...ship, x: mx, y: my }, weapon.range * 1.4);
      ship.turretCooldowns[i] = Math.max(0, ship.turretCooldowns[i] - DT);
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
      const tolerance = turret.arc > 0 ? 0.06 : 0.1;
      if (aimErr < tolerance && dist < weapon.range && ship.turretCooldowns[i] === 0) {
        this.fire(ship, turret, i, mx, my);
      }
    });
  }

  fire(ship, turret, index, mx, my) {
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
    this.projectiles.push({
      x: mx,
      y: my,
      vx: ship.vx + Math.cos(angle) * weapon.speed,
      vy: ship.vy + Math.sin(angle) * weapon.speed,
      life: (weapon.range / weapon.speed) * (weapon.kind === "flak" ? 0.6 + this.rng() * 0.4 : 1),
      team: ship.team,
      kind: weapon.kind,
      damage: weapon.damage,
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
    hull.thrusters.forEach((t, i) => {
      const f = t.force * ship.throttles[i];
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
    if (speed > hull.speedCap) {
      const k = 1 - Math.min(0.08, (speed - hull.speedCap) / speed);
      ship.vx *= k;
      ship.vy *= k;
    }
    ship.x += ship.vx * DT;
    ship.y += ship.vy * DT;
    ship.heading = wrap(ship.heading + ship.omega * DT);
  }

  advanceProjectiles() {
    const survivors = [];
    for (const p of this.projectiles) {
      const nx = p.x + p.vx * DT;
      const ny = p.y + p.vy * DT;
      p.life -= DT;
      let consumed = false;
      for (const ship of this.ships) {
        if (!isActive(ship) || ship.team === p.team) continue;
        if (segmentHitsCircle(p.x, p.y, nx, ny, ship.x, ship.y, ship.hull.radius)) {
          this.damage(ship, p.damage, nx, ny, p.team);
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
      ship.shield = Math.max(0, ship.shield - amount);
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
    }
  }
}

function emptyEvents() {
  return { hits: [], shieldHits: [], explosions: [], muzzles: [], arrivals: [] };
}

function isActive(ship) {
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
