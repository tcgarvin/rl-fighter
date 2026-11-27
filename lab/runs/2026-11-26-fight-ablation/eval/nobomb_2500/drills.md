# Order drills: nobomb_2500

**Gate: pass.** nobomb_2500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.95 +/- 0.01 (256/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.96 +/- 0.02 (135/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (17/130; 23 killed first, not counted)
- Lift from seeing the order: +0.83
- Near: 0.95 +/- 0.03 (69/73; 6 killed first, not counted)
- Far: 0.97 +/- 0.02 (66/68; 6 killed first, not counted)
- Enemies around the route: 0.95 +/- 0.03 (70/74; 11 killed first, not counted)
- Deadline in the order: 0.97 (91/94)
- No deadline (judged by 2x + 10 s): 0.94 (44/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.92 (22/24) |
| medium (2.5 to 4.5) | 0.97 (38/39) |
| loose (over 4.5) | 1.00 (31/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 94 | 47 | 12 |
| In time | 0.96 | 0.97 | 0.94 | 0.83 |
| Near miss (within 60 m) | 0.03 | 0.02 | 0.04 | 0.08 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.93 +/- 0.02 (119/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.89 +/- 0.07 (17/19)
- Damage on the named target per pilot: 61.5 +/- 5.9 (n=128)
- On other enemies per pilot (not judged): 41.6 +/- 4.4 (n=128)
- Chose the named side: 0.98 +/- 0.01 (126/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.00 +/- 0.00 (0/128)
- Swap test, flipped with the order: 0.97 +/- 0.02 (62/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.95 +/- 0.02 (122/128)
- On the named ward's attackers per pilot: 80.4 +/- 6.2 (n=128)
- On the other's per pilot: 3.5 +/- 1.0 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.62 +/- 0.06 (40/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.31 +/- 0.06 (20/64)
- Docked, of those not shot down: 0.67 +/- 0.06 (40/60)
- Came within 30 m of the dock point: 0.77 +/- 0.05 (49/64); of those, docked: 0.82 +/- 0.06 (40/49)
- Closest approach: median 10 m (10th to 90th percentile 4 to 50 m)
- Time from the order to the dock: median 9.6 s (10th to 90th percentile 6.6 to 23.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=40)
- Damage dealt per drill: 0.8 +/- 0.8 (n=64)
- Same drills, order hidden, docked: 0.09 +/- 0.04 (6/64)
- Lift from seeing the order: +0.53

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.69 (22/32) | 0.03 |
| station | 0.47 (7/15) | 0.13 |
| citadel | 0.65 (11/17) | 0.06 |
| fighter | 0.86 (12/14) | 0.07 |
| strafer | 0.89 (17/19) | 0.11 |
| gunship | 0.53 (8/15) | 0.00 |
| bomber | 0.19 (3/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.27 +/- 0.06 (17/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.42 +/- 0.08 (17/40)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.53 +/- 0.09 (17/32)
- Closest approach: median 30 m (10th to 90th percentile 2 to 168 m)
- Time from the order to the dock: median 21.2 s (10th to 90th percentile 12.3 to 30.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.30 +/- 0.03 (n=17)
- Damage dealt per drill: 27.4 +/- 9.7 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.20

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.27 (9/33) | 0.45 |
| station | 0.00 (0/14) | 0.29 |
| citadel | 0.47 (8/17) | 0.29 |
| fighter | 0.07 (1/14) | 0.79 |
| strafer | 0.12 (1/8) | 0.88 |
| gunship | 0.42 (11/26) | 0.00 |
| bomber | 0.25 (4/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.957 | met |
| goto_lift | 0.827 | met |
| attack_target_hit | 0.930 | met |
| attack_side | 0.984 | met |
| attack_flip | 0.969 | met |
| defend_more_on_named | 0.953 | met |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.625 | unset |
| dock_calm_lift | 0.531 | unset |
| dock_threat_docked | 0.266 | unset |
| dock_threat_docked_of_survivors | 0.425 | unset |
