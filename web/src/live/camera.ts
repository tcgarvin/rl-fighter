// Camera v2 (DESIGN §9): a fixed oblique view of the whole stage (the arena), placed
// once per match, with a "digital" zoom and pan on top: the framing crops and scales
// the rendered image (a scale and shift applied after the projection) instead of
// moving the camera, so perspective, parallax and the backdrop's relation to the ships
// never change; zooming in on a ship by a planet enlarges the planet with it. The crop
// eases to frame every live ship inside the band the HUD leaves free.
//
// The view is set by one world axis, the match's main line (the teams' approach, sim
// +x; a convoy's route): portrait screens look along it, so it runs up the screen's
// long side, and landscape screens look across it, so it runs left to right. Framing
// boxes are kept in that axis's frame (`grow`), so a route at any angle fits tightly.

import * as THREE from "three";

const PITCH = (58 * Math.PI) / 180;
export const FOV = 32;
// Metres: a merge at point-blank range isn't framed absurdly close.
const MIN_FRAME_SPAN = 150;
const FRAME_MARGIN = 28;
// Fraction of the half-width a ship may use before the view pulls back.
const SAFE_NDC_X = 0.88;
// 1/s; about two thirds of the way to the target in 0.7 s.
const EASE_RATE = 1.5;
// Digital zoom limits (1 = the whole stage in view).
const MIN_ZOOM = 0.6;
const MAX_ZOOM = 60;
/** About how far in the framing usually sits during a fight; the backdrop is composed for it. */
export const TYPICAL_ZOOM = 2.5;

