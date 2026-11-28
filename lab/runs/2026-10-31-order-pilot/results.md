# Order pilot: stronger in missions, but it does not visibly follow orders

Run 2026-10-30/31, `SIM_VERSION` 5 (the version of the game's rules that first shows
pilots their orders), plan: `plan.md`. **Nothing promoted**: fleet pilot v1 stays the
pilot that flies the project's website.

<!-- summary: We tried to teach the learned pilot to follow its commander's orders by showing it the orders and paying it a little for following them. It did not visibly follow: ships told to guard or hold a spot stayed about where the old pilot would have flown. But training on the new missions made a much stronger pilot, which won 0.79 of carrier battles against the old one. -->

The question was whether a pilot shown its orders, and paid a little for carrying them
out, would learn to follow them. It did not: ships told to guard a friend or hold a
point spent about as much time there as the old pilot, which cannot see orders at all.
Attack orders were read a little. The side result is large: a night of training on the
carrier and convoy missions made a much stronger mission pilot.

Verdict: **FAIL on the question asked** ("do pilots follow orders?"), with a large side
result: training on the missions makes a much better mission pilot.

## Where this fits

RL Fighter is a space-combat game where every small ship is flown by a neural network,
the **pilot**, that learned to fly by trial and error. The project's website plays
matches forever on its front page, the **live page**. Shortly before this run, [fleet
pilot v1](../2026-10-30-fleet-pilot/results.md) became the one pilot on the live page.
Then the [mission survey](../2026-10-30-mission-survey/results.md) added two missions to
the team deathmatch (small ships only, 1 to 4 a side, until one side is destroyed). In
a **carrier battle** each side has a carrier that launches its strike craft, and a side
wins by destroying the enemy carrier. In a **convoy escort** one side's escorts guard
freighters flying to a jump point and the other side attacks, winning if it destroys at
least half of them. Each side has a hand-written **commander** that splits its ships
into squads and gives each squad an **order**: attack a named enemy, guard a friendly
ship (its "ward", the ship to protect), or hold a point. Pilot v1 cannot see those
orders. It just fights the nearest enemy, so the orders drawn on the page changed
nothing about how ships flew. This version of the rules appends 18 numbers describing a
ship's order to what its pilot sees, and adds a small reward for following it. This run
asks whether training with them makes pilots follow. If they do, a commander can change
how a match goes, which the game's design depends on. In the project's plan
(`docs/M3_PLAN.md`) this is stage B, the step meant to get pilots to follow orders, and
this was its first run, "run 1".

<!-- figure-idea: shared: what an order is. A commander gives a squad an attack, guard or hold order; the pilot sees it as a few extra numbers (the kind, where the target is, how far outside its radius the ship is); and each kind is scored its own way (attack: damage on the target; guard: time near the ward; hold: time inside the circle). -->

## What ran

- Two **arms** (versions of the experiment, trained side by side and identical except
  for one setting), both starting from fleet pilot v1. Its inputs were widened to the
  403 numbers this rules version shows, with the new order inputs starting at zero
  weight, so at the start each arm flies exactly like v1. The one setting is how much
  the order reward counts next to the reward for fighting and winning: weight `w = 1`
  (*w1*) or `w = 0.3` (*w03*).
- Each arm ran 400 **updates** (one update is a batch of matches played, then one
  adjustment of the network) of trial-and-error training (PPO). The matches were the
  `orders_v1` mix: deathmatch 0.4, carrier battle 0.3, convoy 0.3, with each side's
  orders coming from the scripted commander or from a **random commander** that hands
  out random orders, to teach following any order. A "KL anchor" kept the pilot's
  choices close to v1's at moments when the ship had no order, so that only ordered
  flying would change.
- Timeline from `run.out`: baseline 20:20–20:26. Training 20:26–21:22, then **paused at
  updates 157/159** for the owner's machine (both arms saved cleanly), resumed
  00:57–02:29. Gate evals 02:29–04:03. The run is not bit-identical to an uninterrupted
  one.
- About 22 s per update with two arms (playing matches 4.5 s, adjusting the network
  16.4 s), as the plan measured.

## Verdict in detail

The plan fixed four pass marks ("gates") in its §5 before any pilot was measured. A
pilot had to meet all four to replace v1 on the live page:

