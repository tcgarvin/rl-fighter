# Order pilot: stronger in missions, but it does not visibly follow orders

Run 2026-10-30/31, plan: `plan.md` (gates fixed in §5 before any order pilot was
evaluated). **Nothing promoted.** No candidate passes gate O (order-following); every
candidate passes M (missions), D (deathmatch) and H (health). Fleet pilot v1 stays the
champion.

Verdict: **FAIL on the question asked** ("do pilots follow orders?"), with a large
side result: training on the missions makes a much better mission pilot. The best
candidates win 0.79 of carrier battles and 0.74 of convoys against v1.

## What ran

- Two arms from fleet pilot v1, widened to the 403-wide v5 obs with the order columns
  zeroed: order-reward weight `w = 1` (*w1*) and `w = 0.3` (*w03*). Each ran 400 PPO
  updates on the `orders_v1` mix (deathmatch 0.4, carrier 0.3, convoy 0.3; per team a
  scripted or random commander), with a KL anchor to v1 on rows without an order.
- Timeline from `run.out`: baseline 20:20–20:26. PPO 20:26–21:22, then **paused at
  updates 157/159** for the user's machine (clean SIGTERM checkpoints), resumed
  00:57–02:29. Gate evals 02:29–04:03. The run is not bit-identical to an uninterrupted
  one.
- About 22 s per update with two arms (rollout 4.5 s, PPO 16.4 s), as the plan measured.

## Gates (copied from `eval/gates.md`)

| candidate | O | M | D | H | all | mission win vs v1 | guard (random) | hold (random) | response (random) | dm vs script | dm vs v1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| w03_50 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.572 | 0.186 | 0.104 | 35.000 | 0.879 | 0.527 |
| w03_100 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.652 | 0.183 | 0.097 | 41.000 | 0.876 | 0.558 |
| w03_150 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.684 | 0.176 | 0.095 | 42.500 | 0.876 | 0.514 |
| w03_200 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.703 | 0.205 | 0.097 | 43.000 | 0.872 | 0.575 |
| w03_250 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.743 | 0.215 | 0.097 | 37.000 | 0.860 | 0.564 |
| w03_300 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.731 | 0.211 | 0.108 | 44.500 | 0.880 | 0.552 |
| w03_350 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.742 | 0.197 | 0.104 | 38.000 | 0.863 | 0.576 |
| w03_400 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.731 | 0.230 | 0.110 | 40.000 | 0.877 | 0.590 |
| w1_50 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.627 | 0.187 | 0.099 | 42.000 | 0.890 | 0.515 |
| w1_100 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.668 | 0.191 | 0.101 | 33.000 | 0.873 | 0.523 |
| w1_150 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.672 | 0.215 | 0.104 | 42.000 | 0.880 | 0.549 |
| w1_200 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.681 | 0.194 | 0.093 | 41.000 | 0.891 | 0.570 |
| w1_250 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.740 | 0.204 | 0.103 | 42.000 | 0.888 | 0.594 |
| w1_300 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.731 | 0.195 | 0.095 | 45.000 | 0.892 | 0.573 |
| w1_350 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.764 | 0.201 | 0.100 | 41.000 | 0.900 | 0.615 |
| w1_400 | ✗ | ✓ | ✓ | ✓ | ✗ | 0.763 | 0.227 | 0.116 | 41.000 | 0.892 | 0.613 |

What fails in O, for every candidate (the full list is in `eval/gates.md`):
- **Guard time inside** (90 m + bound of the ward), random commander: 0.18–0.23
  against a bound of 0.50. v1 scores 0.18.
- **Hold time inside**, random commander: 0.09–0.12 against 0.40. v1 scores 0.10.
  Under the scripted commander it is 0.00–0.02 for everyone, v1 included.
- **Attack time to gun range** (targets 0–250 m outside range): median 168–247 ticks
  against a bound of 150. v1: 343.
- Attack damage share passes only for some candidates (w1_150, w1_400, w03_350).
- Response time passes everywhere, but v1 passes it too: it does not separate pilots,
  as the plan warned.

## Do the order inputs matter at all? The blanked baseline

The plan runs the secondary baseline only for candidates that pass. It was run by hand
for the two final checkpoints (`eval/*_orders_blank.json`): the same pilot with the 18
order floats zeroed.

| who | scenario | attack share | attack close (median ticks) | guard inside | hold inside |
|---|---|---|---|---|---|
| v1 | carrier / random | 0.452 | 271.5 | 0.147 | 0.094 |
| w1_400 | carrier / random | 0.526 | 239.5 | 0.194 | 0.117 |
| w1_400 blanked | carrier / random | 0.526 | 302.0 | 0.126 | 0.109 |
| v1 | convoy / random | 0.290 | 532.0 | 0.223 | 0.110 |
| w1_400 | convoy / random | 0.292 | 133.0 | 0.277 | 0.113 |
| w1_400 blanked | convoy / random | 0.273 | 292.0 | 0.229 | 0.103 |
| v1 | convoy / scripted | 0.235 | 184.5 | 0.298 | 0.002 |
| w1_400 | convoy / scripted | 0.234 | 63.0 | 0.369 | 0.013 |
| w1_400 blanked | convoy / scripted | 0.214 | 139.0 | 0.320 | 0.008 |

