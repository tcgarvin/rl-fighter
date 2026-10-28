# Four directions for RL Fighter

The central visual subject should be **the control system in motion**: a fighter correcting its heading, a strafer translating while keeping its gun trained, a gunship rotating three turrets toward different targets. Surface detail matters less than making those actions legible at the fit-all camera distance.

Across all four directions:

- Team identity uses **color plus markings**: Team A carries one broad stripe and a solid diamond marker; Team B carries two narrow stripes and a split-square marker.
- Hull silhouettes stay identical across teams, preserving recognition of roles.
- Exhaust reflects actual actuator state: off, half, full. Turrets show actual aim. Effects never imply an action the simulation did not take.
- Position and heading interpolate between simulation ticks; discrete firing and throttle changes remain timestamped events.
- Small ships get simplified silhouettes and screen-space actuator indicators. Below a certain size, individual mounts cannot remain readable through geometry alone.
- Arrival, damage and explosions stay in the battle plane. Mesh thickness adds depth without suggesting vertical maneuvering.

## 1. Enamel Fleet

### Mood

Small, purposeful spacecraft resembling enamel-coated industrial instruments: broad painted plates, dark mechanical joints, exposed nozzles and unmistakable weapon assemblies. The scene feels like a living kinetic exhibit—tactile, orderly and quietly strange. Beauty comes from mechanisms coordinating, not from surface complexity. A stationary screenshot looks composed; motion reveals how each machine works.

### Palette

| Element | Colors |
|---|---|
| Background | Warm charcoal `#14191C` |
| Team A | Saffron `#F2BE43` |
| Team B | Periwinkle `#929EFF` |
| Shared hull / machinery | Porcelain `#DDD9CB` / graphite `#303A40` |
| Exhaust | Pale mint `#B6FFE0`, white core `#F4FFF9` |
| Projectiles | Bullets `#FFF2C4`, beams `#FFFFFF`, missiles `#FF926C` |
| UI | Text `#ECE9DF`, secondary `#A9B4B8`, panels `#20282D` |

### Shape language and roles

Fighter: a narrow arrowhead with one conspicuous rear engine. Strafer: a broad crossbar with four exposed side nozzles and a small rear engine. Gunship: a blunt, stable platform with separated circular turret shoulders.

Use thick plates, clipped corners and restrained bevels. Team paint covers roughly half the visible upper surface. Dark channels separate mechanisms. Future carriers get a broad fork around visibly open bays; minelayers get a scalloped rear magazine; tethered pairs remain two distinct bodies joined by one thin connector.

### Motion and combat

- **Thrusters:** dark, open sockets with a pale inner throat. Active exhaust is a short solid core plus a tapered translucent wedge. Half throttle has a shorter wedge; full throttle adds length and a second internal band.
- **Turrets:** dark circular pedestal, light rotating housing, long contrasting barrel. The housing and barrel rotate together.
- **Projectiles:** short bright capsules with restrained trails; missiles have a distinct head and their own exhaust.
- **Hits:** a brief local white chip and several planar fragments.
- **Explosions:** a compact cream flash, an expanding broken ring, then a few tumbling plates fading within a second. No persistent smoke blanket.

### Environment

A mostly empty charcoal arena with sparse, low-contrast stars and occasional calibration ticks around the boundary. No background objects resembling targets. The arena edge brightens locally when a ship enters the penalty region.

### Lighting and cost

One directional light, ambient fill, flat-shaded surfaces and baked-looking dark seams. No shadow maps, ambient occlusion or bloom required. Optional bloom affects only the brightest effects at reduced resolution.

**Expected cost:** low; transparent exhaust overlap is the main effects concern. This is the strongest baseline for Iris Xe, subject to testing at the eventual fleet size.

### HUD and journal

A clear sans serif for labels and prose; tabular numerals for match statistics; monospace only for bundle IDs and technical values. HUD panels resemble instrument labels. The journal uses warm paper-colored text, generous spacing and compact experiment charts.

### Spectator value and risks

The machinery explains behavior directly. Viewers can notice asymmetric firing, corrections and independent aiming without understanding reinforcement learning.

