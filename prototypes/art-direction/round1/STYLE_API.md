# Style module API (art-direction prototype)

A style is an ES module in `styles/<id>.js` that default-exports an object:

```js
export default {
  id: "debug",
  name: "Debug",
  blurb: "One sentence shown in the style switcher.",
  // CSS custom properties applied to the HUD: --bg, --fg, --muted, --team-a, --team-b,
  // --font (a CSS font-family; Google Fonts may be loaded via `fonts`).
  hud: { "--bg": "#000", "--fg": "#fff", "--muted": "#888", "--team-a": "#4af", "--team-b": "#f84", "--font": "monospace" },
  fonts: [],                // optional Google Fonts CSS URLs

  init(ctx) {},             // ctx = { THREE, scene, renderer, camera, addons }
  createShip(ship) {},      // returns a ShipView (below); ship = { id, hullName, hull, team }
  createProjectiles(capacity) {}, // returns { update(projectiles, beams, alpha) }
  onMuzzle(evt) {},         // { x, y, angle, team, weapon }
  onHit(evt) {},            // { x, y, team }
  onExplosion(evt) {},      // { x, y, radius, team, kind: "death" | "flak" }
  update(dt, time) {},      // per rendered frame: advance effects, background animation
  render(renderer, scene, camera) { renderer.render(scene, camera); }, // override for post-processing
};
```

`ShipView`:

```js
{
  object: THREE.Object3D,   // added to the scene by the harness
  update(view, dt) {},      // view = { x, y, heading, throttles[], turretAngles[], firing[], hpFrac, alive }
  dispose() {},
}
```

## Coordinates

- The sim plane (x, y) maps to three.js (x, 0, -y). +Y is up; the camera looks down
  obliquely at the plane.
- The harness does **not** position the ship: `update` must set
  `object.position.set(view.x, 0, -view.y)` and `object.rotation.y = view.heading`.
- Hull-local axes after that rotation: +X forward (nose), +Z starboard, -Z port, +Y up.
- Mounts in `hulls.js` are body-frame `[x, y]` (+y = port). Convert with
  `mountToLocal(pos, height)` → `[x, height, -y]`.
- A thruster's `dir` is the direction of the force on the ship. **Exhaust points the
  opposite way**: exhaust direction (local) = `[-dir[0], 0, dir[1]]`.
- Turret angles in `view.turretAngles[i]` are radians relative to the hull, CCW when
  seen from above (same sense as heading). Set `turretMesh.rotation.y = angle`.
- Units are metres. A fighter is about 10 m long, a gunship 26 m. The camera
  typically frames 300–1500 m, so ships are small on screen: silhouettes and glow
  matter more than surface detail.

## Requirements

- Every thruster's exhaust must visibly reflect its throttle (0, 0.5, 1), smoothed a
  little so it doesn't flicker.
- Each turret is a separate mesh that rotates.
- Teams A (0) and B (1) must be instantly distinguishable at a glance, including when
  colour-blind (use shape or pattern too, not only hue).
- Pool and reuse projectile and effect objects (use `InstancedMesh` or fixed pools).
  No per-frame allocation growth: the page runs for hours.
- Target 60 fps on Intel Iris Xe. Keep post-processing cheap: at most one bloom
  pass, at reduced resolution.
- Only `three` and `three/addons/*` (r170) are available; there's no build step.
