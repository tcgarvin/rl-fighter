// Slowly turning hull models for the catalogue cards. One offscreen WebGL renderer
// and one scene serve every card: each visible card in turn shows only its model,
// is drawn through the cinematic treatment, and is copied into the card's 2D canvas.
// Three cards cost one GL context, which is what keeps this smooth on a phone.
import * as THREE from "three";
import { buildHull } from "../render/hullgeo.js";
import { HULLS } from "../render/hulls.js";
import cinematic from "../render/treatments/cinematic.js";
import type { Hull } from "./types";

const FRAME_MS = 1000 / 30;
const TURN_RAD_S = 0.32;
const PITCH = (30 * Math.PI) / 180;
const MAX_DPR = 2;

interface Model {
  object: THREE.Object3D;
  turrets: THREE.Object3D[];
  setThrottles(levels: number[], dt: number): void;
  dispose(): void;
}

interface View {
  hull: Hull;
  visual: (typeof HULLS)[keyof typeof HULLS];
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  model: Model;
  visible: boolean;
  phase: number;
}

type Treatment = {
  init(args: { scene: THREE.Scene; renderer: THREE.WebGLRenderer }): void;
  materials(team: number): Record<string, THREE.Material>;
  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, dt: number): void;
  onResize(): void;
};

const treatment = cinematic as unknown as Treatment;

export class TurntableError extends Error {}

/** Shared renderer for every card's turntable. */
export class Turntable {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(26, 16 / 10, 0.1, 2000);
  private readonly views: View[] = [];
  private readonly observer: IntersectionObserver;
  private readonly still = window.matchMedia("(prefers-reduced-motion: reduce)");
  private team = 0;
  private size = { w: 0, h: 0 };
  private last = 0;
  private time = 0;
  private dirty = true;
  private running = false;

  /** @throws TurntableError when the browser cannot create a WebGL context. */
  constructor() {
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: "low-power" });
    } catch (error) {
      throw new TurntableError(`WebGL is not available: ${(error as Error).message}`);
    }
    this.renderer.setPixelRatio(1);
    this.renderer.setClearColor(0x0a0f17, 1);
    treatment.init({ scene: this.scene, renderer: this.renderer });
    this.observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        const view = this.views.find((v) => v.canvas === entry.target);
        if (view) view.visible = entry.isIntersecting;
      }
      this.dirty = true;
    });
    new ResizeObserver(() => {
      this.dirty = true;
    }).observe(document.documentElement);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) this.dirty = true;
    });
    this.still.addEventListener("change", () => {
      this.dirty = true;
    });
  }

  /** Show `hull`'s model in `canvas`. Hulls without a visual model are an error. */
  add(hull: Hull, canvas: HTMLCanvasElement): void {
    const visual = HULLS[hull.name as keyof typeof HULLS];
    if (!visual) throw new TurntableError(`no 3D model for hull "${hull.name}"`);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new TurntableError("2D canvas is not available");
    const model = this.build(visual);
    // Stagger the cards so they don't all show the same angle at once.
    this.views.push({ hull, visual, canvas, ctx, model, visible: false, phase: this.views.length * 2.1 + 0.6 });
    this.observer.observe(canvas);
    this.dirty = true;
  }

  /** Repaint every model in team 0 (blue) or team 1 (orange). */
  setTeam(team: number): void {
    if (team === this.team) return;
    this.team = team;
    for (const view of this.views) {
      view.model.dispose();
      view.model = this.build(view.visual);
    }
    this.dirty = true;
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    const tick = (now: number) => {
      requestAnimationFrame(tick);
      if (document.hidden) return;
      const moving = !this.still.matches;
      if (!moving && !this.dirty) return;
      if (moving && now - this.last < FRAME_MS && !this.dirty) return;
      const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0;
      this.last = now;
      if (moving) this.time += dt;
      this.drawAll(dt);
      this.dirty = false;
    };
    requestAnimationFrame(tick);
  }

  private build(visual: View["visual"]): Model {
    const model = buildHull(visual, this.team, treatment.materials(this.team)) as Model;
    model.object.visible = false;
    this.scene.add(model.object);
    return model;
  }

  private resize(w: number, h: number): void {
    if (w === this.size.w && h === this.size.h) return;
    this.size = { w, h };
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    treatment.onResize();
  }

  private drawAll(dt: number): void {
    const dpr = Math.min(MAX_DPR, window.devicePixelRatio || 1);
    for (const view of this.views) {
      if (!view.visible) continue;
      const w = Math.max(2, Math.round(view.canvas.clientWidth * dpr));
      const h = Math.max(2, Math.round(view.canvas.clientHeight * dpr));
      if (view.canvas.width !== w || view.canvas.height !== h) {
        view.canvas.width = w;
        view.canvas.height = h;
      }
      this.resize(w, h);
      for (const other of this.views) other.model.object.visible = other === view;
      this.pose(view, dt);
      treatment.render(this.renderer, this.scene, this.camera, dt);
      view.ctx.drawImage(this.renderer.domElement, 0, 0, w, h);
    }
  }

  private pose(view: View, dt: number): void {
    const { model, visual, hull } = view;
    const t = this.time + view.phase;
    model.object.rotation.y = t * TURN_RAD_S;
    // Mains at a steady cruise so the exhaust reads; side thrusters stay off.
    model.setThrottles(
      visual.thrusters.map((th: { dir: number[] }) => ((th.dir[0] ?? 0) > 0.5 ? 0.38 : 0)),
      dt || 1,
    );
    // Slewing turrets sweep within their arcs, each on its own rhythm.
    model.turrets.forEach((pivot, i) => {
      const turret = hull.turrets[i];
      if (!turret) return;
      const sweep = turret.arc_deg > 0 ? Math.sin(t * 0.7 + i * 1.9) * turret.arc_deg * 0.3 : 0;
      pivot.rotation.y = ((turret.rest_deg + sweep) * Math.PI) / 180;
    });
    const size = Math.max(visual.length, visual.beam);
    const dist = size * 2.4;
    this.camera.position.set(dist * Math.cos(PITCH), dist * Math.sin(PITCH), 0);
    // Aim a little below the hull so it sits high in the frame, clear of the name plate.
    this.camera.lookAt(0, -size * 0.12, 0);
  }
}
