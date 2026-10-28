// Fallback environment: a plain point starfield. Used only when shared/environment.js fails to load.
export function createEnvironment({ THREE, scene, camera }) {
  scene.background = new THREE.Color(0x020308);
  const count = 3000;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const v = new THREE.Vector3().randomDirection().multiplyScalar(40000);
    positions.set([v.x, v.y, v.z], i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const stars = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffffff, size: 1.5, sizeAttenuation: false }));
  scene.add(stars);
  return {
    newMatch() {},
    update() {
      stars.position.copy(camera.position);
    },
    dispose() {
      scene.remove(stars);
      geo.dispose();
    },
  };
}
