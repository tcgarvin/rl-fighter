// Fallback hull models: flat arrowheads. Used only when shared/hullgeo.js fails to load.
import * as THREE from "three";
import { mountToLocal } from "../../hulls.js";

export function buildHull(hull, team, mats) {
  const L = hull.length;
  const B = hull.beam;
  const shape = new THREE.Shape();
  shape.moveTo(L / 2, 0);
  shape.lineTo(-L / 2, B / 2);
  shape.lineTo(-L / 3, 0);
  shape.lineTo(-L / 2, -B / 2);
  shape.closePath();
  const geo = new THREE.ExtrudeGeometry(shape, { depth: 1.2, bevelEnabled: false });
  geo.rotateX(Math.PI / 2);
  const object = new THREE.Group();
  object.add(new THREE.Mesh(geo, mats.paint));

  const flameGeo = new THREE.ConeGeometry(0.5, 1, 8);
  flameGeo.rotateZ(-Math.PI / 2); // tip along +X, the exhaust direction
  flameGeo.translate(0.5, 0, 0);
  const thrusters = hull.thrusters.map((t) => {
    const node = new THREE.Object3D();
    node.position.set(...mountToLocal(t.pos, 0.4));
    node.rotation.y = Math.atan2(-t.dir[1], -t.dir[0]);
    const flame = new THREE.Mesh(flameGeo, mats.exhaust);
    node.add(flame);
    object.add(node);
    return { node, size: t.size, flame, level: 0 };
  });

  const barrelGeo = new THREE.BoxGeometry(2, 0.4, 0.4);
  barrelGeo.translate(1, 0, 0);
  const muzzles = [];
  const turrets = hull.turrets.map((t) => {
    const pivot = new THREE.Group();
    pivot.position.set(...mountToLocal(t.pos, t.height ?? 1));
    pivot.add(new THREE.Mesh(barrelGeo, mats.machinery));
    const muzzle = new THREE.Object3D();
    muzzle.position.x = 2;
    pivot.add(muzzle);
    muzzles.push(muzzle);
    object.add(pivot);
    return pivot;
  });

  const damagePoints = [new THREE.Vector3(0, 0.8, 0), new THREE.Vector3(-L / 4, 0.8, B / 6), new THREE.Vector3(-L / 4, 0.8, -B / 6)];

  return {
    object,
    thrusters,
    turrets,
    muzzles,
    damagePoints,
    setThrottles(throttles, dt) {
      thrusters.forEach((t, i) => {
        t.level += (throttles[i] - t.level) * Math.min(1, dt * 18);
        const len = 5 * t.size * t.level;
        t.flame.visible = len > 0.05;
        t.flame.scale.set(Math.max(len, 0.01), t.size, t.size);
      });
    },
    dispose() {
      geo.dispose();
    },
  };
}
