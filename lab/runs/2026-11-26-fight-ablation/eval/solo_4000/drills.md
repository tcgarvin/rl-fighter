# Order drills: solo_4000

**Gate: pass.** solo_4000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.84 +/- 0.02 (226/268) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.81 +/- 0.03 (113/140; 13 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.03 (19/133; 20 killed first, not counted)
- Lift from seeing the order: +0.66
- Near: 0.79 +/- 0.05 (58/73; 6 killed first, not counted)
- Far: 0.82 +/- 0.05 (55/67; 7 killed first, not counted)
- Enemies around the route: 0.73 +/- 0.05 (55/75; 10 killed first, not counted)
- Deadline in the order: 0.84 (77/92)
- No deadline (judged by 2x + 10 s): 0.75 (36/48)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.68 (17/25) |
| medium (2.5 to 4.5) | 0.87 (33/38) |
| loose (over 4.5) | 0.93 (27/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 140 | 92 | 48 | 12 |
| In time | 0.81 | 0.84 | 0.75 | 0.83 |
| Near miss (within 60 m) | 0.15 | 0.14 | 0.17 | 0.00 |
| At the enemy instead | 0.04 | 0.02 | 0.08 | 0.17 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (120/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 56.3 +/- 6.0 (n=128)
- On other enemies per pilot (not judged): 33.4 +/- 3.8 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.90 +/- 0.03 (115/128)
- On the named ward's attackers per pilot: 76.8 +/- 6.1 (n=128)
- On the other's per pilot: 5.2 +/- 1.4 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.58 +/- 0.06 (37/64)
- Shot down first: 0.16 +/- 0.05 (10/64)
- Out of time: 0.27 +/- 0.06 (17/64)
- Docked, of those not shot down: 0.69 +/- 0.06 (37/54)
- Came within 30 m of the dock point: 0.78 +/- 0.05 (50/64); of those, docked: 0.74 +/- 0.06 (37/50)
- Closest approach: median 10 m (10th to 90th percentile 1 to 43 m)
- Time from the order to the dock: median 12.7 s (10th to 90th percentile 8.1 to 21.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.12 +/- 0.04 (8/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=37)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.55

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.62 (20/32) | 0.09 |
| station | 0.60 (9/15) | 0.13 |
| citadel | 0.47 (8/17) | 0.29 |
| fighter | 0.79 (11/14) | 0.07 |
| strafer | 0.47 (9/19) | 0.42 |
| gunship | 0.67 (10/15) | 0.00 |
| bomber | 0.44 (7/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.28 +/- 0.06 (18/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.34 +/- 0.06 (22/64)
- Docked, of those not shot down: 0.45 +/- 0.08 (18/40)
- Came within 30 m of the dock point: 0.47 +/- 0.06 (30/64); of those, docked: 0.60 +/- 0.09 (18/30)
- Closest approach: median 33 m (10th to 90th percentile 6 to 182 m)
- Time from the order to the dock: median 23.0 s (10th to 90th percentile 17.9 to 42.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.25 +/- 0.03 (n=18)
- Damage dealt per drill: 27.3 +/- 7.4 (n=64)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/64)
- Lift from seeing the order: +0.28

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.18 (6/33) | 0.48 |
| station | 0.14 (2/14) | 0.21 |
| citadel | 0.59 (10/17) | 0.29 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.46 (12/26) | 0.08 |
| bomber | 0.25 (4/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.807 | met |
| goto_lift | 0.664 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.898 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.578 | unset |
| dock_calm_lift | 0.547 | unset |
| dock_threat_docked | 0.281 | unset |
| dock_threat_docked_of_survivors | 0.450 | unset |
