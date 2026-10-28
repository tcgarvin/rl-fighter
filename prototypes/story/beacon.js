// The capture ring for "Hold the beacon": a flat ring on the battle plane that takes the
// colour of whoever is charging it, with one progress arc per team just inside it.

const ARC_SEGMENTS = 96;
// Rebuild an arc's geometry only when its progress moves this much (fraction of a turn).
const ARC_STEP = 0.004;

export function createBeaconView({ THREE, scene, palette }) {
  const group = new THREE.Group();
  group.visible = false;
  scene.add(group);
  const neutral = new THREE.Color(0x9aa7b4);
  const teams = palette.team.map((c) => new THREE.Color(c));
  const material = (color, opacity) =>
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });

  const ringMat = material(neutral.clone(), 0.55);
  const fillMat = material(neutral.clone(), 0.05);
  const arcMats = teams.map((c) => material(c.clone().multiplyScalar(2.2), 0.9));
  let ring = null;
  let fill = null;
  const arcs = [null, null];
  const arcProgress = [-1, -1];
  let radius = 0;

  function flat(geometry) {
    geometry.rotateX(-Math.PI / 2);
    return geometry;
  }

  function rebuildArc(team, progress) {
    if (arcs[team]) {
      group.remove(arcs[team]);
      arcs[team].geometry.dispose();
    }
    arcs[team] = null;
    arcProgress[team] = progress;
    if (progress <= 0) return;
    // Azure fills clockwise from the top, Ember anticlockwise, on separate tracks.
    const inner = radius - (team === 0 ? 7 : 12.5);
    const length = progress * Math.PI * 2;
    const start = Math.PI / 2 - (team === 0 ? length : 0);
    const mesh = new THREE.Mesh(flat(new THREE.RingGeometry(inner, inner + 4, ARC_SEGMENTS, 1, start, length)), arcMats[team]);
    mesh.position.y = 0.4;
    group.add(mesh);
    arcs[team] = mesh;
  }

  return {
    setMission(mission) {
      for (const m of [ring, fill, ...arcs]) {
        if (!m) continue;
        group.remove(m);
        m.geometry.dispose();
      }
      ring = fill = null;
      arcs[0] = arcs[1] = null;
      arcProgress[0] = arcProgress[1] = -1;
      group.visible = Boolean(mission?.beacon);
      if (!group.visible) return;
      const b = mission.beacon;
      radius = b.radius;
      group.position.set(b.x, 0, -b.y);
      ring = new THREE.Mesh(flat(new THREE.RingGeometry(radius - 2, radius, ARC_SEGMENTS)), ringMat);
      fill = new THREE.Mesh(flat(new THREE.CircleGeometry(radius - 2, ARC_SEGMENTS)), fillMat);
      ring.position.y = 0.3;
      fill.position.y = 0.2;
      group.add(fill, ring);
    },

    update(battle, dt, time) {
      if (!group.visible) return;
      const inside = battle.beaconInside ?? [0, 0];
      // The ring shows who is charging right now: one team's colour, or a contested flicker.
      let target = neutral;
      if (inside[0] > 0 && inside[1] === 0) target = teams[0];
      else if (inside[1] > 0 && inside[0] === 0) target = teams[1];
      const contested = inside[0] > 0 && inside[1] > 0;
      const k = 1 - Math.exp(-dt * 5);
      ringMat.color.lerp(target, k);
      fillMat.color.copy(ringMat.color);
      const pulse = 0.5 + 0.5 * Math.sin(time * (contested ? 14 : 3));
      ringMat.opacity = contested ? 0.35 + 0.5 * pulse : 0.5 + 0.25 * pulse;
      fillMat.opacity = target === neutral ? 0.03 : 0.06 + 0.04 * pulse;
      for (const team of [0, 1]) {
        const progress = battle.capture[team] / 100;
        if (Math.abs(progress - arcProgress[team]) >= ARC_STEP || (progress >= 1 && arcProgress[team] < 1)) rebuildArc(team, progress);
      }
    },
  };
}
