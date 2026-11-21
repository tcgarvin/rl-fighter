# Order drills: dockkite_final_2286

**Gate: fail.** dockkite_final_2286 failed the drill gate: defend_more_on_named.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2286.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.82 +/- 0.02 (463/567) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.02 (260/311; 23 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.02 (42/297; 37 killed first, not counted)
- Lift from seeing the order: +0.69
- Near: 0.75 +/- 0.03 (130/173; 7 killed first, not counted)
- Far: 0.94 +/- 0.02 (130/138; 16 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.03 (151/179; 13 killed first, not counted)
- Deadline in the order: 0.88 (191/218)
- No deadline (judged by 2x + 10 s): 0.74 (69/93)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.79 (41/52) |
| medium (2.5 to 4.5) | 0.89 (90/101) |
| loose (over 4.5) | 0.92 (60/65) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 311 | 218 | 93 | 20 |
| In time | 0.84 | 0.88 | 0.74 | 0.65 |
| Near miss (within 60 m) | 0.13 | 0.11 | 0.19 | 0.30 |
| At the enemy instead | 0.03 | 0.02 | 0.05 | 0.05 |
| Neither | 0.00 | 0.00 | 0.01 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.96 +/- 0.01 (245/256)
- Swap test, flipped, groups busy with a freighter: 0.88 +/- 0.03 (84/96)
- Swap test, flipped, groups flying at the pilots: 0.59 +/- 0.09 (19/32)
- Damage on the named target per pilot: 62.1 +/- 4.4 (n=256)
- On other enemies per pilot (not judged): 45.3 +/- 3.6 (n=256)
- Chose the named side: 0.89 +/- 0.02 (228/256)
- Chose the other side: 0.07 +/- 0.02 (18/256)
- Chose neither: 0.04 +/- 0.01 (10/256)
- Swap test, flipped with the order: 0.80 +/- 0.04 (103/128)
- Swap test, one side whatever was named: 0.12 +/- 0.03 (15/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.02 (213/256)
- On the named ward's attackers per pilot: 76.9 +/- 4.4 (n=256)
- On the other's per pilot: 12.7 +/- 1.4 (n=256)
- Chose the named side: 0.88 +/- 0.02 (226/256)
- Chose the other side: 0.04 +/- 0.01 (9/256)
- Chose neither: 0.08 +/- 0.02 (21/256)
- Swap test, flipped with the order: 0.78 +/- 0.04 (100/128)
- Swap test, one side whatever was named: 0.07 +/- 0.02 (9/128)

## Dock, alone (128 drills)

- Docked: 0.44 +/- 0.04 (56/128)
- Shot down first: 0.16 +/- 0.03 (21/128)
- Out of time: 0.40 +/- 0.04 (51/128)
- Docked, of those not shot down: 0.52 +/- 0.05 (56/107)
- Came within 30 m of the dock point: 0.70 +/- 0.04 (90/128); of those, docked: 0.62 +/- 0.05 (56/90)
- Closest approach: median 19 m (10th to 90th percentile 4 to 64 m)
- Time from the order to the dock: median 15.4 s (10th to 90th percentile 8.6 to 23.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.02 (11/128)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.02 (n=56)
- Damage dealt per drill: 3.8 +/- 2.2 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.44

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.48 (29/60) | 0.08 |
| station | 0.52 (16/31) | 0.26 |
| citadel | 0.30 (11/37) | 0.22 |
| fighter | 0.45 (14/31) | 0.35 |
| strafer | 0.62 (21/34) | 0.24 |
| gunship | 0.53 (17/32) | 0.03 |
| bomber | 0.13 (4/31) | 0.03 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.17 +/- 0.03 (22/128)
- Shot down first: 0.44 +/- 0.04 (56/128)
- Out of time: 0.39 +/- 0.04 (50/128)
- Docked, of those not shot down: 0.31 +/- 0.05 (22/72)
- Came within 30 m of the dock point: 0.35 +/- 0.04 (45/128); of those, docked: 0.49 +/- 0.07 (22/45)
- Closest approach: median 47 m (10th to 90th percentile 8 to 212 m)
- Time from the order to the dock: median 17.4 s (10th to 90th percentile 9.4 to 32.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.07 +/- 0.02 (9/128)
- Hull at the dock (fraction of its maximum): 0.24 +/- 0.03 (n=22)
- Damage dealt per drill: 47.3 +/- 7.5 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.16

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.19 (12/64) | 0.47 |
| station | 0.15 (5/34) | 0.41 |
| citadel | 0.17 (5/30) | 0.40 |
| fighter | 0.04 (1/27) | 0.74 |
| strafer | 0.23 (6/26) | 0.65 |
| gunship | 0.31 (12/39) | 0.10 |
| bomber | 0.08 (3/36) | 0.42 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.836 | met |
| goto_lift | 0.695 | met |
| attack_target_hit | 0.957 | met |
| attack_side | 0.891 | met |
| attack_flip | 0.805 | met |
| defend_more_on_named | 0.832 | failed |
| defend_side | 0.883 | met |
| defend_flip | 0.781 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.438 | unset |
| dock_calm_lift | 0.438 | unset |
| dock_threat_docked | 0.172 | unset |
| dock_threat_docked_of_survivors | 0.306 | unset |
