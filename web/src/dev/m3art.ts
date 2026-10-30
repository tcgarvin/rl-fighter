// M3 art preview (dev-only page, web/dev/m3-art.html): the carrier, the transport and
// the strike craft in the Cinematic treatment with the live page's camera, playing the
// M3 effects (bay launch, jump charge + jump out, the quick jump-out, the order overlay,
// shield impacts and collapse, the major explosion) from small scripted scenes, with no
// sim. tools/web/art_shots.mjs screenshots it.
//
// URL: ?scene=lineup|convoy|launch|jump|quick|orders|shield|deplete|explode
//   &t=<s> fast-forwards to that time
// in fixed 1/60 s steps and then holds still (window.artReady turns true), for shots.

import * as THREE from "three";
import treatmentModule from "../render/treatments/cinematic.js";
import * as hullgeo from "../render/hullgeo.js";
import { createEffects, jumpOutOffset, JUMP_OUT_DURATION } from "../render/effects.js";
import { createEnvironment } from "../render/environment.js";
import { HULLS } from "../render/hulls.js";
import { FitCamera, TYPICAL_ZOOM, emptyBounds, growBounds } from "../live/camera.ts";

interface Vec2Spec {
  pos: [number, number];
  dir: [number, number];
}
interface HullSpec {
  role: string;
  length: number;
  beam: number;
  thrusters: Array<{ dir: [number, number] }>;
  turrets: Array<{ rest: number }>;
  bays?: Array<Vec2Spec & { id: string }>;
}
interface HullModel {
  object: THREE.Group;
  turrets: THREE.Object3D[];
  setThrottles(levels: ArrayLike<number>, dt: number): void;
  dispose(): void;
}
interface Order {
  kind: "attack" | "guard" | "hold" | "jump";
  team: number;
  x2: number;
  y2: number;
  radius?: number;
  x1?: number;
  y1?: number;
  progress?: number;
}
interface Effects {
  bayLaunch(e: { x: number; y: number; heading: number; team: number; size: number; speed: number }): void;
  jumpCharge(e: { object: THREE.Object3D; team: number; size: number; duration: number }): { cancel(): void };
  jumpOut(e: { x: number; y: number; heading: number; team: number; size: number }): void;
  jumpOutQuick(e: { x: number; y: number; heading: number; team: number; size: number }): void;
  arrival(e: { x: number; y: number; heading: number; team: number; size: number; duration: number }): void;
  drawOrders(orders: Order[]): void;
  shieldHit(e: { x: number; y: number; nx: number; ny: number; team: number; depleted: boolean; radius: number; object?: THREE.Object3D }): void;
  explosion(e: { x: number; y: number; radius: number; team: number; kind: string }): void;
  attachDamage(model: HullModel): { update(hp: number, visible: boolean, dt: number): void };
  update(dt: number): void;
}
interface Treatment {
  palette: unknown;
  init(o: { THREE: typeof THREE; scene: THREE.Scene; renderer: THREE.WebGLRenderer; camera: THREE.Camera }): void;
  materials(team: number): unknown;
  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, dt: number): void;
  onResize(width: number, height: number): void;
}

const STEP = 1 / 60;
const LAUNCH_SPEED = 60;
// The launch coast: controls locked, engines cold, then the craft turns to the fleet heading.
const LAUNCH_LOCK = 0.6;
const CHARGE = 2;

const treatment = treatmentModule as unknown as Treatment;
const hulls = HULLS as unknown as Record<string, HullSpec>;
const params = new URLSearchParams(location.search);
const sceneName = params.get("scene") ?? "lineup";
const seekTo = params.has("t") ? Math.max(0, Number(params.get("t"))) : null;
const closeSpan = Math.max(0, Number(params.get("close") ?? 0) || 0);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.prepend(renderer.domElement);
const scene = new THREE.Scene();
const cam = new FitCamera(window.innerWidth / window.innerHeight);
const ctx = { THREE, scene, renderer, camera: cam.camera };
treatment.init(ctx);
const environment = createEnvironment(ctx) as unknown as { newMatch(seed: number): void; update(dt: number, v: { centerX: number; centerY: number; extent: number }): void };
const fx = createEffects({ ...ctx, palette: treatment.palette }) as unknown as Effects;
environment.newMatch(7);

