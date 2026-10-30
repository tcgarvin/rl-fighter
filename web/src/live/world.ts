// The three.js side of the live page: the cinematic treatment, backdrop, effects and
// one hull model per ship, drawn by interpolating between sim ticks. Ships jump in as
// in the duel (a ~55 ms streak and a landing flash) or launch from a carrier's bay;
// freighters spool their jump drive and leave as a streak; damage shows as smoke,
// flame and arcing on the hull (no health bars). A destroyed ship either burns for up
// to two seconds and goes up in a major explosion or becomes a hulk: it coasts on,
// tumbling and smouldering, sunk below the battle plane so the living fly over it. Behind "show commands" the
// commanders' squad orders, carrier waypoints and the jump point are drawn faintly.

import * as THREE from "three";
import treatmentModule from "../render/treatments/cinematic.js";
import * as hullgeo from "../render/hullgeo.js";
import { createEffects, jumpOutOffset, JUMP_OUT_DURATION } from "../render/effects.js";
import { createEnvironment } from "../render/environment.js";
import { renderHullThumbnails } from "../render/thumbs.js";
import { HULLS } from "../render/hulls.js";
import { FitCamera, TYPICAL_ZOOM, emptyBounds, growBounds, type Bounds } from "./camera.ts";
import type { LiveMatch } from "./match.ts";
import { JUMP_DEPARTED, SIM_HZ, type HullInfo, type ShipState, type SimEvent } from "./sim.ts";

// Jump-in streak, as in the story and the duel.
const JUMP_DISTANCE = 900;
const JUMP_DURATION = 0.055;
// The burst at the kill itself; a major explosion, if one comes, is the big one.
const DEATH_RADIUS_SCALE = 1.8;
// Largest crash flash radius, metres (a 100 m/s head-on reaches it).
const COLLISION_FLASH_MAX = 4;
// Chance a destroyed ship blows up (else it's a hulk), and the latest it does, seconds.
const MAJOR_CHANCE = 0.45;
const MAJOR_DELAY_MAX = 2;
// A major explosion's radius against the hull's collision radius r: min(2.6 r, 1.6 r + 12),
// so a fighter's is 2.6 r and a carrier's (r ~ 50 m) doesn't swallow the screen.
const MAJOR_RADIUS_SCALE = 2.6;
const MAJOR_RADIUS_LARGE = 1.6;
const MAJOR_RADIUS_PAD = 12;
// Drift decays at this rate (1/s): a doomed wreck slows hard, a hulk coasts on.
const WRECK_DRAG = 0.7;
const HULK_DRAG = 0.12;
// A hulk sinks this far below the plane (metres, plus its own radius), easing at HULK_SINK_RATE.
const HULK_DEPTH = 6;
const HULK_SINK_RATE = 0.8;
// The hp fraction a wreck burns at (below the flame and arcing thresholds); a hulk's
// fire dies down to smoke over HULK_SMOULDER seconds.
const WRECK_HP = 0.12;
const HULK_HP = 0.35;
const HULK_SMOULDER = 6;
const BEAM_TTL = 0.06;
// Weapon ids are assets/weapons.yaml file order (SIM_SPEC §4.2); `Fire` carries one.
const WEAPON_NAMES = ["gauss", "laser", "flak", "torpedo"];
// The defenders' jump-out at the end of a convoy the escort won: after a beat, one
// ship every QUICK_JUMP_GAP seconds, freighters first.
const QUICK_JUMP_DELAY = 0.7;
const QUICK_JUMP_GAP = 0.11;
// The convoy's camera looks this far down the route ahead of the lead freighter, and
// takes in the jump point itself once the lead is this close to it (metres).
const CONVOY_LOOKAHEAD = 110;
const CONVOY_SHOW_JUMP = 230;
// Order markers: an attack or guard ring this much larger than the target's hull.
const MARK_PAD = 6;
const WAYPOINT_MARK = 14;
const WAYPOINT_MIN_DIST = 30;