/** A box in the camera axis's frame: f along the axis, g across it (CCW). */
export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export function emptyBounds(): Bounds {
  return { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
}

/** Grow a box by a point already in its frame (the axis is sim +x by default). */
export function growBounds(b: Bounds, x: number, y: number): void {
  b.minX = Math.min(b.minX, x);
  b.maxX = Math.max(b.maxX, x);
  b.minY = Math.min(b.minY, y);
  b.maxY = Math.max(b.maxY, y);
}

export class FitCamera {
  readonly camera: THREE.PerspectiveCamera;
  /** The fixed camera's own projection, before the digital zoom and pan. */
  readonly baseProjection = new THREE.Matrix4();
  /** Smoothed centre (sim metres) and the half-span of the framed box. */
  x = 0;
  y = 0;
  extent = 300;
  /** Digital crop: the base view's NDC point at the band's centre, and the scale. */
  private u = 0;
  private v = 0;
  private zoom = 1;
  private initialized = false;
  private placed = false;
  /** NDC rows the HUD leaves clear (top > bottom). */
  private band = { top: 0.8, bottom: -0.8 };
  /** The stage the fixed camera takes in whole: axis-frame box, sim metres. */
  private stage: Bounds = { minX: -400, maxX: 400, minY: -400, maxY: 400 };
  private readonly corner = new THREE.Vector3();
  private readonly viewProjection = new THREE.Matrix4();
  private readonly crop = new THREE.Matrix4();
  /** The main axis, a unit vector in sim coordinates. */
  private ax = 1;
  private ay = 0;

  constructor(aspect: number) {
    this.camera = new THREE.PerspectiveCamera(FOV, aspect, 1, 60000);
  }

  /** The digital zoom now (1 = the whole stage). */
  get zoomLevel(): number {
    return this.zoom;
  }

  /** Jump straight to the next framing instead of easing (a new match). */
  snap(): void {
    this.initialized = false;
  }

  /** The match's main line (any length); see the header. */
  setAxis(x: number, y: number): void {
    const len = Math.hypot(x, y);
    if (!(len > 1e-6)) return;
    this.ax = x / len;
    this.ay = y / len;
    this.placed = false;
  }

  /** Everything the fixed camera must hold at zoom 1 (axis frame); re-places it. */
  setStage(b: Bounds): void {
    this.stage = { ...b };
    this.placed = false;
  }

  /** Grow `b` (axis frame) by the sim point (x, y). */
  grow(b: Bounds, x: number, y: number): void {
    growBounds(b, x * this.ax + y * this.ay, -x * this.ay + y * this.ax);
  }

  /** Axis-frame (f, g) back to sim metres. */
  private toSim(f: number, g: number): [number, number] {
    return [f * this.ax - g * this.ay, f * this.ay + g * this.ax];
  }

  /** Keep the action between `topPx` (below the top HUD) and `bottomPx` (above the bottom HUD). */
  setSafeBand(width: number, height: number, topPx: number, bottomPx: number): void {
    this.band.top = 1 - (2 * topPx) / height;
    this.band.bottom = 1 - (2 * bottomPx) / height;
    const aspect = width / height;
    if (aspect !== this.camera.aspect) {
      this.camera.aspect = aspect;
      this.placed = false;
    }
  }

  // Portrait looks along the axis; landscape looks along its left-hand normal, so
  // the axis runs left to right (with the default axis: as the duel page did).
  private place(x: number, y: number, dist: number): void {
    const back = Math.cos(PITCH) * dist;
    const portrait = this.camera.aspect < 1;
    const ux = portrait ? this.ax : -this.ay;
    const uy = portrait ? this.ay : this.ax;
    this.camera.position.set(x - ux * back, Math.sin(PITCH) * dist, -(y - uy * back));
    this.camera.lookAt(x, 0, -y);
    this.camera.updateMatrixWorld();
    this.camera.updateProjectionMatrix();
    this.baseProjection.copy(this.camera.projectionMatrix);
    this.viewProjection.multiplyMatrices(this.baseProjection, this.camera.matrixWorldInverse);
  }

  /** The axis-frame box's NDC extent in the fixed camera: [minX, maxX, minY, maxY]. */
  private projectBox(box: [number, number, number, number]): [number, number, number, number] {
    const [minF, maxF, minG, maxG] = box;
    const out: [number, number, number, number] = [Infinity, -Infinity, Infinity, -Infinity];
    for (const [f, g] of [[minF, minG], [minF, maxG], [maxF, minG], [maxF, maxG]] as const) {
      const [x, y] = this.toSim(f, g);
      this.corner.set(x, 0, -y).applyMatrix4(this.viewProjection);
      out[0] = Math.min(out[0], this.corner.x);
      out[1] = Math.max(out[1], this.corner.x);
      out[2] = Math.min(out[2], this.corner.y);
      out[3] = Math.max(out[3], this.corner.y);
    }
    return out;
  }

  /** Put the fixed camera where the whole stage fills the screen at zoom 1. */
  private placeForStage(): void {
    const s = this.stage;
    const [cx, cy] = this.toSim((s.minX + s.maxX) / 2, (s.minY + s.maxY) / 2);
    const probe = Math.max(s.maxX - s.minX, s.maxY - s.minY, 1) * 2;
    this.place(cx, cy, probe);
    const [x0, x1, y0, y1] = this.projectBox([s.minX, s.maxX, s.minY, s.maxY]);
    const extent = Math.max(Math.abs(x0), Math.abs(x1), Math.abs(y0), Math.abs(y1));
    this.place(cx, cy, probe * extent);
    this.placed = true;
  }

  /** Ease the crop toward framing `b` (axis frame, sim metres); an empty box frames the stage centre. */
  update(b: Bounds, dt: number): void {
    if (!this.placed) this.placeForStage();
    if (!Number.isFinite(b.minX)) b = { minX: -60, maxX: 60, minY: -60, maxY: 60 };
    const cf = (b.minX + b.maxX) / 2;
    const cg = (b.minY + b.maxY) / 2;
    const half = MIN_FRAME_SPAN / 2;
    const box: [number, number, number, number] = [
      Math.min(b.minX - FRAME_MARGIN, cf - half),
      Math.max(b.maxX + FRAME_MARGIN, cf + half),
      Math.min(b.minY - FRAME_MARGIN, cg - half),
      Math.max(b.maxY + FRAME_MARGIN, cg + half),
    ];
    const [x0, x1, y0, y1] = this.projectBox(box);
    const bandHalf = Math.max(0.2, (this.band.top - this.band.bottom) / 2);
    const zoom = THREE.MathUtils.clamp(
      Math.min(SAFE_NDC_X / Math.max(1e-4, (x1 - x0) / 2), bandHalf / Math.max(1e-4, (y1 - y0) / 2)),
      MIN_ZOOM,
      MAX_ZOOM,
    );
    const [cx, cy] = this.toSim(cf, cg);
    const k = this.initialized ? 1 - Math.exp(-dt * EASE_RATE) : 1;
    this.initialized = true;
    this.u += ((x0 + x1) / 2 - this.u) * k;
    this.v += ((y0 + y1) / 2 - this.v) * k;
    this.zoom *= Math.exp((Math.log(zoom) - Math.log(this.zoom)) * k);
    this.x += (cx - this.x) * k;
    this.y += (cy - this.y) * k;
    this.extent = Math.max(box[1] - box[0], box[3] - box[2]) / 2;
    this.applyCrop();
  }

  /** Scale about (u, v) and move it to the band's centre, in clip space (so times w). */
  private applyCrop(): void {
    const z = this.zoom;
    const bandCenter = (this.band.top + this.band.bottom) / 2;
    this.crop.set(
      z, 0, 0, -z * this.u,
      0, z, 0, bandCenter - z * this.v,
      0, 0, 1, 0,
      0, 0, 0, 1,
    );
    this.camera.projectionMatrix.multiplyMatrices(this.crop, this.baseProjection);
    this.camera.projectionMatrixInverse.copy(this.camera.projectionMatrix).invert();
  }
}
