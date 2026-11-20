# Citadel and dreadnought (SIM_VERSION 10): plan and contract

The owner asked (2026-11-19 evening) for a bigger station with individually destroyable
turrets, two capital ships on the attacking side, and a dreadnought that can go head to
head with a carrier. Chosen scope: **hardpoints + big station (destroyable bays)**, the
**lance turret**, the **dreadnought**, and **carrier + dreadnought attacking**. Not in
scope: shield generators, a separate carrier-vs-dreadnought mission (the owner may ask
later; don't build them).

This file is the contract between the sim work and the art work. Numbers marked *start*
are starting points that the script-vs-script balance may retune. The mount positions
are the contract: if the sim changes one, it updates this file in the same commit.

## Rules (v10)

1. **Hardpoints.** A capital ship's turrets and bays (role `carrier`, `transport`,
   `line`, or any `static` hull) carry their own hp, from the hull YAML (`hp`, and
   `hit_radius`, default 8 m). Under v10, when a hull hit lands (the shield is down) the
   ship's hull takes the damage as before, and **also** the nearest live hardpoint whose
   world mount is within its `hit_radius` of the impact point takes the same
   armour-scaled amount. The hull takes the full hit either way, so a hardpoint never
   soaks damage and hull balance is unchanged by it. A hardpoint at 0 hp is destroyed for the rest of
   the match: a dead turret never slews or fires, a dead bay never launches (its docked
   craft use the other bays; with every bay dead the reserve is stuck). Events
   `TurretDestroyed { ship, turret }` and `BayDestroyed { ship, bay }`. Strike craft
   keep whole-ship damage. Before v10 nothing changes (v9 replays bit-exact): either
   the rule is gated by sim version or the hardpoint hp only exists on v10 hulls; the
   sim agent picks and documents it.
2. **Capital-only weapons.** A weapon may set `capital_only: true`: its projectiles pass
   through strike craft, and turret aim (scripted capital fire control) only picks
   capital ships. The lance uses it.
3. **Role `line`** (the dreadnought). A capital ship flown by the scripted capital pilot,
   no bays. The nets read it as the obs class `spare` (index 5 of
   `order::HULL_CLASSES`; no input grows, OBS_DIM stays 587). If live pilots ignore it
   zero-shot, mapping it to the carrier class is the fallback, measured, not assumed.
4. **Station assault v10.** The defender is the `citadel`; the attacker brings a carrier
   **and** a dreadnought plus strike craft. The attacker is repelled when its carrier,
   its dreadnought and every strike craft are gone. A dead carrier's hangar dies as
   before; the dreadnought fights on. Arena radius *start* 550 m. The v9 `station` and
   its roster stay as they were for v9 compat.
5. **Hull ids.** Adding `citadel` and `dreadnought` must not move the v9 ids (`bomber`
   5, `station` 6): extend the frozen order rather than re-sorting by name.

## Citadel (`assets/hulls/citadel/hull.yaml`)

Static, role `carrier`, heading 0 at `(-0.35 R, y)` as the v9 station. Body frame +x
toward the attackers. Hexagonal ring: a core and six modules on spokes, with gaps a
strike craft can fly through (and crash in).

- hp *start* 3000, shield *start* 600 (regen 30/s, delay 5 s), shield radius 56, impact
  mult 0.5 all round, cost 320.
- Collision: core `(0,0)` r 20; six modules at radius 38, angles 0°, 60°, ..., 300°,
  r 11 each (module centre `38·(cos θ, sin θ)`). Gaps: ~16 m between modules, ~7 m
  between core and ring.
