# Order drills: h999_3000

**Gate: pass.** h999_3000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_3000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.02 (238/270) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (124/142; 11 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (16/133; 20 killed first, not counted)
- Lift from seeing the order: +0.75
- Near: 0.81 +/- 0.05 (62/77; 2 killed first, not counted)
- Far: 0.95 +/- 0.03 (62/65; 9 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (65/77; 8 killed first, not counted)
- Deadline in the order: 0.89 (85/96)
- No deadline (judged by 2x + 10 s): 0.85 (39/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.92 (24/26) |
| medium (2.5 to 4.5) | 0.80 (32/40) |
| loose (over 4.5) | 0.97 (29/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 142 | 96 | 46 | 12 |
| In time | 0.87 | 0.89 | 0.85 | 0.75 |
| Near miss (within 60 m) | 0.11 | 0.09 | 0.15 | 0.17 |
| At the enemy instead | 0.01 | 0.02 | 0.00 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (122/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 45.7 +/- 4.4 (n=128)
- On other enemies per pilot (not judged): 34.2 +/- 3.7 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 64.9 +/- 6.0 (n=128)
- On the other's per pilot: 5.0 +/- 1.1 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Dock, alone (64 drills)

- Docked: 0.50 +/- 0.06 (32/64)
- Shot down first: 0.05 +/- 0.03 (3/64)
- Out of time: 0.45 +/- 0.06 (29/64)
- Docked, of those not shot down: 0.52 +/- 0.06 (32/61)
- Came within 30 m of the dock point: 0.64 +/- 0.06 (41/64); of those, docked: 0.78 +/- 0.06 (32/41)
- Closest approach: median 21 m (10th to 90th percentile 5 to 56 m)
- Time from the order to the dock: median 11.6 s (10th to 90th percentile 7.4 to 22.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=32)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.47

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.69 (22/32) | 0.03 |
| station | 0.27 (4/15) | 0.07 |
| citadel | 0.35 (6/17) | 0.06 |
| fighter | 0.64 (9/14) | 0.00 |
| strafer | 0.74 (14/19) | 0.16 |
| gunship | 0.40 (6/15) | 0.00 |
| bomber | 0.19 (3/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.25 +/- 0.05 (16/64)
- Shot down first: 0.33 +/- 0.06 (21/64)
- Out of time: 0.42 +/- 0.06 (27/64)
- Docked, of those not shot down: 0.37 +/- 0.07 (16/43)
- Came within 30 m of the dock point: 0.38 +/- 0.06 (24/64); of those, docked: 0.67 +/- 0.10 (16/24)
- Closest approach: median 40 m (10th to 90th percentile 5 to 189 m)
- Time from the order to the dock: median 20.6 s (10th to 90th percentile 10.5 to 41.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.03 (n=16)
- Damage dealt per drill: 27.8 +/- 7.5 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.23

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.18 (6/33) | 0.45 |
| station | 0.36 (5/14) | 0.21 |
| citadel | 0.29 (5/17) | 0.18 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.46 (12/26) | 0.00 |
| bomber | 0.12 (2/16) | 0.31 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.873 | met |
| goto_lift | 0.753 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.953 | met |
| attack_flip | 0.906 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.500 | unset |
| dock_calm_lift | 0.469 | unset |
| dock_threat_docked | 0.250 | unset |
| dock_threat_docked_of_survivors | 0.372 | unset |