| gate | what it checks | pass mark |
|---|---|---|
| O, following | under the random commander: time a guard spends near its ward, time a hold spends inside its circle, how fast an attacker reaches gun range, the share of its damage on the target, how fast it turns toward its order (smaller margins under the scripted commander) | guard ≥ 0.50, hold ≥ 0.40 (each also ≥ v1's + 0.15), attack ≤ 150 ticks (a tick is 1/30 s), attack share ≥ v1's + 0.10, turn ≤ 90 ticks |
| M, missions | win rate against v1 in carrier battles and convoys | ≥ 0.47 in each, ≥ 0.52 on average |
| D, deathmatch | win rate in the standard deathmatch lineups | ≥ 0.85 against the script (the hand-written pilot), ≥ 0.45 against v1 |
| H, health | matches end normally | clock-outs and stalemates at most 0.10 and 0.05 above v1 against itself, broken or stuck matches ≤ 1 %, outside-the-arena share ≤ 0.02 |

No candidate (a saved copy of an arm, listed below) passes gate O. Every candidate
passes M, D and H. The best candidates win
0.79 of carrier battles and 0.74 of convoys against v1.

## Gates (copied from `eval/gates.md`)

Each row is a **candidate**: a saved copy of one arm, named by its arm and the update it
was saved at (`w1_350` is the w1 arm at update 350). O, M, D and H are the four gates
(✓ met, ✗ not), and "all" is whether every one is met. The numbers that follow are
measured in matches played only to measure. "Mission win vs v1" is the mean share of
carrier battles and convoys won against v1. Under the random commander, "guard" is the
share of a guard order's time the ship spent close to its ward (within 90 m plus the
ward's size), "hold" the share spent inside the hold circle, and "response" the median
time, in ticks (the game runs 30 ticks a second), until the ship's nose points within
30° of its order's target. The last two columns are deathmatch win rates against the
hand-written scripted pilot ("the script") and against v1.

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
- Attack damage share (the share of a ship's damage under attack orders that lands on
  its ordered target) passes only for some candidates (w1_150, w1_400, w03_350).
- Response time passes everywhere, but v1 passes it too: it does not separate pilots,
  as the plan warned.

## Do the order inputs matter at all? The blanked baseline

To see whether the pilots use their order inputs at all, we also flew the two final
candidates with their 18 order inputs set to zero ("blanked"), so that they see no
order, on the same evaluation (`eval/*_orders_blank.json`). The plan runs this only
for candidates that pass, and it was run by hand here. Each row is one pilot in one setting (mission and
commander). "Attack share" and "guard inside" and "hold inside" are as above. "Attack
close" is the median ticks to reach gun range of the target.

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

Win rate against v1 (both sides under the scripted commander, capital ships flown by
script, the live page's default lineups, 516 matches per mission; v1 against itself
scores 0.496 in carrier battles and 0.502 in convoys, so 0.5 is an even fight). A draw counts half. The last column is the
share of carrier battles that ran out the clock.

| candidate | carrier battle | convoy escort | time-limit rate (carrier) |
|---|---|---|---|
| w1_400 | 0.787 | 0.738 | 0.008 |
| w1_350 | 0.789 | 0.738 | 0.012 |
| w03_400 | 0.750 | 0.711 | 0.014 |
| w03_250 | 0.772 | 0.713 | 0.019 |

Deathmatch holds: `fleet_v1` (the standard set of deathmatch lineups) win against the
script 0.86–0.90 (v1: 0.889), against v1 0.51–0.62. Engine duty (how hard a ship runs
its strongest thruster, on average) is unchanged from v1 (fighter about 0.2 in missions,
the same under every order kind). So the order reward did not cause the farming the
design review feared (ships parking on a point to collect pay), but it did not get the
pilots moving either.

## Why, probably

1. **Following competes with winning, and winning pays more.** A random hold point is
   usually away from the fight. For one order given to one ship, following
   pays at most a one-off bonus for arriving plus a capped pay for time spent inside
   (together ≤ 0.19), plus pay for approaching the point, which is taken back when the
   ship moves away again. A kill pays about 1, and the reward at the end of
   a match is ±1 for a win or a loss. Ignoring a hold is the rational policy under this
   reward. Guard and attack overlap with fighting, which is why they moved a little.
2. **Nothing shows the pilot *how* to follow.** The recipe that taught v1 to fire was
   behaviour cloning, copying a script's choices. Trial-and-error training from scratch
   never learned it. Here the order-following scripts (`scripted/orders.rs`) exist and
   fly every order, but this run used them only as opponents.
3. **Slow rewiring.** The 18 new inputs start at zero. With small training steps
   (actor learning rate 1e-4, PPO clip 0.1 for 200 updates) and the KL anchor, 400
   updates move them a little. Guard and attack numbers creep up across checkpoints,
   but nowhere near the bounds.

<!-- figure-idea: why following lost to winning: a ship between a random hold point away from the fight and an enemy, with the pay for each path drawn to scale (at most about 0.19 for holding, about 1 for a kill, ±1 for the match). -->

## Next

- **Run B2b, the follow-up: a script pull on ordered rows.** A "script pull" is an extra
  training term that pulls the pilot's choices toward a script's. Use it only on rows
  (one ship's view and choice at one moment of training) where the ship has an order
  (`has_order = 1`), pulling toward what the order-following script would do in that
  moment (the scripts already follow the random commander's orders, and those of any
  outside program that sends orders, so they can supply these answers, from
  `scripted_actions()`). Start it at strength β 0.1 and decay it
  over 300 updates; keep the KL anchor to v1 on unordered rows. Optionally start with a
  short DAgger round on ordered rows only (the pilot flies, and the script says what it
  would have done in those moments). Start from w1_400, not v1, to keep the mission
  gains.
- **Make following pay against winning, or stop asking for it when it can't.** Draw
  random hold points near the action (between the squad and the nearest enemies), not
  uniform in 0.7 R (anywhere within 70 % of the arena's radius), and raise the presence
  cap so that a held point pays on the scale of a kill. Or condition the end-of-match
  reward on following (a commander's team wins *as ordered*).
- **The gate bounds stand.** A guard 50 % of the time by its ward and a hold 40 % in its
  radius is what a viewer needs to see; the run fell short of them, not the reverse.
- **Shipping w1_400 anyway** (orders barely followed, missions much stronger) would need
  the owner to waive gate O, as the owner waived fleet pilot v1's pass mark for engine
  use (its fighters ran their engines less than the bar asked). It is not promoted by
  this run's rule.

## Corrections (2026-10-31, while preparing run B2b)

Measured while preparing the follow-up run; see its plan,
[B2b plan §1–2](../2026-10-31-order-pilot-b2b/plan.md). Its results are in
[the B2b entry](../2026-10-31-order-pilot-b2b/results.md).

- **The approach pay nets to nothing.** The pay for approaching a guard or hold point
  is the change, step by step, in a score that is higher the closer the ship is. Moving
  in earns, moving out costs the same, so a trip in and back out sums to about zero, and
  "taken back when the ship moves away" undersells that. It had looked larger. Before
  the run, a short trial run made to time the training also logged the rewards, and the
  order reward per step came out about 4× the per-step reward for fighting and winning.
  That is why the plan feared ships would park on points to collect pay, and ran the
  lower-weight `w03` arm as a guard against it. Most of that 4× was a part of the
  approach pay that cancels out over a trip. The real pay for following was only
  arrival (0.1) plus presence (≤ 0.09): even smaller than this write-up said. (For the
  record: the score is Φ, the per-step pay is γΦ′ − Φ with γ the trainer's discount,
  and the part that cancels is −(1 − γ)Φ. A reader can skip this.)
- **The lever is the presence rate, not its cap.** Presence pay is 0.0003 for each tick
  a ship spends inside the order's radius, paid for at most 300 ticks per order, which
  is where the 0.09 cap comes from. Ships stay inside for more than 300 ticks in under
  10 % of orders, so they almost never reach the cap, and raising it pays almost nothing
  extra. Raising the pay per tick would.
- **"The gate bounds stand" was wrong for two bounds.** The order-following script
  itself scores guard time within 0.386 (bound 0.50) and attack share v1 + 0.074
  (the bar asks for v1 + 0.10) under the random commander. B2b sets those two from the teacher
  (0.35 and + 0.05) before any of its candidates is evaluated. Run 1 still fails them.
- **Holds were partly geometry.** With hold points drawn near the fight, v1 with no
  training at all goes from 0.10 to 0.26 hold time inside, and w1_400 to 0.31.
- **Orders in deathmatch are only for show.** In deathmatch the scripted commander also
  gives orders, which pilots see but the hand-written pilots do not follow. They make up
  about 20 % of the training moments with an order. A pull toward the script on every
  ordered moment would there pull the pilot toward choices that ignore the order. B2b
  leaves those moments out of the pull.