**Risks:** too many bevels make it toy-like; too much porcelain weakens team identity. Keep the construction severe and the team panels large.

---

## 2. Printed Orbits

### Mood

An animated scientific print: warm paper, crisp colored silhouettes, black mechanical marks and restrained overprinting. Ships resemble diagrams that have acquired agency. The presentation connects the battle to the public research journal, making each match feel like an experiment unfolding on an observatory chart.

### Palette

| Element | Colors |
|---|---|
| Background | Paper `#E8E1CF` |
| Team A | Vermilion `#B83C2E` |
| Team B | Deep teal `#17666B` |
| Shared structure | Ink `#252B2D` |
| Exhaust | Dark violet `#67418B` |
| Projectiles | Ink `#202629`, beam accent `#A65B12` |
| UI | Text `#252B2D`, muted `#696B61`, panels `#F5EFDF` |

### Shape language and roles

Ships are shallow extrusions with strong, nearly graphic footprints. Fighter: a solid dart. Strafer: a wide bracket with a central spine. Gunship: a rounded polygon punctuated by black turret discs. Cutouts and negative space carry role information; greebles are absent.

### Motion and combat

- **Thrusters:** discrete violet wedges with one internal line at half throttle and two at full. Off means no wedge.
- **Turrets:** black discs with long, colored pointer barrels.
- **Projectiles:** moving ink dashes; beams are crisp ruled strokes; missiles resemble pointed annotation arrows.
- **Hits:** tiny star-shaped ink bursts.
- **Explosions:** expanding broken contours and angular fragments, with no luminous flash.

### Environment

A faint coordinate grid, sparse plotted stars and an arena boundary resembling a charted limit. Keep paper texture static and extremely subtle; avoid animated noise.

### Lighting and cost

Mostly unlit materials with two or three authored face tones. Thin dark sidewalls provide depth in oblique view. Build borders into geometry instead of using a full-screen outline pass.

**Expected cost:** very low. Antialiasing and readable line widths matter more than lighting. Transparent layered “ink” should be used sparingly.

### HUD and journal

Editorial typography: a sturdy serif for journal titles, sans serif for controls, tabular numeric tables. Muster becomes a clean fleet plate; the result becomes a printed experiment card.

### Spectator value and risks

Trajectories, orientation and firing decisions read exceptionally well. The visual continuity between battle and journal makes the research process approachable.

**Risks:** may feel like a tactical diagram rather than a space battle. Dark projectiles can disappear over dark hulls; give them a narrow paper-colored border. Fine marks require careful zoom-dependent simplification.

---

## 3. Abyssal Organisms

### Mood

A black-water ecosystem of engineered organisms. Vessels have opaque shells, luminous seams and distinct functional appendages. Combat resembles unfamiliar creatures competing in an artificial habitat: coordinated, surprising and occasionally beautiful. The organic vocabulary makes future drones, tethered pairs and unusual control schemes feel native to the world.

### Palette

| Element | Colors |
|---|---|
| Background | Abyss `#060F18` |
| Team A | Coral `#FF806B` |
| Team B | Ice cyan `#69DCEB` |
| Shared shell | Blue slate `#304450` |
| Exhaust | Acid yellow `#E5FF87` |
| Projectiles | Pearl `#FFF5DF`, missiles `#CB9BFF` |
| UI | Text `#DFECEC`, muted `#88A8AF`, panels `#10232C` |

### Shape language and roles

Fighter: a tapered shell with a split tail. Strafer: a broad ray-like body with lateral propulsion lobes. Gunship: a squat armored carapace with turret nodules spaced around its crown.

Use faceted ellipsoids and tapered wedges, not high-resolution organic meshes. Team A has one continuous dorsal light band; Team B has paired bands.

### Motion and combat

- **Thrusters:** sharply bounded jets from visible siphon mouths. Their organic shape must retain an immediate off state.
- **Turrets:** rigid stalk-and-head assemblies with a clear forward spine.
- **Projectiles:** luminous seeds, short white beam filaments and visibly propelled missile pods.
- **Hits:** a local shell flare and a few bright flecks.
- **Explosions:** a brief luminous rupture followed by dark shell fragments and a fading ring.

