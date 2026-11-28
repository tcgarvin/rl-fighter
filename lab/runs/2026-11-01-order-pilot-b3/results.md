# Order pilot, third run (B3): the pull still costs the fight, the reward alone barely moves

Run 2026-10-31 (the directory is dated for the night it was planned for), `SIM_VERSION`
6 (the version of the game's rules with the redesigned orders), plan: `plan.md`. "B3" is
the project's name for this third order-pilot run. **Nothing promoted**: fleet pilot v1
stays the pilot that flies the project's website.

<!-- summary: Our third try at teaching the learned pilot to follow orders, with redesigned orders (attack, defend, go to a point) and new inputs that show which enemies threaten what it guards. Pulling its choices toward a hand-written pilot only while it travels taught it to follow, but again wrecked its fighting: it won 2 % of carrier battles against the old pilot. Without the pull it kept its strength but followed orders only a little better than with its orders hidden from it. -->

Each side in this game has a commander that gives its ships orders, and the game's
design needs pilots that carry them out. Two earlier runs had found a split. A pilot
pulled during training toward the choices of a hand-written pilot follows orders but
forgets how to fight. A pilot left to learn from its rewards alone fights well but
ignores orders. This run redesigned the orders, showed the pilot more about the ships
around it, and used the pull only while the pilot is travelling to its order, never in
a fight. The split came back. With the pull, the pilot follows and loses nearly every
carrier battle. Without it, the pilot stays strong and follows only a little, mostly on
orders to fly to a point.

Verdict: **FAIL.** No version of the pilot both follows its orders and keeps its
fighting strength.

## Where this fits

RL Fighter is a space-combat game where every small ship is flown by a neural network,
the **pilot**, that learned to fly by trial and error. The project's website plays
matches forever on its front page, the **live page**. Besides team deathmatch (small
ships only, 1 to 4 a side, until one side is destroyed) there are two missions. In a
**carrier battle** each side has a carrier that launches its strike craft, and a side
wins by destroying the enemy carrier. In a **convoy escort** one side's escorts guard
freighters flying to a jump point and the other side attacks, winning if it destroys at
least half of them. Each side's **commander** splits its ships into squads and gives
each squad an order. [Fleet pilot v1](../2026-10-30-fleet-pilot/results.md), then the
live pilot, cannot see orders.

The [first order-pilot run](../2026-10-31-order-pilot/results.md) showed pilots their
orders and paid them a little for following. Its best saved copy, `w1_400` (the arm
with order reward weight 1, saved at training update 400), won 0.79 of carrier battles
against v1 but barely followed. The [second run,
B2b](../2026-10-31-order-pilot-b2b/results.md), added a **script pull**: a training
term that pulls the pilot's choices toward those of the hand-written pilot ("the
script", called the **teacher** when it is used this way). It followed at the teacher's
level and won 0 to 4 % of carrier battles, because most moments with an order were
moments in a fight.

A design review then changed three things.

- **The orders.** **Attack** names an enemy. **Defend** names a friendly ship to
  protect, the **ward**. A defender is paid for damage to the ward's **threat set**:
  the enemies close enough to hit the ward with their own weapons, or that hit it
  recently. It is charged when the ward takes damage. **Go-to** names a point, and the
  order is done once the ship arrives.
- **What the pilot sees.** For each nearby ship, its type, its weapon range, its
  distance to the order point and whether it hit the ward recently, plus the five ships
  nearest the order point. That takes the pilot's inputs from 403 numbers to 583.
- **Where the pull applies.** Training data is made of **rows**: one ship's view and
  choice at one moment. The pull now applies only to **transit rows**, moments when a
  ship is on its way to a go-to point or defending a ward no one is threatening.

<!-- figure-idea: shared: what an order is, with the three kinds of this rules version. Attack (a line to a named enemy), defend (a ward with its threat set drawn as the enemies whose weapon range reaches it), go-to (a point and its arrival circle). Marks which moments count as "transit", the only ones the pull touched. -->

## What ran

- Two **arms** (versions of the experiment trained side by side, identical but for one
  setting), both from run 1's `w1_400`, with its inputs widened from 403 to 583.
  - `transit`: the script pull on transit rows, at strength β 0.05 falling to 0.
  - `reward`: no pull, so only the reward and the new inputs teach following.
- In both, the new inputs started at zero weight, so at the start each arm flies
  exactly like `w1_400`. They learned at 3× the rate of the rest of the network (the
  plan said 10×, and this was lowered before launch). The order reward counted at
  weight 1 beside the reward for fighting and winning. Opponents included frozen copies
  of v1 and `w1_400`.
- A **KL anchor** held each arm near `w1_400` at moments with no order. KL measures how
  far one network's choices have moved from another's (0 is identical), and the anchor
  is a training term that penalises moving too far.
- 300 updates each (an update is a batch of matches played, then one adjustment of the
  network), run concurrently 09:44–11:42 (about 23 s per update). Baseline 09:31–09:44,
  gate evals 11:42–14:07.

## How following was measured

- **Shown and hidden.** Each pilot flies the same matches twice, once with its orders
  and once with them **hidden by the sim** (it gets no order inputs at all). The
  difference is what seeing orders changes. "Hidden" below always means that pilot's
  own score with its orders hidden.
- **Two commanders.** The **random commander** hands out random orders, to test
  following any order. The **scripted commander** is the hand-written one the game uses,
  which gives sensible orders. The gates are judged under the random one.
- **Three measures.** "Attack share": the share of a ship's damage under an attack order
  that lands on its target. "Threat share": the share of a defender's damage that lands
  on its ward's threat set. "Go-to in time": the share of go-to orders reached within
  1.5 × (distance / top speed + 60 ticks), a tick being 1/30 s. Also "defend hull lost":
  the share of the ward's hull lost per minute it is defended.
- **The teacher-first rule.** The teacher was measured first. Any bar it could not
  reach itself was replaced, before any candidate was measured, by one set from its own
  score.

The plan fixed the pass marks ("gates") before any candidate was measured:

| gate | what it checks | pass mark |
|---|---|---|
| O, following | attack share, threat share, go-to in time, defend hull lost, under the random commander | attack and threat share ≥ hidden + 0.05, go-to ≥ 0.7, defend hull lost ≤ 0.62 a minute (set from the teacher, see below) |
| M, missions | mission win rate against v1 and against `w1_400` | against v1 ≥ 0.47 in each mission and ≥ 0.52 on average, against `w1_400` ≥ 0.45 on average |
| D, deathmatch | win rate in the standard deathmatch lineups | ≥ 0.85 against the script, ≥ 0.45 against v1 |
| H, health | matches end normally | as in run 1; every candidate met it |

The teacher scores 0.470 / 0.650 / 0.898 on attack share, threat share and go-to in
time. The plan's defend bar was "a ward loses at most 0.8 × what it loses with the
pilot's orders hidden", which for `w1_400` comes to 0.39 of the hull a minute (0.8 ×
0.49). The teacher's wards lose 0.59, more than `w1_400`'s 0.49, so the teacher could
not meet the bar and it was replaced by 0.62 (the teacher's 0.59 × 1.05). A pilot that
fights well protects its ward better than one that stations by it.

<!-- figure-idea: the paired eval: the same match flown twice side by side, once with the pilot shown its order and once with the order hidden, the difference in where the ship goes highlighted. Helps the reader see what "followed vs hidden" measures, which this entry's numbers all rest on. -->

## Verdict in detail

No candidate passes every gate. The two arms fail in opposite ways:
- `transit` (script pull on transit rows, β 0.05 → 0): follows (threat-set share 0.58,
  go-to in time 0.66, attack share 0.51) but wins 0.2–5 % of carrier battles against v1.
- `reward` (no pull): keeps its strength (mission win vs v1 0.70–0.73, vs w1_400
  0.43–0.53; deathmatch win 0.90 against the script and 0.54–0.61 against v1) but
  follows little better than with its orders hidden.

The carrier figures are per mission, from `eval/<candidate>_missions_vs_v1.md`. The
gates table below shows only the mean of the two missions. Against v1, the `transit`
copies win 0.002 to 0.050 of carrier battles but 0.44 to 0.59 of convoys, and the
`reward` copies 0.70 to 0.76 of carrier battles and 0.68 to 0.72 of convoys.

## Gates (from `eval/gates.md`; random commander unless noted)

Each row is a **candidate**: one arm saved at one update (`reward_150` is the `reward`
arm at update 150). ✓ is a gate met and ✗ not. "Mission win vs v1" is the mean share of
carrier battles and convoys won against v1, and "vs w1_400" the same against run 1's
best, where 0.5 is even. "Defend hull lost" is per minute defended. The last two
columns are deathmatch win rates against the script and against v1.

| candidate | O | M | D | mission win vs v1 | vs w1_400 | attack share | defend hull lost | threat share | go-to in time | dm vs script | dm vs v1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| reward_150 | ✗ | ✓ | ✓ | 0.719 | 0.486 | 0.409 | 0.530 | 0.345 | 0.487 | 0.905 | 0.593 |
| reward_300 | ✗ | ✓ | ✓ | 0.726 | 0.531 | 0.389 | 0.523 | 0.366 | 0.514 | 0.900 | 0.613 |
| transit_150 | ✗ | ✗ | ✗ | 0.255 | 0.140 | 0.510 | 0.538 | 0.579 | 0.667 | 0.681 | 0.305 |
| transit_300 | ✗ | ✗ | ✗ | 0.305 | 0.186 | 0.512 | 0.479 | 0.584 | 0.662 | 0.744 | 0.350 |

Every candidate in `eval/gates.md` meets the defend hull-lost bar. The `reward` arm
fails O on attack share, threat share and go-to. `transit` fails O only on go-to (0.53 to
0.68 against 0.7) and fails M and D by a wide margin.

`reward_300` with its orders vs hidden: go-to in time 0.514 vs 0.393, threat share
0.366 vs 0.342, attack share 0.389 vs 0.404, attack close (median ticks to reach gun
range) 64 vs 78 ticks. Go-to is the only order it reads clearly. Under the scripted
commander, `w1_400` and the `reward` arm reach almost no go-to in time (0.05–0.07,
against the teacher's 0.86 and the `transit` arm's 0.47–0.66). This run did not look
into why.

## Why

- **The pull wrecks aiming, because movement is aiming.** The pull covers only the
  thruster and power controls. But fighters and strafers have guns fixed to the nose,
  which aim by turning the ship, and the thrusters turn it. On 13–15 % of rows
  (`beta_rows_share`), β 0.05 was enough: by update 50, carrier-battle fighters went
  from 61 to 9 damage, hit rate 0.26 → 0.08, fire share (the share of moments they
  pulled a trigger) 0.66 → 0.38. On rows with an order, the `transit` arm's KL from
  `w1_400` reached 2.3, against 0.6 for the `reward` arm: its choices had moved several
  times as far. B2b (pull on 67 % of rows) and B3 (13 %) fail the same way. The row
  filter was not the problem.
- **Without the pull, 300 updates move following only a little.** Go-to improves
  steadily (0.45 → 0.51 over the run, against 0.39 hidden); defend and attack do not.
  The per-update change in the pilot's choices (approx_kl) stayed at 0.005–0.007 with
  the new inputs at 3×, well under the 0.05 the plan treats as too fast, so the new
  inputs could be stepped faster.

## Next (proposed)

- **Drop the script pull for strike craft.** Two runs agree; it is not a tuning issue.
- **Continue the `reward` arm** from `reward_300`: it is as strong as w1_400 in
  missions and improving on go-to. Options for the next night: more updates (600), the
  new-input step at 10× (the reward arm's approx_kl leaves room the transit probe did
  not), and a larger order reward weight for defend and go-to.
- **Decide what "following" must look like on screen.** The teacher's defend is worse
  for the ward than w1_400's fighting. Gate O judges defending two ways: how much hull
  the ward loses, and how much of the defender's damage goes to the ward's threats.
  Only the first should count, measured against the same pilot with its orders hidden
  (as the plan's version of that bar does). The threat-share bar should go.