/** The render-side hull spec (render/hulls.js, overlaid with the sim's YAML mounts). */
export interface HullSpec {
  role: string;
  model?: string;
  length: number;
  beam: number;
  radius: number;
  thrusters: Array<{ id: string; pos: [number, number]; dir: [number, number]; force?: number; size: number }>;
  turrets: Array<{ id: string; pos: [number, number]; height: number; rest: number; arc: number; slew: number; weapon: string }>;
  bays?: Array<{ id: string; pos: [number, number]; dir: [number, number] }>;
  collision?: Array<{ pos: [number, number]; r: number }>;
  shield?: { radius: number; hp?: number };
  speedCap?: number;
  hp?: number;
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

interface Charge {
  cancel(): void;
}

interface Departure {
  x: number;
  y: number;
  heading: number;
  team: number;
  size: number;
}

interface Effects {
  updateProjectiles(projectiles: LiveMatch["projectiles"], beams: Beam[], alpha: number): void;
  muzzle(e: { x: number; y: number; angle: number; team: number; weapon: string }): void;
  hit(e: { x: number; y: number; team: number; targetId: number }): void;
  shieldHit(e: { x: number; y: number; nx: number; ny: number; team: number; depleted: boolean; radius: number; object?: THREE.Object3D }): void;
  explosion(e: { x: number; y: number; radius: number; team: number; kind: string }): void;
  arrival(e: { x: number; y: number; heading: number; team: number; size: number; duration: number }): void;
  bayLaunch(e: { x: number; y: number; heading: number; team: number; size: number; speed: number }): void;
  jumpCharge(e: { object: THREE.Object3D; team: number; size: number; duration: number }): Charge;
  jumpOut(e: Departure): void;
  jumpOutQuick(e: Departure): void;
  drawOrders(orders: Order[]): void;
  attachDamage(model: HullModel): DamageFx;
  update(dt: number): void;
}

interface Environment {
  newMatch(seed: number): void;
  update(dt: number, view: { centerX: number; centerY: number; extent: number; projection?: THREE.Matrix4; layoutZoom?: number }): void;
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
  /** Tumble rate about the hull's long axis, rad/s. */
  roll: number;
  age: number;
  /** Seconds after death of the major explosion; Infinity for a hulk. */
  blowAt: number;
  gone: boolean;
}

/** A hash of (seed, ship, salt) to [0, 1): a match's wreck fates replay with its seed. */
function fate(seed: number, ship: number, salt: number): number {
  let h = Math.imul(seed ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(ship + 1, 0xc2b2ae35) ^ Math.imul(salt + 7, 0x27d4eb2f);
  h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d);
  h = Math.imul(h ^ (h >>> 12), 0x297a2d39);
  return ((h ^ (h >>> 15)) >>> 0) / 4294967296;
}

interface ShipView {
  model: HullModel;
  hull: HullSpec;
  damage: DamageFx;
  jumpStart: number;
  wreck: Wreck | null;
  /** Interpolation origin: the ship at the previous tick. */
  prev: { x: number; y: number; heading: number };
  /** Where it was drawn this frame (sim metres), for the order overlay. */
  drawn: { x: number; y: number; visible: boolean };
  charge: Charge | null;
  /** Jumped out (or quick-jumped at the end): when (world time) and from where. */
  departAt: number;
  depart: { x: number; y: number; heading: number };
}

const treatment = treatmentModule as unknown as Treatment;
const baseSpecs = HULLS as unknown as Record<string, HullSpec>;

/** The renderer's own spec for a catalogue hull, if it has a model for it. */
export function hullSpec(name: string): HullSpec | undefined {
  return baseSpecs[name];
}

/**
 * The renderer's spec with the sim's numbers laid over it: the YAML (bundle catalogue
 * `geometry`) is the source of truth for every mount and size the sim uses (thruster
 * and turret positions and order, bays, collision circles and so the hull's radius,
 * shield radius, hp, speed cap). The renderer keeps only what the YAML has no word for:
 * the model's look, drawn length and beam, plume sizes and turret heights.
 */
export function mergeSpec(base: HullSpec, info: HullInfo | undefined): HullSpec {
  const g = info?.geometry;
  if (!g || !info) return base;
  const thrusters = g.thrusters.map((t, i) => {
    const b = base.thrusters.find((x) => x.id === t.id) ?? base.thrusters[i];
    return { id: t.id, pos: t.pos, dir: t.dir, force: t.max_force, size: b?.size ?? Math.max(0.3, Math.sqrt(t.max_force) / 30) };
  });
  const turrets = g.turrets.map((t, i) => {
    const b = base.turrets.find((x) => x.id === t.id) ?? base.turrets[i];
    return { id: t.id, pos: t.pos, height: b?.height ?? 1, rest: t.rest_deg, arc: t.arc_deg, slew: t.slew_deg_s, weapon: t.weapon };
  });
  const bound = g.collision.length ? Math.max(...g.collision.map((c) => Math.hypot(c.pos[0], c.pos[1]) + c.r)) : base.radius;
  const shield = g.shield_radius > 0 ? { ...(base.shield ?? {}), radius: g.shield_radius, hp: info.shield } : undefined;
  return { ...base, hp: info.hp, speedCap: g.speed_cap, radius: bound, thrusters, turrets, bays: g.bays, collision: g.collision, shield };
}

function drift(w: Wreck, dt: number): void {
  w.age += dt;
  const drag = Math.exp(-(w.blowAt === Infinity ? HULK_DRAG : WRECK_DRAG) * dt);
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
  private specs: Record<string, HullSpec> = { ...baseSpecs };
  private views: ShipView[] = [];
  private beams: Beam[] = [];
  private match: LiveMatch | null = null;
  private ring: THREE.Line | null = null;
  private ringRadius = 0;
  private elapsed = 0;
  private size = { width: 0, height: 0 };
  private readonly tagPos = new THREE.Vector3();
  private quickJumps: Array<{ at: number; ship: number }> = [];
  private showOrders = false;
  private readonly orders: Order[] = [];
  private readonly orderPool: Order[] = [];

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

  /** Take the bundle's hull numbers (call before the first thumbnails or match). */
  setCatalogue(info: Record<string, HullInfo>): void {
    this.specs = Object.fromEntries(Object.entries(baseSpecs).map(([name, spec]) => [name, mergeSpec(spec, info[name])]));
  }

  /** The spec this world draws `name` with. */
  spec(name: string): HullSpec | undefined {
    return this.specs[name];
  }

  /** Card images for every hull the renderer and the catalogue both know: [team0, team1]. */
  thumbnails(names: string[]): Record<string, [string, string]> {
    const hulls = Object.fromEntries(names.filter((n) => this.specs[n]).map((n) => [n, this.specs[n]]));
    return renderHullThumbnails({ THREE, hullgeo, treatment, hulls }) as Record<string, [string, string]>;
  }

  /** Fit the viewport and the HUD's free band; the GPU buffers resize only on a real change. */
  resize(width: number, height: number, safeTopPx: number, safeBottomPx: number): void {
    if (width !== this.size.width || height !== this.size.height) {
      this.size = { width, height };
      this.renderer.setSize(width, height);
      treatment.onResize(width, height);
    }
    this.cam.setSafeBand(width, height, safeTopPx, safeBottomPx);
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

  /** Draw the commander layer (squad orders, waypoints, the jump point) or not. */
  setShowOrders(on: boolean): void {
    this.showOrders = on;
    if (!on) this.effects.drawOrders([]);
  }

  /** Drop the last match's ships and build models for `match`'s (not yet arrived). */
  beginMatch(match: LiveMatch): void {
    for (const v of this.views) {
      v.charge?.cancel();
      v.damage.dispose();
      v.model.dispose();
    }
    this.views = [];
    this.beams = [];
    this.quickJumps = [];
    this.effects.drawOrders([]);
    this.match = match;
    for (const [i, ship] of match.ships.entries()) {
      const name = match.hullNames[i]!;
      const hull = this.specs[name];
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
        drawn: { x: ship.x, y: ship.y, visible: false },
        charge: null,
        departAt: Infinity,
        depart: { x: 0, y: 0, heading: 0 },
      });
    }
    // The convoy's route runs up a phone's long axis; everything else keeps the teams'
    // approach axis (sim x) there.
    const c = match.convoy;
    if (c) this.cam.setAxis(c.jumpX - c.startX, c.jumpY - c.startY);
    else this.cam.setAxis(1, 0);
    // The fixed camera holds the whole arena (and the convoy's road) at zoom 1.
    const stage = emptyBounds();
    const r = match.arenaRadius;
    for (const [x, y] of [[-r, -r], [-r, r], [r, -r], [r, r]] as const) growBounds(stage, x, y);
    if (c) {
      this.cam.grow(stage, c.startX, c.startY);
      this.cam.grow(stage, c.jumpX, c.jumpY);
    }
    this.cam.setStage(stage);
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
   * still starts wrecks and departures, so a fast-forwarded frame shows the right ships.
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
        view.charge?.cancel();
        view.charge = null;
        const major = fate(m.seed, e.a, 0) < MAJOR_CHANCE;
        const spin = fate(m.seed, e.a, 1) - 0.5;
        view.wreck = {
          x: e.x,
          y: e.y,
          vx: ship.vx,
          vy: ship.vy,
          heading: ship.heading,
          omega: ship.omega * 0.5 + spin * 0.8,
          roll: 0.15 + 0.3 * fate(m.seed, e.a, 2),
          age: 0,
          blowAt: major ? MAJOR_DELAY_MAX * fate(m.seed, e.a, 3) : Infinity,
          gone: false,
        };
        if (!quiet) fx.explosion({ x: e.x, y: e.y, radius: view.hull.radius * DEATH_RADIUS_SCALE, team: ship.team, kind: "death" });
        continue;
      }
      if (e.kind === "launch" && ship && view) {
        // Out of the bay at its launch velocity: interpolate from a tick back along it,
        // not from the hangar (the carrier's centre).
        view.prev.x = ship.x - ship.vx / SIM_HZ;
        view.prev.y = ship.y - ship.vy / SIM_HZ;
        view.prev.heading = ship.heading;
        const speed = Math.hypot(ship.vx, ship.vy);
        if (!quiet) fx.bayLaunch({ x: e.x, y: e.y, heading: Math.atan2(ship.vy, ship.vx), team: ship.team, size: view.hull.length, speed });
        continue;
      }
      if (e.kind === "jumpOut" && ship && view) {
        view.charge = null;
        view.depart = { x: e.x, y: e.y, heading: e.extra };
        view.departAt = quiet ? -Infinity : this.elapsed;
        if (!quiet) fx.jumpOut({ x: e.x, y: e.y, heading: e.extra, team: ship.team, size: view.hull.length });
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
          fx.shieldHit({ x: e.x, y: e.y, nx: e.f5, ny: e.f6, team: shooter?.team ?? 0, depleted: e.extra > 0.5, radius: view?.hull.shield?.radius ?? 8, object: view?.model.object });
          break;
        case "burst":
          fx.explosion({ x: e.x, y: e.y, radius: e.extra, team: e.a, kind: "flak" });
          break;
        case "arrival":
          if (!view || !ship) break;
          view.jumpStart = this.elapsed;
          fx.arrival({ x: e.x, y: e.y, heading: e.extra, team: ship.team, size: view.hull.length, duration: JUMP_DURATION });
          break;
        case "jumpCharge":
          if (!view || !ship) break;
          view.charge?.cancel();
          view.charge = fx.jumpCharge({ object: view.model.object, team: ship.team, size: view.hull.length, duration: Math.max(0.2, (e.extra - m.tick) / SIM_HZ) });
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

  /**
   * The end of a convoy the escort saw through: every `team` ship still on the field
   * jumps out too, freighters first, staggered (renderer only; the sim has stopped).
   */
  departAll(team: number): void {
    const m = this.match;
    if (!m) return;
    const ships = m.ships
      .map((s, i) => ({ s, i }))
      .filter(({ s, i }) => s.team === team && m.active(s) && !this.views[i]!.wreck)
      .sort((a, b) => Number(b.s.role === "transport") - Number(a.s.role === "transport") || a.i - b.i);
    this.quickJumps = ships.map(({ i }, k) => ({ at: this.elapsed + QUICK_JUMP_DELAY + k * QUICK_JUMP_GAP, ship: i }));
  }

  /** Age the wrecks without drawing (a fast-forward): due explosions pass silently. */
  advanceWrecks(dt: number): void {
    for (const v of this.views) {
      const w = v.wreck;
      if (!w || w.gone) continue;
      drift(w, dt);
      if (w.age >= w.blowAt) w.gone = true;
    }
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
      this.runQuickJumps(m);
      for (const [i, v] of this.views.entries()) this.drawShip(m, i, v, dt, alpha, bounds, frameAll);
      this.frameConvoy(m, bounds);
      for (const b of this.beams) b.ttl -= dt;
      // Projectiles are at the current tick and ships between the previous and current
      // one, so back the shots up by a tick to keep them on the muzzles.
      this.effects.updateProjectiles(m.projectiles, this.beams, alpha - 1);
      // The jump point is part of the convoy mission, always shown; the rest is the commands layer.
      if (this.showOrders || m.convoy) this.updateOrders(m, this.showOrders);
    }
    this.cam.update(bounds, dt);
    this.environment.update(dt, { centerX: this.cam.x, centerY: this.cam.y, extent: this.cam.extent, projection: this.cam.baseProjection, layoutZoom: TYPICAL_ZOOM });
    this.effects.update(dt);
    treatment.render(this.renderer, this.scene, this.cam.camera, dt);
  }

