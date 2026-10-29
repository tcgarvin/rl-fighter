// The three.js side of the live page: the cinematic treatment, backdrop, effects and
// one hull model per ship, drawn by interpolating between sim ticks. Ships jump in as
// in the duel (a ~55 ms streak and a landing flash), damage shows as smoke, flame and
// arcing on the hull (no health bars), and a destroyed ship's wreck drifts and burns
// for a few seconds before it breaks up.

import * as THREE from "three";
import treatmentModule from "../render/treatments/cinematic.js";
import * as hullgeo from "../render/hullgeo.js";
import { createEffects } from "../render/effects.js";
import { createEnvironment } from "../render/environment.js";
import { renderHullThumbnails } from "../render/thumbs.js";
import { HULLS } from "../render/hulls.js";
import { FitCamera, emptyBounds, growBounds } from "./camera.ts";
import type { LiveMatch } from "./match.ts";
import type { SimEvent } from "./sim.ts";

// Jump-in streak, as in the story and the duel.
const JUMP_DISTANCE = 900;
const JUMP_DURATION = 0.055;
const DEATH_RADIUS_SCALE = 2.5;
// Largest crash flash radius, metres (a 100 m/s head-on reaches it).
const COLLISION_FLASH_MAX = 4;
// A wreck burns this long, then breaks up; long enough to outlast the result banner's
// first beats when the last ship of a side goes.
const WRECK_BURN = 3.2;
// Wreck drift decays at this rate (1/s), so it coasts rather than flies on.
const WRECK_DRAG = 0.7;
// The hp fraction a wreck burns at: below the flame and arcing thresholds.
const WRECK_HP = 0.12;
const BEAM_TTL = 0.06;
// Weapon ids are assets/weapons.yaml file order (SIM_SPEC §4.2); `Fire` carries one.
const WEAPON_NAMES = ["gauss", "laser", "flak", "torpedo"];

/** The render-side hull spec in render/hulls.js (body frame, metres). */
export interface HullSpec {
  role: string;
  length: number;
  beam: number;
  radius: number;
  shield?: { radius: number };
}

interface HullModel {
  object: THREE.Group;
  turrets: THREE.Object3D[];
  setThrottles(throttles: ArrayLike<number>, dt: number): void;
  dispose(): void;
}

interface DamageFx {
  update(hpFraction: number, visible: boolean, dt: number): void;
  dispose(): void;
}

interface Effects {
  updateProjectiles(projectiles: LiveMatch["projectiles"], beams: Beam[], alpha: number): void;
  muzzle(e: { x: number; y: number; angle: number; team: number; weapon: string }): void;
  hit(e: { x: number; y: number; team: number; targetId: number }): void;
  shieldHit(e: { x: number; y: number; nx: number; ny: number; team: number; depleted: boolean; radius: number }): void;
  explosion(e: { x: number; y: number; radius: number; team: number; kind: string }): void;
  arrival(e: { x: number; y: number; heading: number; team: number; size: number; duration: number }): void;
  attachDamage(model: HullModel): DamageFx;
  update(dt: number): void;
}

interface Environment {
  newMatch(seed: number): void;
  update(dt: number, view: { centerX: number; centerY: number; extent: number }): void;
}

interface Treatment {
  palette: unknown;
  init(o: { THREE: typeof THREE; scene: THREE.Scene; renderer: THREE.WebGLRenderer; camera: THREE.Camera }): void;
  materials(team: number): unknown;
  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, dt: number): void;
  onResize(width: number, height: number): void;
}

interface Beam {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  team: number;
  ttl: number;
}

interface Wreck {
  x: number;
  y: number;
  vx: number;
  vy: number;
  heading: number;
  omega: number;
  age: number;
}

interface ShipView {
  model: HullModel;
  hull: HullSpec;
  damage: DamageFx;
  jumpStart: number;
  wreck: Wreck | null;
  /** Interpolation origin: the ship at the previous tick. */
  prev: { x: number; y: number; heading: number };
}

