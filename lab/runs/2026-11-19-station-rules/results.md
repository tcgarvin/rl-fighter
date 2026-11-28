# Station assault: hand rules beat no orders through launches and the carrier, not orders

We asked whether a simple hand-written commander could beat a side that gives no orders
in [the station assault](../2026-11-19-station-bomber/results.md), the mission added the
same night, in which one side defends a space station and the other attacks it with a
carrier and its strike craft (the small piloted ships). Yes, by a lot, in both roles,
and neither rule that does it gives a strike craft an order. On defence, keeping the
station's reserve ships docked until its hull falls below 60% raises the defender's win
rate from 0.56 to 0.75 (+0.19 ± 0.04, where ± is the margin of error). Launching them only when the main wave arrives
gives +0.14. On attack, bringing the carrier to 170 m of the station once its hangar is
empty raises the attacker's win rate from 0.44 to 0.57 (+0.13 ± 0.04), mostly by turning
matches that would have run out the 150 s clock, which the defender wins, into station
kills. Every rule that does order strike craft (go-to, defend, attack, and the script
itself) is level with no orders or worse, by 0.03 to 0.17 in win rate.

The networks were trained before the station assault existed, so the sim presents it to
them as a mission they know, a carrier battle or a convoy escort. Presenting it as a
convoy escort (the convoy reading) instead of a carrier battle gives the same answer.
`SIM_VERSION` 9 (the ninth version of the game's rules); no sim change.

<!-- summary: We asked whether a simple hand-written commander could beat a side that gives no orders in the new station assault. It can, by a lot, but only through the two decisions that are not orders: when the station launches its reserve ships, and where the attacker parks its carrier. Every rule that told the fighters what to do lost ground, as in fleet fights, so a commander trained on this mission has real decisions to learn, and its orders to pilots are not yet among them. -->

## Where this fits

RL Fighter is a space-combat game in which every small ship (a strike craft) is flown by
a neural network, a pilot, that learned by trial and error. Each side also has a
commander that gives its ships orders and directs its big ships, which scripts fly: when
to launch craft from the bays, and where the carrier steers. In fleet fights, orders had only cost:
[commander 3](../2026-11-15-commander-3/results.md) found that a side whose pilots get
no orders beats every commander we had, [the order-cost
night](../2026-11-17-order-cost/results.md) found that an ordered pilot charges its target
and loses the duel, and [order kinds](../2026-11-19-order-kinds/results.md), the same
night as this entry, found a go-to costs a fifth of what an attack order does. The
station assault was built that night to give a commander decisions that matter. Before
training a commander on it, we wanted to know whether any decision there is worth
anything: if no hand rule beats no orders, a learned commander has nothing to find. The
[station commander](../2026-11-19-station-commander/results.md) run then tried to learn
what these rules found.

<div data-figure="diagram" data-name="missions" data-caption="This entry plays the station assault, bottom right, under rules version 9, with the first station and no dreadnought. The decisions that paid were when the station launches its reserve and where the attacker parks its carrier."></div>

<!-- figure-idea: shared: what a commander controls: orders to each strike craft (attack, defend, go-to) on one side, and the capital-ship decisions (when the bays launch, where the carrier steers) on the other; this entry's whole result is that split. -->

## The setup

The setup is the station assault with the live pilots. Every strike craft is flown by a
pilot from `lab/live_pilots.json` (the ten trained pilots the live page draws from),
drawn at random for each ship in each match, as on the live page. Capital ships are
flown by the sim's scripts. The roster is the default "strike of 8". The station has 2
picket ships already out guarding it and 4 in reserve inside: fighters, strafers and one
gunship (fighters and strafers aim their guns by pointing the ship; the slower gunship
has turrets that aim themselves). The attacker's carrier brings 3 strike craft that jump
in, appearing at speed early in the match (the jump-in trio: fighter, bomber, fighter),
and 5 docked, 3 of them bombers (slow strike craft with a torpedo fixed to the nose).

One side is commanded by a **rule**, through the sim's external commander, the hook that
lets a program outside the sim command a side. The other side is `unseen`: the scripted
commander with its orders hidden from its own pilots, as in every "no orders"
measurement since [2026-11-15](../2026-11-15-commander-3/results.md). An external
commander has to launch and steer its carrier itself. `station_rules.py` copies the
script's station logistics (launches and the attacker carrier's waypoint, without the
script's squads, its groups of ships that share an order), so the rule `none` launches
exactly as `unseen` does. On 96 matches per role, `none` reproduces the script-hidden
baseline match for match. So `none` is the baseline row in every table: unseen against
unseen.

As in the station assault entry, the networks see the mission either as a carrier
battle, each side with a carrier (the **carrier** reading), or as a convoy escort with
the station's side as the defending escort (the **convoy** reading). Each cell (one
rule, one role, one reading) on the carrier reading is 1,024 matches, and each on the
convoy reading is 512 (the station's side reads as a convoy defender,
`docs/COMMANDER.md`). Every cell plays the same seeds, rosters and pilot draws. The ± is
the margin of error: the true value very likely lies within that range (1.96 standard
errors). Deltas are paired match by match against `none`. Orders change the matches
early, and the pilots' random choices then diverge, so pairing narrows the interval very
little.