  private runQuickJumps(m: LiveMatch): void {
    while (this.quickJumps.length && this.quickJumps[0]!.at <= this.elapsed) {
      const { ship } = this.quickJumps.shift()!;
      const v = this.views[ship]!;
      const s = m.ships[ship]!;
      if (v.wreck || v.departAt !== Infinity) continue;
      v.charge?.cancel();
      v.charge = null;
      v.depart = { x: v.drawn.x, y: v.drawn.y, heading: s.heading };
      v.departAt = this.elapsed;
      this.effects.jumpOutQuick({ x: v.drawn.x, y: v.drawn.y, heading: s.heading, team: s.team, size: v.hull.length });
    }
  }

  /** Frame the convoy's road ahead: a point down the route, then the jump point itself. */
  private frameConvoy(m: LiveMatch, bounds: Bounds): void {
    const c = m.convoy;
    if (!c) return;
    const dx = c.jumpX - c.startX;
    const dy = c.jumpY - c.startY;
    const len = Math.hypot(dx, dy) || 1;
    let lead: ShipState | null = null;
    let best = -Infinity;
    for (const s of m.ships) {
      if (s.role !== "transport" || !m.active(s)) continue;
      const along = ((s.x - c.startX) * dx + (s.y - c.startY) * dy) / len;
      if (along > best) (best = along), (lead = s);
    }
    if (!lead) return;
    const left = Math.hypot(c.jumpX - lead.x, c.jumpY - lead.y);
    const ahead = Math.min(left, CONVOY_LOOKAHEAD);
    this.cam.grow(bounds, lead.x + (dx / len) * ahead, lead.y + (dy / len) * ahead);
    if (left < CONVOY_SHOW_JUMP) this.cam.grow(bounds, c.jumpX, c.jumpY);
  }

