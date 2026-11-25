# Order drills: h999_5000

**Gate: pass.** h999_5000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_5000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.02 (238/266) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.92 +/- 0.02 (127/138; 15 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (17/138; 15 killed first, not counted)
- Lift from seeing the order: +0.80
- Near: 0.89 +/- 0.04 (65/73; 6 killed first, not counted)
- Far: 0.95 +/- 0.03 (62/65; 9 killed first, not counted)
- Enemies around the route: 0.91 +/- 0.03 (71/78; 7 killed first, not counted)
- Deadline in the order: 0.96 (89/93)
- No deadline (judged by 2x + 10 s): 0.84 (38/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.96 (25/26) |
| medium (2.5 to 4.5) | 0.92 (35/38) |
| loose (over 4.5) | 1.00 (29/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 138 | 93 | 45 | 12 |
| In time | 0.92 | 0.96 | 0.84 | 1.00 |
| Near miss (within 60 m) | 0.07 | 0.03 | 0.13 | 0.00 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (122/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.74 +/- 0.10 (14/19)
- Damage on the named target per pilot: 43.1 +/- 5.0 (n=128)
- On other enemies per pilot (not judged): 30.9 +/- 3.8 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.95 +/- 0.02 (121/128)
- On the named ward's attackers per pilot: 55.0 +/- 4.0 (n=128)
- On the other's per pilot: 1.3 +/- 0.4 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.56 +/- 0.06 (36/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.33 +/- 0.06 (21/64)
- Docked, of those not shot down: 0.63 +/- 0.06 (36/57)
- Came within 30 m of the dock point: 0.73 +/- 0.06 (47/64); of those, docked: 0.77 +/- 0.06 (36/47)
- Closest approach: median 10 m (10th to 90th percentile 4 to 48 m)
- Time from the order to the dock: median 12.3 s (10th to 90th percentile 7.7 to 24.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=36)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.50

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (19/32) | 0.06 |
| station | 0.60 (9/15) | 0.13 |
| citadel | 0.47 (8/17) | 0.18 |
| fighter | 0.79 (11/14) | 0.21 |
| strafer | 0.74 (14/19) | 0.21 |
| gunship | 0.27 (4/15) | 0.00 |
| bomber | 0.44 (7/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.23 +/- 0.05 (15/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.38 +/- 0.08 (15/40)
- Came within 30 m of the dock point: 0.56 +/- 0.06 (36/64); of those, docked: 0.42 +/- 0.08 (15/36)
- Closest approach: median 28 m (10th to 90th percentile 5 to 122 m)
- Time from the order to the dock: median 20.3 s (10th to 90th percentile 8.5 to 35.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=15)
- Damage dealt per drill: 9.1 +/- 3.3 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.24 (8/33) | 0.45 |
| station | 0.21 (3/14) | 0.21 |
| citadel | 0.24 (4/17) | 0.35 |
| fighter | 0.14 (2/14) | 0.79 |
| strafer | 0.00 (0/8) | 1.00 |
| gunship | 0.38 (10/26) | 0.08 |
| bomber | 0.19 (3/16) | 0.19 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.920 | met |
| goto_lift | 0.797 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.945 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.945 | met |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.562 | unset |
| dock_calm_lift | 0.500 | unset |
| dock_threat_docked | 0.234 | unset |
| dock_threat_docked_of_survivors | 0.375 | unset |
