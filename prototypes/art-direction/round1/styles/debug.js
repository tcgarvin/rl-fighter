// Reference style: deliberately plain. It shows how a style module uses the API.
import * as THREE from "three";
import { mountToLocal } from "../hulls.js";

const TEAM_COLORS = [0x4fb3ff, 0xff8a3d];
const MAX_BEAMS = 128;
const MAX_FX = 256;

let scene;
const fx = [];
let fxCursor = 0;

function hullShape(hull) {
  const L = hull.length;
  const B = hull.beam;
  const s = new THREE.Shape();
  s.moveTo(L / 2, 0);
  s.lineTo(-L / 2, B / 2);
  s.lineTo(-L / 3, 0);
  s.lineTo(-L / 2, -B / 2);
  s.closePath();
  return s;
}

export default {
  id: "debug",
  name: "Debug",
  blurb: "Plain reference style used to check the harness.",
  hud: { "--bg": "#05060a", "--fg": "#e8ecf2", "--muted": "#7d8696", "--team-a": "#4fb3ff", "--team-b": "#ff8a3d", "--font": "ui-monospace, monospace" },

  init(ctx) {
    scene = ctx.scene;
    scene.background = new THREE.Color(0x05060a);
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(300, 800, 200);
    scene.add(sun);
    const grid = new THREE.PolarGridHelper(520, 12, 6, 64, 0x1b2230, 0x1b2230);
    scene.add(grid);
    const fxGeo = new THREE.SphereGeometry(1, 10, 8);
    for (let i = 0; i < MAX_FX; i++) {
      const m = new THREE.Mesh(fxGeo, new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false }));
      m.visible = false;
      m.userData = { life: 0, maxLife: 1, radius: 1 };
      scene.add(m);
      fx.push(m);
    }
  },

  createShip(ship) {
    const color = TEAM_COLORS[ship.team];
    const root = new THREE.Group();
    const geo = new THREE.ExtrudeGeometry(hullShape(ship.hull), { depth: 1.5, bevelEnabled: false });
    geo.rotateX(Math.PI / 2);
    const body = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.6 }));
    root.add(body);
    const exhaustMat = new THREE.MeshBasicMaterial({ color: 0xfff1b0, transparent: true, opacity: 0.9 });
    const flames = ship.hull.thrusters.map((t) => {
      const g = new THREE.ConeGeometry(0.6 * t.size, 1, 8);
      g.translate(0, -0.5, 0);
      const m = new THREE.Mesh(g, exhaustMat);
      const [x, y, z] = mountToLocal(t.pos, 0.5);
      m.position.set(x, y, z);
      // Point the cone's -Y (tip) along the exhaust direction.
      const ex = new THREE.Vector3(-t.dir[0], 0, t.dir[1]);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), ex);
      root.add(m);
      return { mesh: m, size: t.size, level: 0 };
    });
    const turrets = ship.hull.turrets.map((t) => {
      const g = new THREE.Group();
      const [x, y, z] = mountToLocal(t.pos, 1.6);
      g.position.set(x, y, z);
      const barrel = new THREE.Mesh(new THREE.BoxGeometry(t.arc > 0 ? 4 : 2, 0.5, 0.5), new THREE.MeshStandardMaterial({ color: 0xdddddd }));
      barrel.position.x = t.arc > 0 ? 2 : 1;
      g.add(barrel);
      root.add(g);
      return g;
    });
    return {
      object: root,
      update(view, dt) {
        root.visible = view.alive;
        root.position.set(view.x, 0, -view.y);
        root.rotation.y = view.heading;
        flames.forEach((f, i) => {
          f.level += (view.throttles[i] - f.level) * Math.min(1, dt * 18);
          const len = 6 * f.size * f.level;
          f.mesh.visible = len > 0.05;
          f.mesh.scale.set(1, Math.max(len, 0.01), 1);
        });
        turrets.forEach((g, i) => (g.rotation.y = view.turretAngles[i]));
      },
      dispose() {
        geo.dispose();
      },
    };
  },

  createProjectiles(capacity) {
    const mesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 6, 4), new THREE.MeshBasicMaterial(), capacity);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    scene.add(mesh);
    const beamGeo = new THREE.BufferGeometry();
    const beamPos = new Float32Array(MAX_BEAMS * 6);
    const beamCol = new Float32Array(MAX_BEAMS * 6);
    beamGeo.setAttribute("position", new THREE.BufferAttribute(beamPos, 3));
    beamGeo.setAttribute("color", new THREE.BufferAttribute(beamCol, 3));
    const beams = new THREE.LineSegments(beamGeo, new THREE.LineBasicMaterial({ vertexColors: true }));
    beams.frustumCulled = false;
    scene.add(beams);
    const m = new THREE.Matrix4();
    const c = new THREE.Color();
    return {
      update(projectiles, beamList, alpha) {
        const n = Math.min(projectiles.length, capacity);
        for (let i = 0; i < n; i++) {
          const p = projectiles[i];
          const r = p.kind === "flak" ? 0.9 : 0.6;
          m.makeScale(r, r, r).setPosition(p.x + p.vx * alpha / 30, 1, -(p.y + p.vy * alpha / 30));
          mesh.setMatrixAt(i, m);
          mesh.setColorAt(i, c.set(TEAM_COLORS[p.team]));
        }
        mesh.count = n;
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        const nb = Math.min(beamList.length, MAX_BEAMS);
        for (let i = 0; i < nb; i++) {
          const b = beamList[i];
          beamPos.set([b.x1, 1, -b.y1, b.x2, 1, -b.y2], i * 6);
          c.set(TEAM_COLORS[b.team]);
          beamCol.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6);
        }
        beamGeo.setDrawRange(0, nb * 2);
        beamGeo.attributes.position.needsUpdate = true;
        beamGeo.attributes.color.needsUpdate = true;
      },
    };
  },

  onMuzzle() {},

  onHit(e) {
    spawnFx(e.x, e.y, 2, 0.15, 0xffffff);
  },

  onExplosion(e) {
    spawnFx(e.x, e.y, e.radius, e.kind === "death" ? 0.8 : 0.25, e.kind === "death" ? 0xffc060 : 0xdddddd);
  },

  update(dt) {
    for (const m of fx) {
      if (!m.visible) continue;
      m.userData.life -= dt;
      if (m.userData.life <= 0) {
        m.visible = false;
        continue;
      }
      const t = 1 - m.userData.life / m.userData.maxLife;
      const r = m.userData.radius * (0.3 + t);
      m.scale.set(r, r, r);
      m.material.opacity = 1 - t;
    }
  },

  render(renderer, s, camera) {
    renderer.render(s, camera);
  },
};

function spawnFx(x, y, radius, life, color) {
  const m = fx[fxCursor];
  fxCursor = (fxCursor + 1) % fx.length;
  m.visible = true;
  m.position.set(x, 1, -y);
  m.material.color.set(color);
  m.userData.life = life;
  m.userData.maxLife = life;
  m.userData.radius = radius;
}