class Ship {
  readonly model: HullModel;
  readonly hull: HullSpec;
  x: number;
  y: number;
  heading: number;
  speed: number;
  /** Heading the ship turns toward (rad/s limited) once its launch coast is over. */
  goal: number;
  shown: boolean;
  launchedAt = -Infinity;
  departAt = Infinity;
  hp = 1;
  damage: { update(hp: number, visible: boolean, dt: number): void } | null = null;

  constructor(readonly name: string, readonly team: number, x: number, y: number, heading: number, speed = 0, shown = true) {
    const hull = hulls[name];
    if (!hull) throw new Error(`no render spec for hull ${name}`);
    this.hull = hull;
    this.model = hullgeo.buildHull(hull, team, treatment.materials(team)) as unknown as HullModel;
    scene.add(this.model.object);
    this.x = x;
    this.y = y;
    this.heading = heading;
    this.goal = heading;
    this.speed = speed;
    this.shown = shown;
    this.model.turrets.forEach((pivot, i) => (pivot.rotation.y = ((hull.turrets[i]?.rest ?? 0) * Math.PI) / 180));
  }

  step(dt: number, t: number): void {
    if (!this.shown) return;
    if (t - this.launchedAt > LAUNCH_LOCK) {
      const d = Math.atan2(Math.sin(this.goal - this.heading), Math.cos(this.goal - this.heading));
      this.heading += Math.sign(d) * Math.min(Math.abs(d), 1.6 * dt);
    }
    this.x += Math.cos(this.heading) * this.speed * dt;
    this.y += Math.sin(this.heading) * this.speed * dt;
  }

  draw(dt: number, t: number): void {
    const age = t - this.departAt;
    const gone = age > JUMP_OUT_DURATION;
    const visible = this.shown && !gone;
    const obj = this.model.object;
    obj.visible = visible;
    const ahead = age >= 0 ? jumpOutOffset(age) : 0;
    obj.position.set(this.x + Math.cos(this.heading) * ahead, 0, -(this.y + Math.sin(this.heading) * ahead));
    obj.rotation.set(0, this.heading, 0);
    obj.updateMatrixWorld();
    const coasting = t - this.launchedAt < LAUNCH_LOCK;
    const main = coasting || this.speed === 0 ? 0 : Math.min(1, 0.25 + this.speed / 60);
    this.model.setThrottles(this.hull.thrusters.map((th) => (th.dir[0] > 0.5 ? main : 0)), dt);
    this.damage?.update(this.hp, visible, dt);
  }

  /** World position of a body-frame point. */
  local(px: number, py: number): [number, number] {
    const c = Math.cos(this.heading);
    const s = Math.sin(this.heading);
    return [this.x + px * c - py * s, this.y + px * s + py * c];
  }
}

interface Scene {
  ships: Ship[];
  events: Array<{ at: number; run: () => void }>;
  orders?: (t: number) => Order[];
  /** Extra points to keep in frame (markers), sim metres. */
  frame?: Array<[number, number]>;
  caption: string;
}

function launch(carrier: Ship, craft: Ship, bayIndex: number, t: number): void {
  const bay = carrier.hull.bays?.[bayIndex];
  if (!bay) throw new Error(`${carrier.name} has no bay ${bayIndex}`);
  const [x, y] = carrier.local(bay.pos[0], bay.pos[1]);
  const heading = carrier.heading + Math.atan2(bay.dir[1], bay.dir[0]);
  Object.assign(craft, { x, y, heading, speed: LAUNCH_SPEED, shown: true, launchedAt: t, goal: carrier.heading });
  fx.bayLaunch({ x, y, heading, team: craft.team, size: craft.hull.length, speed: LAUNCH_SPEED });
}