Avoid breathing or rhythmic light animations on actuators: those would obscure actual policy actions.

### Environment

Almost empty depth, with a few distant specks and dim broad color fields. All active entities remain clearly anchored to one plane. No drifting foreground organisms.

### Lighting and cost

Low-poly standard materials, one directional light, ambient fill and emissive seams. Optional reduced-resolution bloom; no transmission, volumetrics or dynamic lights per projectile.

**Expected cost:** low to moderate. Bloom and overlapping translucent bursts are the principal costs; the style must still read with bloom disabled.

### HUD and journal

Spare aquarium-instrument typography: humanist sans serif, delicate dividers, bright numeric readouts. The journal resembles a field notebook with hull specimens and annotated behavior sequences.

### Spectator value and risks

Encourages viewers to perceive emergent behavior as adaptation. Swarms and unusual hulls gain a coherent identity.

**Risks:** soft forms obscure heading and turret aim. Glowing seams can merge into noise at distance. Use opaque silhouettes, limited luminous area and exaggerated directional features.

---

## 4. Signal Foundry

### Mood

Heavy mechanical vessels suspended over a dark operational display. Black metal bodies carry large hazard-colored identification slabs, exposed propulsion blocks and hard white weapon pointers. It feels like a public test range: forceful, precise and slightly austere. Every movement reads as an actuator applying force to mass.

### Palette

| Element | Colors |
|---|---|
| Background | Graphite `#101214` |
| Team A | Signal lime `#D1EA49` |
| Team B | Hot magenta `#EF77B7` |
| Shared hull | Steel `#657078`, recesses `#22282C` |
| Exhaust | Amber `#FFB454` |
| Projectiles | White `#F7FAEF`, missiles `#FF795D` |
| UI | Text `#E5E9DD`, muted `#9CA69D`, panels `#1D2223` |

### Shape language and roles

Fighter: a spear assembled around a long engine block. Strafer: a skeletal H frame with conspicuous lateral motor banks. Gunship: a broad slab with three oversized weapon stations.

Rectangular beams, exposed gaps and standardized mounting collars dominate. Future bays become large empty rectangles; tethered hulls resemble linked machinery.

### Motion and combat

- **Thrusters:** compact amber bars extending from black nozzles, with a bright transverse band indicating full throttle.
- **Turrets:** large steel discs and white rectangular barrels.
- **Projectiles:** sharp white streaks, straight beam segments, boxy missiles with amber tails.
- **Hits:** directional sparks concentrated at the impact.
- **Explosions:** a short polygonal flash and chunky debris. No camera shake during unattended viewing.

### Environment

A dark test field with faint boundary graduations and sparse distance marks. Optional order vectors use dashed lines, visually distinct from solid weapon traces.

### Lighting and cost

Hard directional lighting, restrained metalness, high roughness and a small static environment map. No screen-space reflections or real-time shadows.

**Expected cost:** low to moderate. Extra exposed parts can increase draw calls unless merged or instanced. It needs less post-processing than the organic direction.

### HUD and journal

Condensed sans-serif headings, tabular numerals and strongly aligned status tables. The journal resembles a test report, with large verdict labels and explicit before/after comparisons.

### Spectator value and risks

The exposed frame makes thrust allocation and weapon independence obvious. It scales naturally to carriers and strange mechanical hulls.

**Risks:** industrial detail can overwhelm small ships; lime and magenta can dominate long viewing sessions. Restrict bright paint to a few large surfaces and simplify aggressively at distance.

# Recommendation: Enamel Fleet

Enamel Fleet offers the best balance of character, actuator readability and economical rendering. Printed Orbits is the strongest alternative if the public-lab identity should dominate. Enamel Fleet gives the ships more physical presence while retaining similarly clear silhouettes.

Its defining rule should be:

> **A broad painted body identifies the ship; dark joints identify mechanisms; pale moving effects reveal actions.**

# Implementable procedural specification

## Coordinates and model contract

Use metres and a local **XY battle plane**, with **+X forward, +Y port and +Z dorsal**. Ship heading rotates around Z. The camera views from +Z with a modest oblique offset.

Every mount is a named `THREE.Object3D`:

