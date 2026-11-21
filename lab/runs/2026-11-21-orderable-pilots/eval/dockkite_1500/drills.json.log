# Order drills: dockkite_1500

**Gate: fail.** dockkite_1500 failed the drill gate: defend_flip.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.84 +/- 0.02 (223/267) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.85 +/- 0.03 (118/139; 14 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (16/132; 21 killed first, not counted)
- Lift from seeing the order: +0.73
- Near: 0.85 +/- 0.04 (64/75; 4 killed first, not counted)
- Far: 0.84 +/- 0.05 (54/64; 10 killed first, not counted)
- Enemies around the route: 0.81 +/- 0.04 (65/80; 5 killed first, not counted)
- Deadline in the order: 0.86 (83/96)
- No deadline (judged by 2x + 10 s): 0.81 (35/43)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.79 (22/28) |
| medium (2.5 to 4.5) | 0.85 (33/39) |
| loose (over 4.5) | 0.97 (28/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 139 | 96 | 43 | 13 |
| In time | 0.85 | 0.86 | 0.81 | 0.85 |
| Near miss (within 60 m) | 0.13 | 0.12 | 0.14 | 0.15 |
| At the enemy instead | 0.02 | 0.01 | 0.05 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (122/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 60.7 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 46.4 +/- 4.3 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 73.8 +/- 5.8 (n=128)
- On the other's per pilot: 10.0 +/- 2.0 (n=128)
- Chose the named side: 0.86 +/- 0.03 (110/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.10 +/- 0.03 (13/128)
- Swap test, flipped with the order: 0.73 +/- 0.06 (47/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Dock, alone (64 drills)

- Docked: 0.48 +/- 0.06 (31/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.45 +/- 0.06 (29/64)
- Docked, of those not shot down: 0.52 +/- 0.06 (31/60)
- Came within 30 m of the dock point: 0.73 +/- 0.06 (47/64); of those, docked: 0.66 +/- 0.07 (31/47)
- Closest approach: median 21 m (10th to 90th percentile 9 to 43 m)
- Time from the order to the dock: median 18.0 s (10th to 90th percentile 8.1 to 27.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=31)
- Damage dealt per drill: 1.0 +/- 1.0 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.42

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.53 (17/32) | 0.03 |
| station | 0.60 (9/15) | 0.07 |
| citadel | 0.29 (5/17) | 0.12 |
| fighter | 0.57 (8/14) | 0.14 |
| strafer | 0.58 (11/19) | 0.11 |
| gunship | 0.60 (9/15) | 0.00 |
| bomber | 0.19 (3/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.33 +/- 0.06 (21/64)
- Shot down first: 0.34 +/- 0.06 (22/64)
- Out of time: 0.33 +/- 0.06 (21/64)
- Docked, of those not shot down: 0.50 +/- 0.08 (21/42)
- Came within 30 m of the dock point: 0.38 +/- 0.06 (24/64); of those, docked: 0.88 +/- 0.07 (21/24)
- Closest approach: median 41 m (10th to 90th percentile 5 to 211 m)
- Time from the order to the dock: median 17.1 s (10th to 90th percentile 8.2 to 23.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.06 +/- 0.03 (4/64)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.02 (n=21)
- Damage dealt per drill: 43.4 +/- 11.7 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.28

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.30 (10/33) | 0.39 |
| station | 0.29 (4/14) | 0.29 |
| citadel | 0.41 (7/17) | 0.29 |
| fighter | 0.14 (2/14) | 0.57 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.50 (13/26) | 0.08 |
| bomber | 0.25 (4/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.849 | met |
| goto_lift | 0.728 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.953 | met |
| attack_flip | 0.906 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.859 | met |
| defend_flip | 0.734 | failed |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.484 | unset |
| dock_calm_lift | 0.422 | unset |
| dock_threat_docked | 0.328 | unset |
| dock_threat_docked_of_survivors | 0.500 | unset |