## The rules

Each rule is a small hand-written commander for one side. The table gives which side it
commands, what it does and why we tried it. The order kinds are go-to (fly to a point),
defend (stay near a friendly ship and protect it) and attack (go after a named enemy). A
ship under no order is "free" and flies on its own judgment. Flak is the anti-craft guns
of the capital ships. A commander acts on its slow tick, every 2 s.

| Rule | Side | What it does | Why |
|---|---|---|---|
| `none` | either | The script's launches and carrier waypoint, no orders | The baseline: launches like `unseen` |
| `scripted` | either | The sim's script, its orders shown to its pilots | Its orders cost pilots 0.12 to 0.23 here ([the station run](../2026-11-19-station-bomber/results.md)) |
| `rally_release` | attacker | Whole wing (and each later launch) one squad: go-to 320 m from the station on the line to the carrier, radius 60 m, with a deadline (rules version 8: 2 × the slowest ship's straight-line time + 3 s). Free on arrival or a miss | The turrets punish a wing that arrives piecemeal. A go-to is the cheap order ([0.08 in a 3 v 3](../2026-11-19-order-kinds/results.md)), and its arrival edge, 260 m out, is outside the 230 m flak |
| `bomber_only` | attacker | Bombers only: go-to 180 m from the station (arrival edge at the torpedo's 240 m range), deadline, then free. Nobody else ordered | The bombers are what kills the station when the script flies them (52% of its damage) |
| `escort_bombers` | attacker | `bomber_only`, plus the gunship defends the lead bomber (nearest the station, kept until it is gone). Fighters and strafers free | Defend wins gunship fights (+0.17 to +0.29) and loses fighter and strafer fights |
| `carrier_push` | attacker | No orders. Once the hangar is empty (t = 6 s), the carrier's waypoint is 170 m short of the station (the script's carrier-battle standoff, the distance it holds from its target, inside both sides' flak) instead of its patrol 430 m out | Added after the first smoke runs (small trial runs): the carrier deals about a fifth of the station's damage under the patrol, and once its hangar is empty it is a gun platform whose loss does not end the match |
| `hold_reserve` | defender | No orders. Launch nothing until 4 attacking strike craft are within 320 m of the station (the main wave; the jump-in trio is 3), then every bay every slow tick | See below: the script launches at once |
| `hold_late` | defender | No orders. Launch nothing until the station's hull is below 60%, then every bay | The latest launch that still uses the reserve |
| `hold_never` | defender | No orders, no launches: the picket alone | Added after `hold_late`: what the reserve is worth at all |
| `intercept_bombers` | defender | The script's launches. The gunship defends the station; everyone else free | Gunships gain from defend, the others lose |
| `hunt_bombers` | defender | `intercept_bombers`, plus fighters and strafers attack the bomber nearest the station once one is within 320 m (kept until it dies) | The script's interceptor arm, restricted to the ships that are close |

**Launches.** `unseen` launches as the script does. For the attacker that means every
bay every slow tick until the hangar is empty, which is the right call when only the
attacker can lose to the clock. The defender keeps 3 strike craft out and scrambles
every bay while any attacking strike craft is within 320 m of the station. The
attacker's jump-in trio arrives about 390 m out at 1.4 times
its speed cap and is inside 320 m by t = 2 s. So the script empties the station's hangar
in the first 4 s of every match, into those three ships. The defender's launch rules
change only that timing.

## Results

### Carrier reading (1,024 matches a cell)

"Attacker win" is the share of matches the attacker won. "Rule side's score" is the same
for whichever side the rule commands (a draw counts half). "vs `none`" is how much the
rule changes that score against the no-orders baseline, paired match by match. The end
columns are the shares of matches ending with the station destroyed, the assault
repelled, or the clock, and "Median s" is the median match length in seconds.

| Rule | Attacker win | Rule side's score | vs `none` (paired) | End: station / repelled / clock | Median s |
|---|---|---|---|---|---|
| **Attacker** | | | | | |
| `none` | 0.436 ± 0.030 | 0.436 | | 0.44 / 0.43 / 0.13 | 94 |
| `scripted` | 0.268 ± 0.027 | 0.268 | −0.168 ± 0.038 | 0.27 / 0.66 / 0.07 | 88 |
| `rally_release` | 0.397 ± 0.030 | 0.397 | −0.038 ± 0.041 | 0.40 / 0.47 / 0.13 | 96 |
| `bomber_only` | 0.402 ± 0.030 | 0.402 | −0.033 ± 0.041 | 0.40 / 0.45 / 0.14 | 97 |
| `escort_bombers` | 0.346 ± 0.029 | 0.346 | −0.090 ± 0.041 | 0.35 / 0.49 / 0.16 | 97 |
| `carrier_push` | 0.565 ± 0.030 | 0.565 | **+0.130 ± 0.038** | 0.57 / 0.43 / 0.01 | 71 |
| **Defender** | | | | | |
| `none` | 0.436 ± 0.030 | 0.564 | | 0.44 / 0.43 / 0.13 | 94 |
| `scripted` | 0.550 ± 0.030 | 0.450 | −0.114 ± 0.042 | 0.55 / 0.26 / 0.19 | 110 |
| `hold_reserve` | 0.296 ± 0.028 | 0.704 | **+0.140 ± 0.039** | 0.30 / 0.57 / 0.14 | 100 |
| `hold_late` | 0.251 ± 0.027 | 0.749 | **+0.185 ± 0.039** | 0.25 / 0.67 / 0.08 | 101 |
| `hold_never` | 0.925 ± 0.016 | 0.075 | −0.489 ± 0.034 | 0.92 / 0.00 / 0.07 | 56 |
| `intercept_bombers` | 0.467 ± 0.031 | 0.533 | −0.031 ± 0.038 | 0.47 / 0.37 / 0.16 | 106 |
| `hunt_bombers` | 0.554 ± 0.030 | 0.446 | −0.118 ± 0.040 | 0.55 / 0.27 / 0.18 | 111 |

### Convoy reading (512 matches a cell)

The same columns, on the convoy reading, for the rules that mattered most.

| Rule | Attacker win | Rule side's score | vs `none` (paired) | End: station / repelled / clock |
|---|---|---|---|---|
| `none` | 0.426 ± 0.043 | (0.426 / 0.574) | | 0.43 / 0.44 / 0.14 |
| attacker `scripted` | 0.234 ± 0.037 | 0.234 | −0.191 ± 0.052 | 0.23 / 0.71 / 0.05 |
| attacker `carrier_push` | 0.570 ± 0.043 | 0.570 | **+0.145 ± 0.054** | 0.57 / 0.42 / 0.01 |
| defender `scripted` | 0.551 ± 0.043 | 0.449 | −0.125 ± 0.057 | 0.55 / 0.24 / 0.21 |
| defender `hold_late` | 0.223 ± 0.036 | 0.777 | **+0.203 ± 0.053** | 0.22 / 0.71 / 0.07 |

The two readings agree within their noise on every rule measured on both.

### Telemetry (carrier reading)

Station damage counts hull and shield, summed over the match. "Under an order" is the
share of the rule side's strike-craft seconds with an effective order. Go-to counts are
ships (8 a match for the rally, 3 for the bombers) that arrived, missed the deadline,
or neither.

| Rule | Torpedo hit the station (share of matches) | First torpedo hit, median s | Station damage: all / by bombers | Station hull at 45 s | Rule side under an order | Go-to: arrived / missed |
|---|---|---|---|---|---|---|
| `none` | 0.42 | 28 | 1,558 / 77 | 0.79 | (0.98, hidden) | |
| attacker `scripted` | 0.46 | 29 | 1,239 / 91 | 0.84 | 0.97 | |
| `rally_release` | 0.45 | 24 | 1,519 / 90 | 0.78 | 0.11 | 0.46 / 0.54 |
| `bomber_only` | 0.43 | 25 | 1,547 / 86 | 0.77 | 0.14 | 0.19 / 0.79 |
| `escort_bombers` | 0.43 | 27 | 1,433 / 86 | 0.80 | 0.29 | 0.18 / 0.80 |
| `carrier_push` | 0.42 | 26 | 1,522 / 80 | 0.78 | 0 | |
| defender `hold_reserve` | 0.39 | 29 | 1,385 / 79 | 0.83 | 0 | |
| defender `hold_late` | 0.55 | 39 | 1,567 / 117 | 0.48 | 0 | |
| defender `hold_never` | 0.38 | 27 | 1,940 / 73 | 0.36 | 0 | |

Over time, means over the matches still running. Each cell gives: station hull ·
attacking strike craft alive · defending strike craft alive (out and docked) · share of
matches still running.

| Rule | 10 s | 20 s | 30 s | 45 s | 60 s | 90 s |
|---|---|---|---|---|---|---|
| `none` | 1.00 · 7.8 · 5.7 · 1.00 | 0.99 · 6.5 · 4.3 · 1.00 | 0.93 · 4.9 · 3.0 · 1.00 | 0.79 · 2.9 · 1.7 · 1.00 | 0.67 · 1.9 · 1.0 · 0.90 | 0.57 · 0.7 · 0.3 · 0.53 |
| `carrier_push` | 1.00 · 7.8 · 5.7 · 1.00 | 0.99 · 6.5 · 4.2 · 1.00 | 0.92 · 5.0 · 3.0 · 1.00 | 0.78 · 3.0 · 1.7 · 1.00 | 0.60 · 1.9 · 1.0 · 0.82 | 0.40 · 1.1 · 0.5 · 0.17 |
| `hold_reserve` | 1.00 · 7.9 · 5.8 · 1.00 | 0.99 · 6.6 · 4.8 · 1.00 | 0.94 · 4.9 · 3.5 · 1.00 | 0.83 · 2.8 · 2.1 · 1.00 | 0.74 · 1.6 · 1.4 · 0.95 | 0.65 · 0.6 · 0.5 · 0.59 |
| `hold_late` | 1.00 · 7.9 · 5.8 · 1.00 | 0.89 · 7.1 · 5.4 · 1.00 | 0.65 · 6.0 · 4.8 · 1.00 | 0.48 · 4.1 · 3.8 · 1.00 | 0.41 · 2.2 · 2.9 · 0.96 | 0.38 · 0.5 · 1.8 · 0.67 |
| `hold_never` | 1.00 · 7.9 · 5.8 · 1.00 | 0.89 · 7.1 · 5.4 · 1.00 | 0.63 · 6.1 · 4.8 · 1.00 | 0.36 · 4.7 · 4.4 · 0.82 | 0.30 · 3.5 · 4.2 · 0.40 | 0.28 · 1.5 · 4.1 · 0.19 |

The carrier under `carrier_push` is 396 m from the station at 20 s, 237 m at 45 s and
163 m at 90 s. Under the patrol it stays 420 to 460 m out until the wing is spent. The
full tables, including every rule's over-time row and the counts at 20 s, are in
`tables.md`.

What this says:

1. **Orders to strike craft do not pay, on either side.** The cheapest orders are a
   one-off go-to to a rally point (−0.04) or bombers only to a standoff point (−0.03),
   both level with no orders. Every defend or attack order costs more: the gunship
   defending the lead bomber costs 0.06 on top of `bomber_only`. The fighters' and
   strafers' attacks on the nearest bomber (`hunt_bombers`) add 0.09 to
   `intercept_bombers`' 0.03, and the script's orders cost 0.11 to 0.19. These pilots
   barely follow a go-to here: 46% reach the rally, and only 19% of bombers reach their
   standoff point before the deadline. The bombers barely use the torpedo either (it lands in about 0.4 of
   matches, around 80 damage of ~1,550), so no rule about the bombers changes much.
2. **The attacker's carrier is a weapon the patrol leaves unused.** Sent to 170 m at
   t = 6 s, it is 237 m out at 45 s and 205 m at 60 s, and from then on the station's
   hull falls faster (0.40 at 90 s against 0.57). Clock endings drop from 0.13 to 0.01: the matches that
   ran out the clock become station kills. Repelled assaults stay at 0.43, so the push
   does not lose the carrier's side more matches. The median match is 23 s shorter.
3. **The defender's reserve is worth most if it comes out late.** Never launching it
   loses almost every match (0.075). Launching it into the jump-in trio at t = 2 to 4 s,
   as the script does, scores 0.56. Launching it once the main wave is inside 320 m
   scores 0.70. Launching it when the station is down to 60% hull scores 0.75. Under
   `hold_late` the picket and the station's turrets take the first 30 to 45 s alone.
   The station loses hull faster (0.48 at 45 s against 0.79), and more attackers are
   still alive then (4.1 against 2.9). But they have spent half their wing on the
   turrets, and four fresh defenders launch into what is left. The
   defending gunship survives 0.75 of matches under `hold_late` against 0.32. Most of
   those wins are assaults repelled (0.67 against 0.43), not the clock (0.08).

<!-- figure-idea: the defender's launch timing as a timeline with its payoff: never launch (0.075), launch at once into the jump-in trio (0.56), on the main wave (0.70), at 60% hull (0.75); makes the "late is best, never is worst" shape visible at a glance. -->

## What we learned

- **A hand rule beats no orders, by 0.13 to 0.20 in win rate, in both roles.** The
  defender gains most by timing its launches (`hold_late` +0.19 ± 0.04, `hold_reserve`
  +0.14). The attacker gains by moving its carrier (`carrier_push` +0.13 ± 0.04, +0.15
  on the convoy reading). These are the station assault's biggest effects of any
  commander decision we have measured, about as large as hiding the script's orders
  (0.12 to 0.23).
- **None of it is an order to a pilot.** Every strike-craft order rule is level or
  worse, as in [fleet fights](../2026-11-19-order-kinds/results.md). The hull split
  that made defend pay for gunships there does not help here: the one gunship defending
  a bomber costs 0.06, and the one gunship defending the station costs 0.03.
- **So the mission gives a commander something to learn, in its launch and waypoint
  heads** (the parts of its network that choose launches and where its carrier goes). A
  learned commander can see what these rules use: the station's hull fraction (entity
  feature 14, one of its inputs), every enemy's position, and the hangar counts. One of
  the points its waypoint head can pick, the arena's centre, is about 157 m from the
  station, close to the 170 m standoff. Launch timing has a steep payoff that is not
  monotone, that is, it does not simply rise the later the launch (never −0.49, at once
  0, on the main wave +0.14, at 60% hull +0.19), which a policy-gradient learner (one
  trained by trial and error, as ours are) should find. Two cautions. Against the
  `unseen` side among its training opponents, a commander that learns these will also
  have to learn to give almost no strike-craft orders, as the [phase-3
  commanders](../2026-11-15-commander-3/results.md) did. And a bomber reads as the gunship class, so no commander can tell bombers apart
  yet.
- **The script's own logistics are beatable, and cheaply.** Its defender empties the
  hangar into the jump-in trio, and its attacking carrier stays out of reach until the
  wing is gone. These are hand-tunable, but changing them changes the script-against-
  script balance (0.55) and WAR's replacement level (the script is the zero point of
  WAR, wins above replacement, our rating of pilots), so it is a separate decision.
- **Not measured:** the threshold sweep for `hold_late` (only 0.6 was tried), a push to
  other standoff distances, both winning rules on opposite sides of one match, and
  scripted pilots (they read the script's orders, so the rules here would change their
  flying too).

## Files

The record of how to rerun this; a reader can skip it.

- `station_rules.py`: the eval (`rlf.lab.station_rules/1`), the rules and the port of
  the script's station logistics. It reuses `PilotPool` from
  `../2026-11-19-station-bomber/station_eval.py`.
- `run.sh`: reproduces `out/`, with six single-thread chains under `nice -n 19`. A cell
  of 1,024 matches takes about 27 minutes on one core, and inference is about 90% of
  that. The second round (`hold_never`, the size-matched baseline `checksmall`, the
  convoy cells) was started by hand with the same cell commands, after the first round
  had been launched by the earlier version of the script.
- `out/<as>_<role>_<rule>.json`: each cell's summary and per-match arrays (winner,
  reason, end tick, station damage, first torpedo, first contact); `out/*.log` are the
  chain logs.
- `analyze.py`: prints `tables.md` (all tables, over-time rows per rule, and the
  `none` against `unseen` identity check).