  private nextOrder(): Order {
    const o = this.orderPool[this.orders.length] ?? { kind: "hold", team: 0, x2: 0, y2: 0 };
    this.orderPool[this.orders.length] = o;
    this.orders.push(o);
    delete o.x1;
    delete o.y1;
    delete o.progress;
    o.radius = 0;
    return o;
  }

  /** Rebuild the order overlay from the sim's squads, waypoints and convoy, at the drawn positions. */
  private updateOrders(m: LiveMatch, commands: boolean): void {
    this.orders.length = 0;
    for (const sq of commands ? m.squads : []) {
      if (sq.order === "none" || sq.members === 0) continue;
      let sx = 0;
      let sy = 0;
      let n = 0;
      for (let i = 0; i < this.views.length; i++) {
        if (!(sq.mask & (1 << i))) continue;
        const d = this.views[i]!.drawn;
        if (!d.visible) continue;
        sx += d.x;
        sy += d.y;
        n += 1;
      }
      const target = sq.target >= 0 ? this.views[sq.target] : undefined;
      const tx = target?.drawn.visible ? target.drawn.x : sq.x;
      const ty = target?.drawn.visible ? target.drawn.y : sq.y;
      const o = this.nextOrder();
      o.kind = sq.order;
      o.team = sq.team;
      o.x2 = tx;
      o.y2 = ty;
      o.radius = sq.order === "hold" ? sq.radius : (target?.hull.radius ?? 8) + MARK_PAD;
      if (n > 0) {
        o.x1 = sx / n;
        o.y1 = sy / n;
      }
    }
    // Capital ships' waypoints: where the carrier is headed (the convoy's is the jump point).
    for (const [i, s] of m.ships.entries()) {
      if (!commands || s.role !== "carrier" || !s.hasWaypoint || !m.active(s)) continue;
      const d = this.views[i]!.drawn;
      if (Math.hypot(s.waypointX - d.x, s.waypointY - d.y) < WAYPOINT_MIN_DIST) continue;
      const o = this.nextOrder();
      Object.assign(o, { kind: "hold", team: s.team, x2: s.waypointX, y2: s.waypointY, radius: WAYPOINT_MARK, x1: d.x, y1: d.y });
    }
    const c = m.convoy;
    if (c) {
      let sx = 0;
      let sy = 0;
      let n = 0;
      for (const [i, s] of m.ships.entries()) {
        if (s.role !== "transport" || !m.active(s)) continue;
        sx += this.views[i]!.drawn.x;
        sy += this.views[i]!.drawn.y;
        n += 1;
      }
      const o = this.nextOrder();
      Object.assign(o, { kind: "jump", team: 0, x2: c.jumpX, y2: c.jumpY, radius: c.jumpRadius, progress: c.total ? c.escaped / c.total : 0 });
      if (n > 0 && commands) {
        o.x1 = sx / n;
        o.y1 = sy / n;
      }
    }
    this.effects.drawOrders(this.orders);
  }

