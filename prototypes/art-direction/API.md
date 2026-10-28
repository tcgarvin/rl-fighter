# Art-direction prototype, round 2: module contracts

Round 1 (frozen in `round1/`) gave each style its own hulls and palette. The owner's
feedback:

- The ships looked the same in every style anyway.
- Explore **rendering treatments**: materials, shaders, lighting, post-processing
  (a tilt-shift "miniature photograph" was one idea). Do not explore palette swaps.
- Keep the Abyssal Organisms explosions.
- A starfield background, with foreground dust and a little parallax so motion reads.
- Large, nicely painted scenery (planets and the like) off to one side of the battle,
  rarely behind it. There should be enough variety that it never feels like a
  rotation.
- No health bars. Damaged ships smoke, then burn, then arc electrically.
- Shields on some hulls, invisible until they deflect fire.
- The field starts empty. Ships jump in, in squads, with millisecond staggers, as an
  extremely fast streak from off-screen that ends with them already moving forward.

So round 2 splits rendering into **shared** modules (identical in every treatment) and
**treatments**, which only decide how things look.

```
hulls.js                 hull specs + mounts (do not edit)
sim.js                   scripted battle (do not edit)
main.js                  harness: owns the loop, camera, HUD, jump-in motion (do not edit)
shared/hullgeo.js        canonical hull models with material slots
shared/environment.js    starfield, parallax dust, procedural scenery
shared/effects.js        projectiles, hits, shields, explosions, damage FX, jump streaks
treatments/<id>.js       materials, lights, tone mapping, post-processing
treatments/index.js      registry (harness-owned)
```

## Viewing conditions

The owner reviews mostly on an **iPhone in portrait** (about 390×844 CSS px, DPR
capped at 2), as well as on desktop. Everything must read on a phone: effects and
scenery large enough to see, and HUD-safe framing (the harness measures the HUD
and frames the action in the band between the top bar and the bottom controls).
Test at both sizes.

## Coordinates (unchanged from round 1)

- The sim plane (x, y) maps to three.js (x, 0, -y). +Y is up.
- Hull-local axes: +X forward (nose), +Y up, +Z starboard, -Z port.
- Body-frame mounts `[x, y]` (+y = port) convert with `mountToLocal(pos, height)`,
  giving `[x, height, -y]`.
- A thruster's `dir` is the force direction; its exhaust points the opposite way.
- Turret angles are radians relative to the hull, counter-clockwise seen from above:
  `pivot.rotation.y = angle`.
- Units are metres. The arena radius is 520 m. The camera pitch is 58° down from
  horizontal. The camera frames about 160–700 m of the plane, and its distance is
  roughly 400–2000 m.

## shared/hullgeo.js

```js
export function buildHull(hull, team, mats) // -> HullModel
```

`mats` is a treatment's material set (see below). `HullModel`:

```js
{
  object,            // THREE.Group in the hull-local frame; the harness positions and rotates it
  thrusters,         // [{ node, size }], index-aligned with hull.thrusters; node at the mount, local +X = exhaust direction
  turrets,           // [pivot], index-aligned with hull.turrets; the harness sets pivot.rotation.y
  muzzles,           // [Object3D] at each barrel tip (children of the pivots)
  damagePoints,      // [THREE.Vector3] 6–10 hull-local points on the upper surface, for smoke, fire and arcs
  setThrottles(throttles, dt), // animate exhaust (0 / 0.5 / 1), smoothed, using mats.exhaust
  dispose(),
}
```

- Geometry is identical for every treatment. One canonical model per hull, built from
  the footprints in `PROPOSALS.md` and the mounts in `hulls.js`. Use the best ideas
  from round 1 (`round1/styles/*.js`).
- Each mesh uses exactly one slot: `mats.paint` (team-painted armour), `mats.trim`
  (light secondary plates), `mats.machinery` (dark joints, nozzles, turret bases),
  `mats.glow` (small emissive details: running lights, seams), `mats.marking` (team
  identity marks), `mats.exhaust`.
- Team identity must not rely only on colour. Team 0 carries one broad stripe and a
  solid diamond; team 1 carries two narrow stripes and a split square.
- Give meshes enough edge definition (bevels, panel breaks) that lighting and
  outline-based treatments have something to work with. Merge static geometry per
  slot.

## shared/environment.js

```js
export function createEnvironment({ THREE, scene, camera, renderer }) // -> Environment
```

