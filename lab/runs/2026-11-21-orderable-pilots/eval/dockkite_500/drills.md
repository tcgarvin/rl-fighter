# Order drills: dockkite_500

**Gate: pass.** dockkite_500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.87 +/- 0.02 (233/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.03 (119/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (20/134; 19 killed first, not counted)
- Lift from seeing the order: +0.69
- Near: 0.82 +/- 0.04 (63/77; 2 killed first, not counted)
- Far: 0.88 +/- 0.04 (56/64; 10 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.04 (68/80; 5 killed first, not counted)
- Deadline in the order: 0.89 (85/96)
- No deadline (judged by 2x + 10 s): 0.76 (34/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.77 (20/26) |
| medium (2.5 to 4.5) | 0.92 (36/39) |
| loose (over 4.5) | 0.94 (29/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 96 | 45 | 13 |
| In time | 0.84 | 0.89 | 0.76 | 0.77 |
| Near miss (within 60 m) | 0.15 | 0.11 | 0.22 | 0.23 |
| At the enemy instead | 0.01 | 0.00 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.93 +/- 0.02 (119/128)
- Swap test, flipped, groups busy with a freighter: 0.89 +/- 0.05 (40/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 57.3 +/- 5.9 (n=128)
- On other enemies per pilot (not judged): 47.8 +/- 4.9 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.85 +/- 0.03 (109/128)
- On the named ward's attackers per pilot: 74.1 +/- 6.2 (n=128)
- On the other's per pilot: 9.8 +/- 2.3 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Dock, alone (64 drills)

- Docked: 0.53 +/- 0.06 (34/64)
- Shot down first: 0.08 +/- 0.03 (5/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.58 +/- 0.06 (34/59)
- Came within 30 m of the dock point: 0.77 +/- 0.05 (49/64); of those, docked: 0.69 +/- 0.07 (34/49)
- Closest approach: median 10 m (10th to 90th percentile 3 to 40 m)
- Time from the order to the dock: median 14.8 s (10th to 90th percentile 9.2 to 27.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=34)
- Damage dealt per drill: 0.7 +/- 0.7 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.52

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (19/32) | 0.06 |
| station | 0.47 (7/15) | 0.07 |
| citadel | 0.47 (8/17) | 0.12 |
| fighter | 0.64 (9/14) | 0.14 |
| strafer | 0.58 (11/19) | 0.16 |
| gunship | 0.53 (8/15) | 0.00 |
| bomber | 0.38 (6/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.25 +/- 0.05 (16/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.38 +/- 0.06 (24/64)
- Docked, of those not shot down: 0.40 +/- 0.08 (16/40)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.55 +/- 0.09 (16/29)
- Closest approach: median 34 m (10th to 90th percentile 3 to 205 m)
- Time from the order to the dock: median 30.1 s (10th to 90th percentile 15.9 to 38.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=16)
- Damage dealt per drill: 37.5 +/- 9.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.22

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.42 |
| station | 0.21 (3/14) | 0.29 |
| citadel | 0.35 (6/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.62 |
| gunship | 0.50 (13/26) | 0.12 |
| bomber | 0.06 (1/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.844 | met |
| goto_lift | 0.695 | met |
| attack_target_hit | 0.930 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.852 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.531 | unset |
| dock_calm_lift | 0.516 | unset |
| dock_threat_docked | 0.250 | unset |
| dock_threat_docked_of_survivors | 0.400 | unset |