  private drawShip(m: LiveMatch, i: number, v: ShipView, dt: number, alpha: number, bounds: Bounds, frameAll: boolean): void {
    const ship = m.ships[i]!;
    const obj = v.model.object;
    v.drawn.visible = false;
    if (v.wreck) {
      this.drawWreck(v, dt, frameAll ? bounds : null, ship.team);
      return;
    }
    if (v.departAt !== Infinity) {
      this.drawDeparture(v, dt);
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
    const visible = m.active(ship);
    obj.visible = visible;
    obj.position.set(x, 0, -y);
    obj.rotation.set(0, heading, 0);
    obj.updateMatrixWorld();
    v.drawn.x = x;
    v.drawn.y = y;
    v.drawn.visible = visible;
    v.model.setThrottles(ship.throttles, dt);
    v.model.turrets.forEach((pivot, k) => (pivot.rotation.y = ship.turretAngles[k] ?? 0));
    v.damage.update(Math.max(0, ship.hp) / (m.maxHp[i] ?? 1), visible, dt);
    // Ships yet to jump in count too, so the empty field is framed where they'll
    // appear; ships in a hangar or gone through the jump point do not.
    if (ship.alive && !ship.docked && ship.jump !== JUMP_DEPARTED) this.cam.grow(bounds, ship.x, ship.y);
  }

  /** A hull leaving through its jump: pulled forward along its heading, then gone. */
  private drawDeparture(v: ShipView, dt: number): void {
    const obj = v.model.object;
    const age = this.elapsed - v.departAt;
    if (age > JUMP_OUT_DURATION) {
      obj.visible = false;
      v.damage.update(1, false, dt);
      return;
    }
    const ahead = jumpOutOffset(age);
    const d = v.depart;
    obj.visible = true;
    obj.position.set(d.x + Math.cos(d.heading) * ahead, 0, -(d.y + Math.sin(d.heading) * ahead));
    obj.rotation.set(0, d.heading, 0);
    obj.updateMatrixWorld();
  }

  private drawWreck(v: ShipView, dt: number, bounds: Bounds | null, team: number): void {
    const w = v.wreck!;
    const obj = v.model.object;
    if (w.gone) {
      obj.visible = false;
      v.damage.update(1, false, dt);
      return;
    }
    drift(w, dt);
    if (w.age >= w.blowAt) {
      w.gone = true;
      obj.visible = false;
      v.damage.update(1, false, dt);
      this.effects.explosion({ x: w.x, y: w.y, radius: Math.min(v.hull.radius * MAJOR_RADIUS_SCALE, v.hull.radius * MAJOR_RADIUS_LARGE + MAJOR_RADIUS_PAD), team, kind: "major" });
      return;
    }
    const hulk = w.blowAt === Infinity;
    // A hulk eases down below the plane; a doomed wreck stays on it until it goes.
    const depth = hulk ? (HULK_DEPTH + v.hull.radius) * (1 - Math.exp(-HULK_SINK_RATE * w.age)) : 0;
    obj.visible = true;
    obj.position.set(w.x, -depth, -w.y);
    obj.rotation.set(w.age * w.roll, w.heading, 0);
    obj.updateMatrixWorld();
    v.model.setThrottles([], dt);
    const hp = hulk ? WRECK_HP + (HULK_HP - WRECK_HP) * Math.min(1, w.age / HULK_SMOULDER) : WRECK_HP;
    v.damage.update(hp, true, dt);
    // Only a wreck still to blow is worth holding in the shot.
    if (bounds && !hulk) this.cam.grow(bounds, w.x, w.y);
  }

  /** Screen position and drawn length (CSS px) of ship `i`, or null when it isn't on show. */
  shipOnScreen(i: number, width: number, height: number): { x: number; y: number; sizePx: number } | null {
    const v = this.views[i];
    if (!v || !v.model.object.visible || v.wreck || v.departAt !== Infinity) return null;
    return this.project(v.model.object.matrixWorld, v.hull.length, width, height);
  }

  /** Screen position (CSS px) of a sim point, and how many px a metre is there. */
  pointOnScreen(x: number, y: number, width: number, height: number): { x: number; y: number; pxPerMetre: number } {
    this.tagPos.set(x, 0, -y);
    const cam = this.cam.camera;
    const depth = this.tagPos.distanceTo(cam.position);
    // The projection's y scale carries the digital zoom as well as the field of view.
    const pxPerMetre = (height * cam.projectionMatrix.elements[5]!) / (2 * depth);
    this.tagPos.project(cam);
    return { x: ((this.tagPos.x + 1) / 2) * width, y: ((1 - this.tagPos.y) / 2) * height, pxPerMetre };
  }

  private project(matrix: THREE.Matrix4, length: number, width: number, height: number): { x: number; y: number; sizePx: number } {
    const cam = this.cam.camera;
    this.tagPos.setFromMatrixPosition(matrix);
    const depth = this.tagPos.distanceTo(cam.position);
    // The projection's y scale carries the digital zoom as well as the field of view.
    const pxPerMetre = (height * cam.projectionMatrix.elements[5]!) / (2 * depth);
    this.tagPos.project(cam);
    return { x: ((this.tagPos.x + 1) / 2) * width, y: ((1 - this.tagPos.y) / 2) * height, sizePx: length * pxPerMetre };
  }

  /** GPU resource counts, for the soak test. */
  gpuStats(): { geometries: number; textures: number; programs: number } {
    const info = this.renderer.info;
    return { geometries: info.memory.geometries, textures: info.memory.textures, programs: info.programs?.length ?? 0 };
  }
}