```js
{
  newMatch(seed),               // regenerate the scenery deterministically from the seed
  update(dt, view),             // view = { centerX, centerY, extent } in sim metres: the camera's target and the half-size of what it frames
  dispose(),
}
```

- **Starfield:** far away, effectively no parallax. Varied star sizes and
  temperatures, plus a faint galactic band or dust lanes. Static: no twinkling noise.
- **Dust:** small motes in a volume around the battle plane (roughly y from -60 to
  +40 m), wrapping around the camera target, so camera pans and zooms produce gentle
  parallax. Sparse and dim: never mistakable for projectiles.
- **Scenery:** 1–3 large bodies per match, placed so that from the camera's typical
  framing they sit beyond the arena edge, to one side, top or bottom. The battle
  should rarely be drawn over them. Put them far below the plane (thousands of
  metres) so they are naturally slow-parallax backdrops.
- Planets must look **painted**: procedural shaders (layered noise, domain warping,
  banding for gas giants, continents and oceans, ice, lava, cloud layers, an
  atmospheric rim, a soft terminator from a consistent star direction). Include
  rings, moons, and the occasional nebula or distant station silhouette.
- Generate from the seed with wide parameter ranges (type, palette, size, rotation,
  rings, moons, light direction), so a hundred matches don't feel repetitive.
- **Budget:** about 1 ms per frame on Iris Xe. Render planets as a few shaded
  spheres or billboards, not huge particle counts.

## shared/effects.js

```js
export function createEffects({ THREE, scene, camera, renderer, palette }) // -> Effects
```

`palette` comes from the treatment: `{ team: [hexA, hexB], exhaust, projectile: [hexA, hexB], shield: [hexA, hexB] }`.

```js
{
  updateProjectiles(projectiles, beams, alpha), // sim lists; extrapolate by alpha / 30 s
  muzzle(e),        // { x, y, angle, team, weapon }
  hit(e),           // { x, y, team } hull hit (shield down)
  shieldHit(e),     // { x, y, nx, ny, radius, targetId, team, depleted }: impact point on the bubble and its outward normal. Show a brief local ripple, no permanent bubble. `depleted` gets a bigger collapse flash
  explosion(e),     // { x, y, radius, team, kind: "death" | "flak" }: port the Abyssal round-1 explosions
  arrival(e),       // { x, y, heading, team, size, duration }: jump streak and flash; the harness animates the hull itself
  attachDamage(hullModel), // -> { update(hpFrac, alive, dt), dispose() }: smoke under 70% HP, fire under 40%, arcing under 20%, emitted from damagePoints in world space (read hullModel.object.matrixWorld)
  update(dt, time),
}
```

- Pool everything. No allocation growth over hours.
- Smoke should trail behind moving ships (emit in world space, so the trail stays
  where it was emitted).

## treatments/<id>.js

```js
export default {
  id, name, blurb,
  hud: { "--bg": …, "--fg": …, "--muted": …, "--team-a": …, "--team-b": …, "--font": … },
  fonts: [],                      // optional Google Fonts CSS URLs
  palette: { team: [a, b], exhaust, projectile: [a, b], shield: [a, b] },
  init({ THREE, scene, renderer, camera }), // lights, tone mapping, environment map, post chain
  materials(team),                // -> { paint, trim, machinery, glow, marking, exhaust }; cache per team
  render(renderer, scene, camera, dt),
  onResize(width, height),
}
```

- A treatment differs in **how** things are rendered: material models, shader
  tricks, lighting, post-processing and camera-lens effects. It does not differ in
  geometry, and team hues may stay similar between treatments.
- It must stay legible: teams distinguishable, and every thruster's exhaust readable.
- Target 60 fps on Iris Xe at 1080p. Post-processing at most about 3 ms; use reduced
  resolution where you can.
- Only `three` and `three/addons/*` (r170) are available, as plain ES modules with no
  build step.

## Testing

A static server runs at http://localhost:8765/. To take a headless screenshot:

```
google-chrome --headless=new --no-sandbox --enable-unsafe-swiftshader --use-angle=swiftshader \
  --window-size=1280,720 --virtual-time-budget=5000 --screenshot=/tmp/x.png \
  "http://localhost:8765/?treatment=<id>&warmup=20"
```

Useful parameters: `warmup=<seconds>` fast-forwards the battle; `focus=<shipId>` gives
a close-up of one ship (ids 0–11); `seed=<n>` changes the match.