- Thruster local +X points in the **force direction**. Exhaust extends along local −X.
- Turret local +X points in its rest aiming direction.
- Visible nozzles, barrel pivots and effects derive from those same transforms.
- Rotating turret visuals are children of the mount; apply the simulated turret angle once.
- Mount definitions come from the shared hull description used to produce the YAML and model. Styling must not silently move them.

The dimensions below are a proposed geometry-and-actuator draft. Force, mass, slew and weapon values still require gameplay tuning.

## Shared part kit

Build these reusable primitives:

| Part | Construction |
|---|---|
| Hull plate | Convex 2D polygon extruded in Z; one small bevel at near detail |
| Spine / crossbar | Box or clipped rectangular extrusion |
| Engine bell | Low-sided tapered shell with a dark open mouth and inset throat |
| RCS nozzle | Smaller engine bell with an opaque mounting collar |
| Turret | Eight-sided pedestal, clipped box housing, rectangular barrel |
| Team panel | Raised polygon, approximately 0.02 m above its parent surface |
| Exhaust | Instanced tapered wedge plus a smaller opaque bright core |
| Impact / burst | Pooled planar shards and expanding ring segments |

Use roughly six shared material families: porcelain, graphite, team paint, muted metal, exhaust and combat effects. Avoid unique textures per ship.

## Fighter — 10 m × 5.6 m × 1.5 m

**Silhouette:** narrow arrowhead, clipped nose, exposed rear bell.

- Main plate footprint:  
  `(5,0), (2.5,1.25), (-2.7,2.3), (-4.2,1.3), (-4.2,-1.3), (-2.7,-2.3), (2.5,-1.25)`.
- Plate spans Z = −0.45 to +0.45 m.
- Add a central dorsal spine, 5.8 × 1.2 × 0.55 m, centered at X = −0.1 m.
- Main bell occupies the rear center and extends to approximately X = −5 m.
- Four small RCS collars extend the maximum beam to 5.6 m.
- Paint the upper arrowhead in team color; leave the central spine porcelain and mechanisms graphite.

### Mounts

Angles are measured counterclockwise from +X; positions are `(x,y,z)`.

| Mount | Position, m | Force / rest angle |
|---|---|---:|
| `thruster.main.0` | `(-4.6, 0, 0)` | 0° |
| `thruster.rcs.fl` | `(2.2, 2.3, 0)` | −90° |
| `thruster.rcs.fr` | `(2.2, -2.3, 0)` | +90° |
| `thruster.rcs.rl` | `(-2.8, 2.3, 0)` | −90° |
| `thruster.rcs.rr` | `(-2.8, -2.3, 0)` | +90° |
| `turret.nose` | `(3.8, 0, 0.65)` | 0° |

The nose gun has zero firing arc. Its barrel extends to X ≈ 5 m.

This RCS layout provides lateral translation and both rotation directions. It has no dedicated reverse thrust; slowing relies on drag or turning to brake. That limitation should be deliberate and visible.

## Strafer — 9 m × 10.5 m × 1.4 m

**Silhouette:** a wide crossbar with a short forward spine. It should read as broader than it is long.

- Central body: clipped rectangle, X = −3.8 to +3.5 m, Y = ±1.25 m, thickness 0.8 m.
- Forward wedge reaches X = +4.5 m.
- Two transverse beams sit at X = +2.4 and −2.4 m, each about 1.1 m wide in X.
- Four nozzle pods terminate the beams at Y = ±4.7 m; outer bell edges reach Y ≈ ±5.25 m.
- Keep negative space between the beams.
- Weak main engine is visibly smaller than the Fighter’s.
- Paint the crossbars in team color; keep the central spine porcelain.

### Mounts

| Mount | Position, m | Force / rest angle |
|---|---|---:|
| `thruster.main.0` | `(-4.1, 0, 0)` | 0° |
| `thruster.lateral.fl` | `(2.4, 4.7, 0)` | −90° |
| `thruster.lateral.fr` | `(2.4, -4.7, 0)` | +90° |
| `thruster.lateral.rl` | `(-2.4, 4.7, 0)` | −90° |
| `thruster.lateral.rr` | `(-2.4, -4.7, 0)` | +90° |
| `turret.nose` | `(3.4, 0, 0.6)` | 0° |