function charge(ship: Ship, at: number, events: Scene["events"]): void {
  events.push({ at, run: () => void fx.jumpCharge({ object: ship.model.object, team: ship.team, size: ship.hull.length, duration: CHARGE }) });
  events.push({
    at: at + CHARGE,
    run: () => {
      ship.departAt = at + CHARGE;
      fx.jumpOut({ x: ship.x, y: ship.y, heading: ship.heading, team: ship.team, size: ship.hull.length });
    },
  });
}

/** A shot from bearing `bearing` (rad, sim frame) landing on `ship`'s shield of radius r. */
function shieldShot(ship: Ship, bearing: number, r: number, depleted = false): void {
  const nx = Math.cos(bearing);
  const ny = Math.sin(bearing);
  const shooter = ship.team === 0 ? 1 : 0;
  fx.shieldHit({ x: ship.x + nx * r, y: ship.y + ny * r, nx, ny, team: shooter, depleted, radius: r, object: ship.model.object });
}

function centroid(ships: Ship[]): [number, number] {
  return [ships.reduce((a, s) => a + s.x, 0) / ships.length, ships.reduce((a, s) => a + s.y, 0) / ships.length];
}

const SCENES: Record<string, () => Scene> = {
  // Every hull side by side, nose +x, for scale and silhouette.
  lineup: () => {
    const ships = [
      new Ship("carrier", 0, 0, 48, 0),
      new Ship("freighter", 0, 4, 18, 0),
      new Ship("gunship", 0, -2, -2, 0),
      new Ship("bomber", 0, -2, -18, 0),
      new Ship("fighter", 0, -2, -32, 0),
      new Ship("strafer", 0, -2, -46, 0),
      new Ship("freighter", 1, 62, 30, Math.PI),
      new Ship("gunship", 1, 62, 6, Math.PI),
      new Ship("fighter", 1, 62, -10, Math.PI),
      new Ship("carrier", 1, 66, -40, Math.PI),
    ];
    return { ships, events: [], caption: "lineup: carrier, freighter, gunship, bomber, fighter, strafer (blue); freighter, gunship, fighter, carrier (orange)" };
  },
  // The two capital-scale hulls next to a gunship and a fighter, for a close look (?close=90).
  detail: () => {
    const ships = [
      new Ship("carrier", 0, 0, 22, 0),
      new Ship("freighter", 0, -4, -6, 0),
      new Ship("gunship", 1, -10, -26, 0),
      new Ship("fighter", 1, 12, -26, 0),
    ];
    return { ships, events: [], caption: "detail: carrier and freighter (blue), gunship and fighter (orange)" };
  },
  // A convoy at battle scale: four transports, an escort, and the strike force inbound.
  convoy: () => {
    const h = 0.12;
    const ships = [
      new Ship("freighter", 0, 0, 0, h, 12),
      new Ship("freighter", 0, -40, 22, h, 12),
      new Ship("freighter", 0, -40, -22, h, 12),
      new Ship("freighter", 0, -80, 0, h, 12),
      new Ship("carrier", 0, -170, 10, h, 9),
      new Ship("fighter", 0, 40, 30, 0.3, 50),
      new Ship("fighter", 0, 30, -40, -0.2, 50),
      new Ship("gunship", 0, -20, 50, h, 14),
      new Ship("fighter", 1, 260, 60, Math.PI + 0.25, 55),
      new Ship("fighter", 1, 280, 40, Math.PI + 0.2, 55),
      new Ship("fighter", 1, 270, -50, Math.PI - 0.15, 55),
      new Ship("bomber", 1, 310, 0, Math.PI, 30),
      new Ship("bomber", 1, 320, -24, Math.PI, 30),
      new Ship("gunship", 1, 350, 30, Math.PI, 18),
    ];
    const hurt = ships[1]!;
    hurt.hp = 0.35;
    hurt.damage = fx.attachDamage(hurt.model);
    return { ships, events: [], caption: "convoy: four freighters (one damaged), carrier and escort; strike force inbound" };
  },
  launch: () => {
    const carrier = new Ship("carrier", 0, 0, 0, 0.35, 8);
    const enemy = new Ship("carrier", 1, 190, 40, Math.PI + 0.2, 8);
    const ships = [carrier, enemy];
    const events: Scene["events"] = [];
    const craft = ["fighter", "fighter", "bomber", "fighter", "strafer", "fighter"];
    craft.forEach((name, i) => {
      const s = new Ship(name, 0, 0, 0, 0, 0, false);
      ships.push(s);
      events.push({ at: 0.3 + i * 0.6, run: () => launch(carrier, s, i % 2, 0.3 + i * 0.6) });
      const e = new Ship(name, 1, 0, 0, 0, 0, false);
      ships.push(e);
      events.push({ at: 0.6 + i * 0.6, run: () => launch(enemy, e, i % 2, 0.6 + i * 0.6) });
    });
    return { ships, events, caption: "bay launch: craft leave both carriers' bays, alternating port and starboard" };
  },
  jump: () => {
    const ships = [
      new Ship("freighter", 0, 0, 0, 0, 10),
      new Ship("freighter", 0, -38, 20, 0, 10),
      new Ship("freighter", 0, -38, -20, 0, 10),
      new Ship("freighter", 0, -76, 0, 0, 10),
      new Ship("fighter", 0, 20, 40, 0.1, 40),
      new Ship("fighter", 0, 10, -45, -0.1, 40),
      new Ship("freighter", 1, 30, -95, 0.3, 10),
    ];
    const events: Scene["events"] = [];
    charge(ships[0]!, 0.3, events);
    charge(ships[1]!, 1.2, events);
    charge(ships[6]!, 0.6, events);
    return { ships, events, caption: "jump: freighters spool the drive (2 s) and leave as a streak" };
  },
  // Match end: the surviving defenders all jump out, staggered.
  quick: () => {
    const ships = [
      new Ship("gunship", 1, 0, 0, 0.2, 14),
      new Ship("fighter", 1, 30, 30, 0.4, 45),
      new Ship("fighter", 1, 25, -25, 0.1, 45),
      new Ship("strafer", 1, -20, 40, 0.3, 40),
      new Ship("fighter", 1, -35, -10, 0.2, 45),
      new Ship("bomber", 1, -10, -50, 0.15, 30),
      new Ship("carrier", 0, -150, 20, 0, 0),
    ];
    const events: Scene["events"] = [];
    ships.slice(0, 6).forEach((s, i) => {
      const at = 0.5 + i * 0.09;
      events.push({
        at,
        run: () => {
          s.departAt = at;
          fx.jumpOutQuick({ x: s.x, y: s.y, heading: s.heading, team: s.team, size: s.hull.length });
        },
      });
    });
    return { ships, events, caption: "quick jump-out: the defenders leave at the end of the match" };
  },
  orders: () => {
    const carrier = new Ship("carrier", 0, -140, 0, 0.1, 6);
    const enemy = new Ship("carrier", 1, 170, -30, Math.PI, 6);
    const guard = [new Ship("fighter", 0, -110, 40, 0.2, 30), new Ship("fighter", 0, -120, -40, -0.3, 30)];
    const strike = [new Ship("fighter", 0, -10, 40, -0.1, 45), new Ship("fighter", 0, -20, 55, -0.1, 45), new Ship("bomber", 0, -30, 30, -0.1, 30)];
    const holders = [new Ship("fighter", 1, 60, -110, 2.5, 20), new Ship("gunship", 1, 75, -120, 2.7, 10)];
    const ships = [carrier, enemy, ...guard, ...strike, ...holders];
    const jumpPoint: [number, number] = [-40, -170];
    const orders = (t: number): Order[] => {
      const [sx, sy] = centroid(strike);
      const [gx, gy] = centroid(guard);
      const [hx, hy] = centroid(holders);
      return [
        { kind: "attack", team: 0, x1: sx, y1: sy, x2: enemy.x, y2: enemy.y, radius: 28 },
        { kind: "guard", team: 0, x1: gx, y1: gy, x2: carrier.x, y2: carrier.y, radius: 30 },
        { kind: "hold", team: 1, x1: hx, y1: hy, x2: 70, y2: -60, radius: 36 },
        { kind: "jump", team: 0, x1: carrier.x, y1: carrier.y, x2: jumpPoint[0], y2: jumpPoint[1], radius: 50, progress: Math.min(1, 0.35 + t * 0.1) },
      ];
    };
    return { ships, events: [], orders, frame: [jumpPoint], caption: "orders: attack (brackets), guard (ring), hold (ticked ring), jump point (progress arc)" };
  },
  // Shield impacts: a single hit on each shield, then sustained fire on the gunship and
  // the carrier (several hits a second from a narrow arc), as in a capital-ship fight.
  shield: () => {
    const gunship = new Ship("gunship", 0, 0, 0, 0.3, 14);
    const strafer = new Ship("strafer", 1, 46, -22, Math.PI - 0.4, 0);
    const carrier = new Ship("carrier", 1, 40, 42, Math.PI + 0.1, 4);
    const ships = [gunship, strafer, carrier];
    const events: Scene["events"] = [
      { at: 0.3, run: () => shieldShot(gunship, 0.5, 11) },
      { at: 0.35, run: () => shieldShot(strafer, 2.6, 7.5) },
      { at: 0.4, run: () => shieldShot(carrier, -2.2, 24) },
    ];
    for (let i = 0; i < 12; i++) {
      const at = 1.0 + i * 0.13;
      events.push({ at, run: () => shieldShot(gunship, 0.2 + Math.sin(i * 2.1) * 0.5, 11) });
      events.push({ at: at + 0.05, run: () => shieldShot(carrier, -2.6 + Math.sin(i * 1.7) * 0.6, 24) });
    }
    return { ships, events, caption: "shield: single impacts (gunship, strafer, carrier), then sustained fire on the gunship and carrier" };
  },
  // Shield collapse: the last hit takes the shield down (depleted).
  deplete: () => {
    const gunship = new Ship("gunship", 0, 0, 0, 0.3, 10);
    const carrier = new Ship("carrier", 1, 50, 30, Math.PI + 0.1, 0);
    const strafer = new Ship("strafer", 1, 40, -26, Math.PI - 0.4, 0);
    const ships = [gunship, carrier, strafer];
    const events: Scene["events"] = [
      { at: 0.2, run: () => shieldShot(gunship, 0.4, 11) },
      { at: 0.3, run: () => shieldShot(gunship, 0.6, 11, true) },
      { at: 0.4, run: () => shieldShot(carrier, -2.4, 24, true) },
      { at: 0.5, run: () => shieldShot(strafer, 2.4, 7.5, true) },
    ];
    return { ships, events, caption: "deplete: shields collapse (gunship, carrier, strafer)" };
  },
  // A kill: the immediate 'death' burst, then the hulk blows up big ('major').
  explode: () => {
    const fighter = new Ship("fighter", 0, -10, -30, 0.4, 0);
    const carrier = new Ship("carrier", 1, 40, 25, Math.PI + 0.1, 0);
    const gunship = new Ship("gunship", 0, -30, 30, 0.2, 0);
    const witness = new Ship("fighter", 1, 70, -40, 2.4, 0);
    const ships = [fighter, carrier, gunship, witness];
    const kill = (s: Ship, at: number, majorAt: number, radius: number, events: Scene["events"]) => {
      events.push({ at, run: () => fx.explosion({ x: s.x, y: s.y, radius, team: s.team, kind: "death" }) });
      events.push({
        at: majorAt,
        run: () => {
          s.shown = false;
          fx.explosion({ x: s.x, y: s.y, radius, team: s.team, kind: "major" });
        },
      });
    };
    const events: Scene["events"] = [];
    kill(fighter, 0.2, 0.5, 6.5, events);
    kill(carrier, 0.3, 0.7, 50, events);
    kill(gunship, 1.6, 2.2, 15, events);
    return { ships, events, caption: "explode: death burst, then the major blow-up (fighter 6.5 m, carrier 50 m, gunship 15 m)" };
  },
};