- **The orders are read, a little.** With its orders, w1_400 closes on an attack target
  about twice as fast as with them blanked (133 vs 292 ticks in convoy), and guards
  spend about 0.05–0.07 more of their time by the ward.
- **Holds are ignored.** Time inside a hold is about 0.1 with or without the order,
  close to chance.
- w03_400 shows the same pattern, weaker.

## Missions: the side result

Win rate against v1 (both sides under the scripted commander, capital ships by script,
live default rosters, n = 516 per mission; v1 against itself: 0.496 / 0.5):

| candidate | carrier battle | convoy escort | time-limit rate (carrier) |
|---|---|---|---|
| w1_400 | 0.787 | 0.738 | 0.008 |
| w1_350 | 0.789 | 0.738 | 0.012 |
| w03_400 | 0.750 | 0.711 | 0.014 |
| w03_250 | 0.772 | 0.713 | 0.019 |

Deathmatch holds: `fleet_v1` win against the script 0.86–0.90 (v1: 0.889), against v1
0.51–0.62. Engine duty is unchanged from v1 (fighter about 0.2 in missions, the same
under every order kind), so the order reward did not cause the farming the design
review feared, but it did not get the pilots moving either.

## Why, probably

1. **Following competes with winning, and winning pays more.** A random hold point is
   usually away from the fight. Per order instance, following pays at most the arrival
   bonus plus the capped presence (≤ 0.19) plus the net approach shaping, which is
   given back when the ship leaves. A kill pays about 1, and the terminal reward is ±1.
   Ignoring a hold is the rational policy under this reward. Guard and attack overlap
   with fighting, which is why they moved a little.
2. **Nothing shows the pilot *how* to follow.** The recipe that taught v1 to fire was
   behaviour cloning from a script. PPO from scratch never learned it. Here the
   order-following scripts (`scripted/orders.rs`) exist and fly every order, but stage B
   used them only as opponents.
3. **Slow rewiring.** The 18 new inputs start at zero; with actor LR 1e-4, clip 0.1 for
   200 updates and the KL anchor, 400 updates move them a little. Guard and attack
   numbers creep up across checkpoints, but nowhere near the bounds.

## Next

- **Run B2b: a script pull on ordered rows.** Use the existing β mechanism, but only on
  rows with `has_order = 1`, toward the order-following script's action for that ship
  (labels from `scripted_actions()`, which already follow orders under the random and
  external commanders). Start it at β 0.1 and decay it over 300 updates; keep the KL
  anchor to v1 on unordered rows. Optionally start with a short DAgger round on ordered
  rows only. Start from w1_400, not v1, to keep the mission gains.
- **Make following pay against winning, or stop asking for it when it can't.** Draw
  random hold points near the action (between the squad and the nearest enemies), not
  uniform in 0.7 R, and raise the presence cap so that a held point pays on the scale
  of a kill. Or condition the terminal reward on following (a commander's team wins *as
  ordered*).
- **The gate bounds stand.** A guard 50 % of the time by its ward and a hold 40 % in its
  radius is what a viewer needs to see; the run fell short of them, not the reverse.
- **Shipping w1_400 anyway** (orders barely followed, missions much stronger) would need
  the user to waive gate O, as they waived engine duty for fleet pilot v1. It is not
  promoted by this run's rule.

## Corrections (2026-10-31, while preparing run B2b)

Measured on the B2b branch; see `../2026-10-31-order-pilot-b2b/plan.md` §1–2.

- **The shaping term pays nothing net.** It is potential-based with the trainer's γ,
  so its expected sum is zero, and "given back when the ship leaves" undersells it.
  The "order reward ≈ 4× team reward per step" seen in the timing slice was mostly the
  neutral −(1 − γ)Φ term. The real pay for following was only arrival (0.1) plus
  presence (≤ 0.09): even smaller than this write-up said.
- **The lever is the presence rate, not its cap.** Ships stay inside a radius for more
  than 300 ticks in under 10 % of orders, so a higher cap pays almost nothing extra.
- **"The gate bounds stand" was wrong for two bounds.** The order-following script
  itself scores guard time within 0.386 (bound 0.50) and attack share v1 + 0.074
  (margin + 0.10) under the random commander. B2b sets those two from the teacher
  (0.35 and + 0.05) before any of its candidates is evaluated. Run 1 still fails them.
- **Holds were partly geometry.** With hold points drawn near the fight, v1 with no
  training at all goes from 0.10 to 0.26 hold time inside, and w1_400 to 0.31.
- **Advisory deathmatch orders** show in the obs (about 20 % of ordered training rows)
  but the scripts ignore them, so a plain `has_order` mask would pull those rows toward
  labels that don't follow the order. B2b excludes them.
