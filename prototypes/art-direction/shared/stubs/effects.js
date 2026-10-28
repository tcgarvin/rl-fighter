// Fallback effects: dots for projectiles, expanding spheres for everything else.
// Used only when shared/effects.js fails to load.
const MAX_PROJECTILES = 1024;
const MAX_BEAMS = 128;
const MAX_FX = 256;

export function createEffects({ THREE, scene, palette }) {
  const teamColor = palette.projectile.map((c) => new THREE.Color(c));
  const shots = new THREE.InstancedMesh(new THREE.SphereGeometry(0.7, 6, 4), new THREE.MeshBasicMaterial(), MAX_PROJECTILES);
  shots.frustumCulled = false;
  scene.add(shots);
  const beamPos = new Float32Array(MAX_BEAMS * 6);
  const beamGeo = new THREE.BufferGeometry();
  beamGeo.setAttribute("position", new THREE.BufferAttribute(beamPos, 3));
  const beams = new THREE.LineSegments(beamGeo, new THREE.LineBasicMaterial({ color: 0xffffff }));
  beams.frustumCulled = false;
  scene.add(beams);

  const fxGeo = new THREE.SphereGeometry(1, 10, 8);
  const fx = Array.from({ length: MAX_FX }, () => {
    const m = new THREE.Mesh(fxGeo, new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false }));
    m.visible = false;
    m.userData = { life: 0, maxLife: 1, radius: 1 };
    scene.add(m);
    return m;
  });
  let cursor = 0;
  const spawn = (x, y, radius, life, color) => {
    const m = fx[cursor];
    cursor = (cursor + 1) % MAX_FX;
    Object.assign(m.userData, { life, maxLife: life, radius });
    m.position.set(x, 1, -y);
    m.material.color.set(color);
    m.visible = true;
  };
  const matrix = new THREE.Matrix4();

  return {
    updateProjectiles(projectiles, beamList, alpha) {
      const n = Math.min(projectiles.length, MAX_PROJECTILES);
      for (let i = 0; i < n; i++) {
        const p = projectiles[i];
        matrix.makeTranslation(p.x + (p.vx * alpha) / 30, 1, -(p.y + (p.vy * alpha) / 30));
        shots.setMatrixAt(i, matrix);
        shots.setColorAt(i, teamColor[p.team]);
      }
      shots.count = n;
      shots.instanceMatrix.needsUpdate = true;
      if (shots.instanceColor) shots.instanceColor.needsUpdate = true;
      const nb = Math.min(beamList.length, MAX_BEAMS);
      for (let i = 0; i < nb; i++) {
        const b = beamList[i];
        beamPos.set([b.x1, 1, -b.y1, b.x2, 1, -b.y2], i * 6);
      }
      beamGeo.setDrawRange(0, nb * 2);
      beamGeo.attributes.position.needsUpdate = true;
    },
    muzzle() {},
    hit(e) {
      spawn(e.x, e.y, 2, 0.15, 0xffffff);
    },
    shieldHit(e) {
      spawn(e.x, e.y, 3, 0.2, palette.shield[e.team === 0 ? 1 : 0]);
    },
    explosion(e) {
      spawn(e.x, e.y, e.radius, e.kind === "death" ? 0.8 : 0.25, 0xffc060);
    },
    arrival(e) {
      spawn(e.x, e.y, e.size, 0.25, 0xffffff);
    },
    attachDamage() {
      return { update() {}, dispose() {} };
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
        m.scale.setScalar(m.userData.radius * (0.3 + t));
        m.material.opacity = 1 - t;
      }
    },
  };
}