Use a fixed forward gun initially, keeping the control distinction focused on propulsion. Same-side fore/aft thrusters produce translation; opposing diagonal thrusters produce rotation. The large lateral bells communicate their greater authority before the ship moves.

## Gunship — 15 m × 10 m × 2.6 m

**Silhouette:** blunt armored platform with three widely separated weapon stations.

- Main footprint:  
  `(7.5,0), (5,4), (-4.5,5), (-7.5,3), (-7.5,-3), (-4.5,-5), (5,-4)`.
- Main plate spans Z = −0.7 to +0.7 m.
- Add three shallow armor islands beneath the turret stations.
- Keep the upper surface otherwise flat so barrels remain visible.
- Two rear engine housings flank the centerline.
- Paint a broad perimeter band in team color; leave the weapon islands porcelain.
- Omit decorative aerials and narrow protrusions.

### Mounts

| Mount | Position, m | Force / rest angle |
|---|---|---:|
| `thruster.main.l` | `(-7, 2, 0)` | 0° |
| `thruster.main.r` | `(-7, -2, 0)` | 0° |
| `thruster.rcs.fl` | `(4, 4.4, 0)` | −90° |
| `thruster.rcs.fr` | `(4, -4.4, 0)` | +90° |
| `thruster.rcs.rl` | `(-4.5, 4.6, 0)` | −90° |
| `thruster.rcs.rr` | `(-4.5, -4.6, 0)` | +90° |
| `turret.fore` | `(3.8, 0, 1.05)` | 0° |
| `turret.port` | `(-2.7, 2.8, 1.05)` | +90° |
| `turret.starboard` | `(-2.7, -2.8, 1.05)` | −90° |

Each turret uses an approximately 1.5 m pedestal, 1.6 × 1.0 m housing and 2.2 m barrel. Start with a 240° fore arc and 220° side arcs centered on their rest directions. Verify muzzle clearance across those arcs before finalizing the YAML.

Slow movement should come from force-to-mass tuning, not decorative sluggish animation.

## Style-module responsibilities

The module should expose four clear operations:

```ts
buildHull(hullDefinition, team): HullVisual
applyState(visual, interpolatedPose, actuatorState): void
emitCombatEvent(event): void
dispose(): void
```

`HullVisual` contains the root, named mounts, turret pivots, actuator-instance handles and bounds. Physics footprints include structural hull parts and engine housings; exclude effects, identity markers and rotating decorative weapon parts. Validate the resulting collision-circle approximation against each silhouette.

### Readability and rendering rules

- At approximately **24 px hull length and above**, show full geometry and mount-attached exhaust.
- At **12–24 px**, omit bevels and secondary plates; preserve barrel direction and separated nozzle cores.
- Below **12 px**, render a simplified role silhouette and a small actuator diagram anchored beside the ship. Give every thruster a stable slot, with off/half/full states. Show the full diagram on hover or selection when crowding requires decluttering.
- Never enlarge collision geometry to match screen-space indicators.
- Use shared static geometry and materials. Merge static parts by material; instance repeated hull parts, turret components, exhaust and projectiles.
- Pool effects, cap their count and lifetime, and avoid allocations in the render loop.
- Start without post-processing, shadow maps or dynamic projectile lights. Cap device pixel ratio and test at the exhibit’s actual resolution.

## Exhibit acceptance checks

Before committing to the direction, use scripted matches to verify:

1. A viewer can distinguish both teams and all three roles at the widest expected camera framing.
2. A stationary demonstration makes every thruster’s off, half and full states identifiable.
3. A moving Gunship clearly shows hull heading and three independent aim directions.
4. Dense combat remains readable with bloom disabled and in grayscale.
5. Muster explains the fleet, arrival establishes the opposing sides, and results identify the winner and active champion.
6. A multi-hour run on Iris Xe sustains the frame target without growing memory or accumulating debris.

The performance claims above are design expectations, not measurements. Fleet size, display resolution, WASM inference load and transparency overdraw will determine the final budget.