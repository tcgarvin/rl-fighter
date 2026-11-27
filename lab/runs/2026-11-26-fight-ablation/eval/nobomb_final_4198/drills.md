# Order drills: nobomb_final_4198

**Gate: pass.** nobomb_final_4198 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4198.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.01 (499/565) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.90 +/- 0.02 (277/309; 25 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.02 (44/292; 42 killed first, not counted)
- Lift from seeing the order: +0.75
- Near: 0.85 +/- 0.03 (146/172; 8 killed first, not counted)
- Far: 0.96 +/- 0.02 (131/137; 17 killed first, not counted)
- Enemies around the route: 0.89 +/- 0.02 (154/173; 19 killed first, not counted)
- Deadline in the order: 0.92 (200/217)
- No deadline (judged by 2x + 10 s): 0.84 (77/92)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.80 (43/54) |
| medium (2.5 to 4.5) | 0.96 (94/98) |
| loose (over 4.5) | 0.97 (63/65) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 309 | 217 | 92 | 20 |
| In time | 0.90 | 0.92 | 0.84 | 0.75 |
| Near miss (within 60 m) | 0.09 | 0.07 | 0.15 | 0.25 |
| At the enemy instead | 0.01 | 0.01 | 0.01 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.96 +/- 0.01 (247/256)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.02 (92/96)
- Swap test, flipped, groups flying at the pilots: 0.66 +/- 0.08 (21/32)
- Damage on the named target per pilot: 60.4 +/- 4.3 (n=256)
- On other enemies per pilot (not judged): 37.1 +/- 3.0 (n=256)
- Chose the named side: 0.93 +/- 0.02 (239/256)
- Chose the other side: 0.05 +/- 0.01 (13/256)
- Chose neither: 0.02 +/- 0.01 (4/256)
- Swap test, flipped with the order: 0.88 +/- 0.03 (113/128)
- Swap test, one side whatever was named: 0.07 +/- 0.02 (9/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.02 (219/256)
- On the named ward's attackers per pilot: 73.3 +/- 4.7 (n=256)
- On the other's per pilot: 7.6 +/- 1.2 (n=256)
- Chose the named side: 0.93 +/- 0.02 (237/256)
- Chose the other side: 0.03 +/- 0.01 (8/256)
- Chose neither: 0.04 +/- 0.01 (11/256)
- Swap test, flipped with the order: 0.85 +/- 0.03 (109/128)
- Swap test, one side whatever was named: 0.06 +/- 0.02 (8/128)

## Dock, alone (128 drills)

- Docked: 0.65 +/- 0.04 (83/128)
- Shot down first: 0.09 +/- 0.02 (11/128)
- Out of time: 0.27 +/- 0.04 (34/128)
- Docked, of those not shot down: 0.71 +/- 0.04 (83/117)
- Came within 30 m of the dock point: 0.79 +/- 0.04 (101/128); of those, docked: 0.82 +/- 0.04 (83/101)
- Closest approach: median 10 m (10th to 90th percentile 5 to 40 m)
- Time from the order to the dock: median 13.4 s (10th to 90th percentile 8.2 to 29.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.04 +/- 0.02 (5/128)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.01 (n=83)
- Damage dealt per drill: 7.3 +/- 4.0 (n=128)
- Same drills, order hidden, docked: 0.10 +/- 0.03 (13/128)
- Lift from seeing the order: +0.55

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.70 (42/60) | 0.05 |
| station | 0.65 (20/31) | 0.10 |
| citadel | 0.57 (21/37) | 0.14 |
| fighter | 0.74 (23/31) | 0.23 |
| strafer | 0.85 (29/34) | 0.09 |
| gunship | 0.62 (20/32) | 0.03 |
| bomber | 0.35 (11/31) | 0.00 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.24 +/- 0.04 (31/128)
- Shot down first: 0.39 +/- 0.04 (50/128)
- Out of time: 0.37 +/- 0.04 (47/128)
- Docked, of those not shot down: 0.40 +/- 0.06 (31/78)
- Came within 30 m of the dock point: 0.38 +/- 0.04 (49/128); of those, docked: 0.63 +/- 0.07 (31/49)
- Closest approach: median 40 m (10th to 90th percentile 6 to 180 m)
- Time from the order to the dock: median 22.6 s (10th to 90th percentile 11.7 to 34.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.03 (12/128)
- Hull at the dock (fraction of its maximum): 0.24 +/- 0.02 (n=31)
- Damage dealt per drill: 35.2 +/- 6.6 (n=128)
- Same drills, order hidden, docked: 0.07 +/- 0.02 (9/128)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.23 (15/64) | 0.42 |
| station | 0.21 (7/34) | 0.29 |
| citadel | 0.30 (9/30) | 0.43 |
| fighter | 0.19 (5/27) | 0.70 |
| strafer | 0.19 (5/26) | 0.73 |
| gunship | 0.36 (14/39) | 0.08 |
| bomber | 0.19 (7/36) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.896 | met |
| goto_lift | 0.746 | met |
| attack_target_hit | 0.965 | met |
| attack_side | 0.934 | met |
| attack_flip | 0.883 | met |
| defend_more_on_named | 0.855 | met |
| defend_side | 0.926 | met |
| defend_flip | 0.852 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.648 | unset |
| dock_calm_lift | 0.547 | unset |
| dock_threat_docked | 0.242 | unset |
| dock_threat_docked_of_survivors | 0.397 | unset |
