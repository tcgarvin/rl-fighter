// Camera v1 (DESIGN §9): a fixed oblique view that frames every live ship, with
// smoothed zoom and pan, kept inside the band the HUD leaves free. Ported from the
// duel page (and the story demo before it).

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

export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export function emptyBounds(): Bounds {
  return { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
}

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

  constructor(aspect: number) {
    this.camera = new THREE.PerspectiveCamera(FOV, aspect, 1, 60000);
  }

  /** Jump straight to the next framing instead of easing (a new match). */
  snap(): void {
    this.initialized = false;
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

  // Portrait screens turn the camera 90° so the teams' approach axis (sim x) runs up
  // the screen instead of across its narrow width.
  private place(x: number, y: number, dist: number): void {
    const back = Math.cos(PITCH) * dist;
    const portrait = this.camera.aspect < 1;
    if (portrait) this.camera.position.set(x - back, Math.sin(PITCH) * dist, -y);
    else this.camera.position.set(x, Math.sin(PITCH) * dist, -y + back);
    this.camera.lookAt(x, 0, -y);
    this.camera.updateMatrixWorld();
  }

  private fitDistance(cx: number, cy: number, box: [number, number, number, number]): number {
    const [minX, maxX, minY, maxY] = box;
    const probe = Math.max(maxX - minX, maxY - minY, 1) * 2;
    this.place(cx, cy, probe);
    const bandCenter = (this.band.top + this.band.bottom) / 2;
    const bandHalf = Math.max(0.2, (this.band.top - this.band.bottom) / 2);
    let extent = 0;
    for (const [x, y] of [[minX, minY], [minX, maxY], [maxX, minY], [maxX, maxY]] as const) {
      this.corner.set(x, 0, -y).project(this.camera);
      extent = Math.max(extent, Math.abs(this.corner.x) / SAFE_NDC_X, Math.abs(this.corner.y - bandCenter) / bandHalf);
    }
    return probe * extent;
  }

  /** Ease toward framing `b` (sim metres); an empty box frames the arena centre. */
  update(b: Bounds, dt: number): void {
    if (!Number.isFinite(b.minX)) b = { minX: -60, maxX: 60, minY: -60, maxY: 60 };
    const cx = (b.minX + b.maxX) / 2;
    const cy = (b.minY + b.maxY) / 2;
    const half = MIN_FRAME_SPAN / 2;
    const box: [number, number, number, number] = [
      Math.min(b.minX - FRAME_MARGIN, cx - half),
      Math.max(b.maxX + FRAME_MARGIN, cx + half),
      Math.min(b.minY - FRAME_MARGIN, cy - half),
      Math.max(b.maxY + FRAME_MARGIN, cy + half),
    ];
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