const build = SCENES[sceneName];
if (!build) throw new Error(`unknown scene ${sceneName}; one of ${Object.keys(SCENES).join(", ")}`);
const current = build();
document.getElementById("caption")!.textContent = current.caption;
current.events.sort((a, b) => a.at - b.at);
let time = 0;
let nextEvent = 0;

function layout(): void {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h);
  treatment.onResize(w, h);
  // The live page's HUD leaves roughly this band free.
  cam.setSafeBand(w, h, w < 600 ? 110 : 90, h - (w < 600 ? 120 : 90));
}

/** ?close=<metres>: a fixed close shot of that width, at the live camera's pitch. */
function closeUp(b: ReturnType<typeof emptyBounds>): void {
  const camera = cam.camera;
  const cx = (b.minX + b.maxX) / 2;
  const cy = (b.minY + b.maxY) / 2;
  const portrait = camera.aspect < 1;
  const halfFov = THREE.MathUtils.degToRad(camera.fov) / 2;
  // Fit the span across the screen's narrow axis.
  const dist = closeSpan / 2 / (Math.tan(halfFov) * Math.min(1, camera.aspect));
  const pitch = (58 * Math.PI) / 180;
  const back = Math.cos(pitch) * dist;
  if (portrait) camera.position.set(cx - back, Math.sin(pitch) * dist, -cy);
  else camera.position.set(cx, Math.sin(pitch) * dist, -cy + back);
  camera.lookAt(cx, 0, -cy);
  camera.updateMatrixWorld();
}