const treatment = treatmentModule as unknown as Treatment;
const hullSpecs = HULLS as unknown as Record<string, HullSpec>;

/** The render spec for a catalogue hull, if the renderer has a model for it. */
export function hullSpec(name: string): HullSpec | undefined {
  return hullSpecs[name];
}

function drift(w: Wreck, dt: number): void {
  w.age += dt;
  const drag = Math.exp(-WRECK_DRAG * dt);
  w.vx *= drag;
  w.vy *= drag;
  w.x += w.vx * dt;
  w.y += w.vy * dt;
  w.heading += w.omega * dt;
}

function lerpAngle(a: number, b: number, t: number): number {
  return a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * t;
}

export class World {
  readonly renderer: THREE.WebGLRenderer;
  readonly cam: FitCamera;
  private readonly scene = new THREE.Scene();
  private readonly environment: Environment;
  private readonly effects: Effects;
  private views: ShipView[] = [];
  private beams: Beam[] = [];
  private match: LiveMatch | null = null;
  private ring: THREE.Line | null = null;
  private ringRadius = 0;
  private elapsed = 0;
  private readonly tagPos = new THREE.Vector3();

  constructor(parent: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    parent.prepend(this.renderer.domElement);
    this.cam = new FitCamera(window.innerWidth / window.innerHeight);
    const ctx = { THREE, scene: this.scene, renderer: this.renderer, camera: this.cam.camera };
    treatment.init(ctx);
    this.environment = createEnvironment(ctx) as unknown as Environment;
    this.effects = createEffects({ ...ctx, palette: treatment.palette }) as unknown as Effects;
  }

  /** Card images for every hull the renderer and the catalogue both know: [team0, team1]. */
  thumbnails(names: string[]): Record<string, [string, string]> {
    const hulls = Object.fromEntries(names.filter((n) => hullSpecs[n]).map((n) => [n, hullSpecs[n]]));
    return renderHullThumbnails({ THREE, hullgeo, treatment, hulls }) as Record<string, [string, string]>;
  }

  resize(width: number, height: number, safeTopPx: number, safeBottomPx: number): void {
    this.renderer.setSize(width, height);
    this.cam.setSafeBand(width, height, safeTopPx, safeBottomPx);
    treatment.onResize(width, height);
  }