- Turrets (12; `MAX_TURRETS` must grow to at least 12). On each module, positions at
  radius 44 along the module angle θ, or at radius 42 at θ ± 8°. Rest angle = θ
  (outward) unless noted.

  Exact list (θ = module angle; L = lance, F = flak, G = gauss):

  | module θ | turrets |
  |---|---|
  | 0° | L at r 44, θ; F at r 42, θ − 8° |
  | 60° | F at r 42, θ − 8°; G at r 42, θ + 8° |
  | 120° | F at r 42, θ − 8°; G at r 42, θ + 8° |
  | 180° | L at r 44, θ; F at r 42, θ − 8° |
  | 240° | F at r 42, θ − 8°; G at r 42, θ + 8° |
  | 300° | F at r 42, θ − 8°; G at r 42, θ + 8° |

  Ids in that order: `turret.lance.0`, `turret.flak.0`, `turret.flak.1`,
  `turret.gauss.0`, `turret.flak.2`, `turret.gauss.1`, `turret.lance.1`,
  `turret.flak.3`, `turret.flak.4`, `turret.gauss.2`, `turret.flak.5`,
  `turret.gauss.3`. Arcs: lance 240 (slew 20), flak 200 (slew 90), gauss 200 (slew 120).
  hp *start*: lance 250, flak 120, gauss 100; hit_radius 8.
- Bays (4) on the core facing the gaps: angles 30°, 150°, 210°, 330°, mouth at radius
  22, dir outward. Ids `bay.0` .. `bay.3`. hp *start* 200, hit_radius 7.

## Dreadnought (`assets/hulls/dreadnought/hull.yaml`)

Role `line`, ~62 m long, armoured bow, soft stern: it pays to flank it. Body frame +x
forward, +y port.

- hp *start* 1800, shield *start* 350 (regen 18/s, delay 5 s), shield radius 36,
  mass 900, inertia 150000, speed_cap 7, cost 180.
- Impact (armour) *start*: bow ±60° 0.4; flanks 0.7; stern ±45° about 180° 1.3.
- Collision: `(20,0)` r 7, `(6,0)` r 9, `(-10,0)` r 9, `(-24,0)` r 7.
- Thrusters: mains `(-31, 5)`, `(-31, 0)`, `(-31, -5)` dir (1,0) force *start* 420;
  RCS `(22, 7)` (0,-1), `(22,-7)` (0,1), `(-22, 8)` (0,-1), `(-22,-8)` (0,1) force 600.
- Turrets (5):

| id | pos | rest | arc | slew °/s | weapon | hp *start* |
|---|---|---|---|---|---|---|
| turret.rail.fore | (14, 0) | 0 | 300 | 25 | rail | 220 |
| turret.rail.aft | (-14, 0) | 180 | 300 | 25 | rail | 220 |
| turret.flak.port | (0, 9) | 90 | 200 | 90 | flak | 120 |
| turret.flak.starboard | (0, -9) | -90 | 200 | 90 | flak | 120 |
| turret.gauss.bow | (26, 0) | 0 | 180 | 120 | gauss | 100 |

  The aft rail cannot fire within 30° of the bow, so pointing the armour at the enemy
  costs one main gun: the script holds the target some 35-45° off the bow.

## Weapons (`assets/weapons.yaml`, appended, so v9 weapon ids stay)

- `rail` *start*: bullet, speed 260, range 380, damage 40, interval 1.6, spread 0.3°.
  Hits anything; its slew makes fighters hard to track.
- `lance` *start*: bullet (rendered as a heavy beam-like slug), speed 300, range 430,
  damage 55, interval 2.2, spread 0.2°, `capital_only: true`.

## Scripts

- Dreadnought: closes on the nearest enemy capital to ~0.8 × rail range, holds it
  35-45° off the bow, and its rails aim at the nearest live enemy hardpoint in range
  (lances first), else the capital's centre. Flak and gauss as a carrier's.
- Scripted commander, station assault v10: the dreadnought advances with the carrier's
  strike; the defender's commander logic as v9's. Learned commanders must not crash on
  a second capital; the dreadnought is never given orders (it is not a strike craft).

## Live page and art

- Rosters (*start*): garrison `citadel` + 7 strike craft; attackers `carrier`,
  `dreadnought` + 9 strike craft (≤ `MAX_SHIPS` 20 together).
- Art (Codex, DESIGN §11): procedural geometry for the citadel and the dreadnought in
  `web/src/render/hullgeo.js`, matching the mounts above; a destroyed turret shows a
  scorched stump with smoke, a destroyed bay a dark, sparking mouth; lance and rail
  shots get their own projectile looks; a dev art scene for each.
- WASM exposes turret/bay alive state per ship so the renderer and inspector can show it.