function advance(dt: number): void {
  time += dt;
  while (nextEvent < current.events.length && current.events[nextEvent]!.at <= time) current.events[nextEvent++]!.run();
  for (const s of current.ships) s.step(dt, time);
  const bounds = emptyBounds();
  for (const s of current.ships) {
    s.draw(dt, time);
    if (s.shown && time - s.departAt < JUMP_OUT_DURATION) growBounds(bounds, s.x, s.y);
  }
  for (const [x, y] of current.frame ?? []) growBounds(bounds, x, y);
  // Departed ships keep their last spot in frame, so the streak's origin stays put.
  for (const s of current.ships) if (time - s.departAt >= JUMP_OUT_DURATION) growBounds(bounds, s.x, s.y);
  if (current.orders) fx.drawOrders(current.orders(time));
  cam.update(bounds, dt);
  if (closeSpan > 0) closeUp(bounds);
  environment.update(dt, { centerX: cam.x, centerY: cam.y, extent: cam.extent, projection: cam.baseProjection, layoutZoom: TYPICAL_ZOOM });
  fx.update(dt);
}

layout();
window.addEventListener("resize", layout);
const w = window as unknown as { artReady: boolean };
w.artReady = false;
if (seekTo !== null) {
  // Fixed steps up to the requested time, then one still frame (a second one lets the
  // treatment's history settle). The camera eases exactly as it would live.
  cam.snap();
  while (time + STEP <= seekTo + 1e-9) advance(STEP);
  treatment.render(renderer, scene, cam.camera, STEP);
  treatment.render(renderer, scene, cam.camera, 0);
  w.artReady = true;
} else {
  let last = performance.now();
  const loop = (now: number) => {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    advance(dt);
    treatment.render(renderer, scene, cam.camera, dt);
    requestAnimationFrame(loop);
  };
  cam.snap();
  requestAnimationFrame(loop);
  w.artReady = true;
}