  /** A faint ring at the arena radius (leaving it drains hull). Rebuilt only on change. */
  setArena(radius: number): void {
    if (radius === this.ringRadius) return;
    if (this.ring) {
      this.scene.remove(this.ring);
      this.ring.geometry.dispose();
      (this.ring.material as THREE.Material).dispose();
    }
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 256; i++) {
      const a = (i / 256) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * radius, 0, -Math.sin(a) * radius));
    }
    this.ring = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0x8c99a8, transparent: true, opacity: 0.18, depthWrite: false }),
    );
    this.scene.add(this.ring);
    this.ringRadius = radius;
  }

  /** Drop the last match's ships and build models for `match`'s (not yet arrived). */
  beginMatch(match: LiveMatch): void {
    for (const v of this.views) {
      v.damage.dispose();
      v.model.dispose();
    }
    this.views = [];
    this.beams = [];
    this.match = match;
    for (const [i, ship] of match.ships.entries()) {
      const name = match.hullNames[i]!;
      const hull = hullSpecs[name];
      if (!hull) throw new Error(`no render model for hull ${name}`);
      const model = hullgeo.buildHull(hull, ship.team, treatment.materials(ship.team)) as unknown as HullModel;
      model.object.visible = false;
      this.scene.add(model.object);
      this.views.push({
        model,
        hull,
        damage: this.effects.attachDamage(model),
        jumpStart: -Infinity,
        wreck: null,
        prev: { x: ship.x, y: ship.y, heading: ship.heading },
      });
    }
    this.environment.newMatch(match.seed);
    this.cam.snap();
  }

  /** Call before each sim step: the current state becomes the interpolation origin. */
  beforeStep(): void {
    const m = this.match;
    if (!m) return;
    for (const [i, v] of this.views.entries()) {
      const s = m.ships[i]!;
      v.prev.x = s.x;
      v.prev.y = s.y;
      v.prev.heading = s.heading;
    }
  }

  /**
   * React to the last step's events. `quiet` (fast-forward) skips the effects but
   * still starts wrecks, so a fast-forwarded result still shows one burning.
   */
  dispatch(events: SimEvent[], quiet = false): void {
    const m = this.match;
    if (!m) return;
    this.beams = [];
    const fx = this.effects;
    for (const e of events) {
      const ship = m.ships[e.a];
      const view = this.views[e.a];
      if (e.kind === "death" && ship && view) {
        view.wreck = { x: e.x, y: e.y, vx: ship.vx, vy: ship.vy, heading: ship.heading, omega: ship.omega * 0.5 + 0.4, age: 0 };
        if (!quiet) fx.explosion({ x: e.x, y: e.y, radius: view.hull.radius * DEATH_RADIUS_SCALE, team: ship.team, kind: "death" });
        continue;
      }
      if (quiet) continue;
      const shooter = m.ships[e.b];
      switch (e.kind) {
        case "fire":
          fx.muzzle({ x: e.x, y: e.y, angle: e.extra, team: ship?.team ?? 0, weapon: WEAPON_NAMES[e.f5] ?? "gauss" });
          break;
        case "beam":
          this.beams.push({ x1: e.x, y1: e.y, x2: e.f5, y2: e.f6, team: ship?.team ?? 0, ttl: BEAM_TTL });
          break;
        case "hit":
          fx.hit({ x: e.x, y: e.y, team: shooter?.team ?? 0, targetId: e.a });
          break;
        case "shieldHit":
          fx.shieldHit({ x: e.x, y: e.y, nx: e.f5, ny: e.f6, team: shooter?.team ?? 0, depleted: e.extra > 0.5, radius: view?.hull.shield?.radius ?? 8 });
          break;
        case "burst":
          fx.explosion({ x: e.x, y: e.y, radius: e.extra, team: e.a, kind: "flak" });
          break;
        case "arrival":
          if (!view || !ship) break;
          view.jumpStart = this.elapsed;
          fx.arrival({ x: e.x, y: e.y, heading: e.extra, team: ship.team, size: view.hull.length, duration: JUMP_DURATION });
          break;
        case "collision":
          // A teamless (white) flash with the hit's amber sparks, a bit bigger the
          // harder the ships met (extra = closing speed, m/s).
          fx.hit({ x: e.x, y: e.y, team: -1, targetId: e.a });
          fx.explosion({ x: e.x, y: e.y, radius: Math.min(COLLISION_FLASH_MAX, 1.5 + e.extra / 40), team: -1, kind: "collision" });
          break;
      }
    }
  }

  /** Age the wrecks without drawing (a fast-forward), so old ones have burnt out. */
  advanceWrecks(dt: number): void {
    for (const v of this.views) if (v.wreck && v.wreck.age <= WRECK_BURN) drift(v.wreck, dt);
  }

  /** No streaks for ships that arrived during a fast-forward. */
  settle(): void {
    for (const v of this.views) v.jumpStart = -Infinity;
  }

  /**
   * Draw one frame. `alpha` is the fraction of a tick since the last step; `frameAll`
   * keeps burning wrecks in the shot (the result hold) as well as live ships.
   */
  frame(dt: number, alpha: number, frameAll: boolean): void {
    this.elapsed += dt;
    const m = this.match;
    const bounds = emptyBounds();
    if (m) {
      for (const [i, v] of this.views.entries()) this.drawShip(m, i, v, dt, alpha, bounds, frameAll);
      for (const b of this.beams) b.ttl -= dt;
      // Projectiles are at the current tick and ships between the previous and current
      // one, so back the shots up by a tick to keep them on the muzzles.
      this.effects.updateProjectiles(m.projectiles, this.beams, alpha - 1);
    }
    this.cam.update(bounds, dt);
    this.environment.update(dt, { centerX: this.cam.x, centerY: this.cam.y, extent: this.cam.extent });
    this.effects.update(dt);
    treatment.render(this.renderer, this.scene, this.cam.camera, dt);
  }

  private drawShip(m: LiveMatch, i: number, v: ShipView, dt: number, alpha: number, bounds: ReturnType<typeof emptyBounds>, frameAll: boolean): void {
    const ship = m.ships[i]!;
    const obj = v.model.object;
    if (v.wreck) {
      this.drawWreck(v, dt, frameAll ? bounds : null, ship.team);
      return;
    }
    let x = v.prev.x + (ship.x - v.prev.x) * alpha;
    let y = v.prev.y + (ship.y - v.prev.y) * alpha;
    const heading = lerpAngle(v.prev.heading, ship.heading, alpha);
    const jumpT = (this.elapsed - v.jumpStart) / JUMP_DURATION;
    if (jumpT < 1) {
      const back = JUMP_DISTANCE * (1 - jumpT) ** 3;
      x -= Math.cos(heading) * back;
      y -= Math.sin(heading) * back;
    }
    const visible = ship.alive && ship.present;
    obj.visible = visible;
    obj.position.set(x, 0, -y);
    obj.rotation.set(0, heading, 0);
    obj.updateMatrixWorld();
    v.model.setThrottles(ship.throttles, dt);
    v.model.turrets.forEach((pivot, k) => (pivot.rotation.y = ship.turretAngles[k] ?? 0));
    v.damage.update(Math.max(0, ship.hp) / (m.maxHp[i] ?? 1), visible, dt);
    // Ships yet to jump in count too, so the empty field is framed where they'll appear.
    if (ship.alive) growBounds(bounds, ship.x, ship.y);
  }

  private drawWreck(v: ShipView, dt: number, bounds: ReturnType<typeof emptyBounds> | null, team: number): void {
    const w = v.wreck!;
    const obj = v.model.object;
    if (w.age > WRECK_BURN) {
      obj.visible = false;
      return;
    }
    drift(w, dt);
    obj.visible = true;
    obj.position.set(w.x, -w.age * 0.6, -w.y);
    // A slow tumble: the wreck rolls as it spins.
    obj.rotation.set(w.age * 0.35, w.heading, 0);
    obj.updateMatrixWorld();
    v.model.setThrottles([], dt);
    v.damage.update(WRECK_HP, true, dt);
    if (bounds) growBounds(bounds, w.x, w.y);
    if (w.age > WRECK_BURN) {
      obj.visible = false;
      this.effects.explosion({ x: w.x, y: w.y, radius: v.hull.radius * 1.2, team, kind: "death" });
    }
  }

  /** Screen position and drawn length (CSS px) of ship `i`, or null when it isn't on show. */
  shipOnScreen(i: number, width: number, height: number): { x: number; y: number; sizePx: number } | null {
    const v = this.views[i];
    if (!v || !v.model.object.visible || v.wreck) return null;
    const cam = this.cam.camera;
    this.tagPos.setFromMatrixPosition(v.model.object.matrixWorld);
    const depth = this.tagPos.distanceTo(cam.position);
    const pxPerMetre = height / (2 * depth * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2));
    this.tagPos.project(cam);
    return { x: ((this.tagPos.x + 1) / 2) * width, y: ((1 - this.tagPos.y) / 2) * height, sizePx: v.hull.length * pxPerMetre };
  }

  /** GPU resource counts, for the soak test. */
  gpuStats(): { geometries: number; textures: number; programs: number } {
    const info = this.renderer.info;
    return { geometries: info.memory.geometries, textures: info.memory.textures, programs: info.programs?.length ?? 0 };
  }
}
