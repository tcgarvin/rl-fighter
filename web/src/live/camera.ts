// Camera v1 (DESIGN §9): a fixed oblique view that frames every live ship, with
// smoothed zoom and pan, kept inside the band the HUD leaves free. Ported from the
// duel page (and the story demo before it).
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
// Fraction of the half-width a ship may use before the camera pulls back.
const SAFE_NDC_X = 0.88;
// 1/s; about two thirds of the way to the target in 0.7 s.
const EASE_RATE = 1.5;

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
  /** Smoothed centre (sim metres) and the half-span of the framed box. */
  x = 0;
  y = 0;
  extent = 300;
  private dist = 800;
  private initialized = false;
  /** NDC rows the HUD leaves clear (top > bottom). */
  private band = { top: 0.8, bottom: -0.8 };
  private readonly corner = new THREE.Vector3();
  /** The main axis, a unit vector in sim coordinates. */
  private ax = 1;
  private ay = 0;

  constructor(aspect: number) {
    this.camera = new THREE.PerspectiveCamera(FOV, aspect, 1, 60000);
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
  }

  /** Grow `b` (axis frame) by the sim point (x, y). */
  grow(b: Bounds, x: number, y: number): void {
    growBounds(b, x * this.ax + y * this.ay, -x * this.ay + y * this.ax);
  }

  /** Axis-frame (f, g) back to sim metres. */
  private toSim(f: number, g: number): [number, number] {
    return [f * this.ax - g * this.ay, f * this.ay + g * this.ax];
  }

  /**
   * Keep the action between `topPx` (below the top HUD) and `bottomPx` (above the
   * bottom HUD): shift the projection so the band's centre is the view's centre.
   */
  setSafeBand(width: number, height: number, topPx: number, bottomPx: number): void {
    this.band.top = 1 - (2 * topPx) / height;
    this.band.bottom = 1 - (2 * bottomPx) / height;
    const bandCenterPx = (topPx + bottomPx) / 2;
    this.camera.aspect = width / height;
    this.camera.setViewOffset(width, height, 0, height / 2 - bandCenterPx, width, height);
    this.camera.updateProjectionMatrix();
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
  }

  private fitDistance(cx: number, cy: number, box: [number, number, number, number]): number {
    const [minF, maxF, minG, maxG] = box;
    const probe = Math.max(maxF - minF, maxG - minG, 1) * 2;
    this.place(cx, cy, probe);
    const bandCenter = (this.band.top + this.band.bottom) / 2;
    const bandHalf = Math.max(0.2, (this.band.top - this.band.bottom) / 2);
    let extent = 0;
    for (const [f, g] of [[minF, minG], [minF, maxG], [maxF, minG], [maxF, maxG]] as const) {
      const [x, y] = this.toSim(f, g);
      this.corner.set(x, 0, -y).project(this.camera);
      extent = Math.max(extent, Math.abs(this.corner.x) / SAFE_NDC_X, Math.abs(this.corner.y - bandCenter) / bandHalf);
    }
    return probe * extent;
  }

  /** Ease toward framing `b` (axis frame, sim metres); an empty box frames the arena centre. */
  update(b: Bounds, dt: number): void {
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
    const [cx, cy] = this.toSim(cf, cg);
    const needed = this.fitDistance(cx, cy, box);
    const k = this.initialized ? 1 - Math.exp(-dt * EASE_RATE) : 1;
    this.initialized = true;
    this.x += (cx - this.x) * k;
    this.y += (cy - this.y) * k;
    this.dist += (needed - this.dist) * k;
    this.extent = Math.max(box[1] - box[0], box[3] - box[2]) / 2;
    this.place(this.x, this.y, this.dist);
  }
}
