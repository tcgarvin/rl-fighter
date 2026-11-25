# Order drills: h995_3000

**Gate: pass.** h995_3000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_3000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.91 +/- 0.02 (243/268) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.89 +/- 0.03 (124/140; 13 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (16/129; 24 killed first, not counted)
- Lift from seeing the order: +0.76
- Near: 0.88 +/- 0.04 (66/75; 4 killed first, not counted)
- Far: 0.89 +/- 0.04 (58/65; 9 killed first, not counted)
- Enemies around the route: 0.86 +/- 0.04 (67/78; 7 killed first, not counted)
- Deadline in the order: 0.88 (84/95)
- No deadline (judged by 2x + 10 s): 0.89 (40/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.75 (21/28) |
| medium (2.5 to 4.5) | 0.89 (33/37) |
| loose (over 4.5) | 1.00 (30/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 140 | 95 | 45 | 12 |
| In time | 0.89 | 0.88 | 0.89 | 0.92 |
| Near miss (within 60 m) | 0.11 | 0.11 | 0.11 | 0.00 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 54.7 +/- 5.9 (n=128)
- On other enemies per pilot (not judged): 37.4 +/- 3.8 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (117/128)
- On the named ward's attackers per pilot: 73.1 +/- 5.8 (n=128)
- On the other's per pilot: 4.2 +/- 1.2 (n=128)
- Chose the named side: 0.99 +/- 0.01 (127/128)
- Chose the other side: 0.00 +/- 0.00 (0/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.98 +/- 0.02 (63/64)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/64)

## Dock, alone (64 drills)

- Docked: 0.62 +/- 0.06 (40/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.31 +/- 0.06 (20/64)
- Docked, of those not shot down: 0.67 +/- 0.06 (40/60)
- Came within 30 m of the dock point: 0.88 +/- 0.04 (56/64); of those, docked: 0.71 +/- 0.06 (40/56)
- Closest approach: median 10 m (10th to 90th percentile 3 to 33 m)
- Time from the order to the dock: median 14.6 s (10th to 90th percentile 8.3 to 24.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.35 +/- 0.02 (n=40)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.58

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.69 (22/32) | 0.06 |
| station | 0.60 (9/15) | 0.00 |
| citadel | 0.53 (9/17) | 0.12 |
| fighter | 0.79 (11/14) | 0.07 |
| strafer | 0.84 (16/19) | 0.16 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.38 (6/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.30 +/- 0.06 (19/64)
- Shot down first: 0.34 +/- 0.06 (22/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.45 +/- 0.08 (19/42)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.59 +/- 0.09 (19/32)
- Closest approach: median 30 m (10th to 90th percentile 2 to 188 m)
- Time from the order to the dock: median 22.9 s (10th to 90th percentile 12.9 to 30.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.17 +/- 0.05 (11/64)
- Hull at the dock (fraction of its maximum): 0.23 +/- 0.03 (n=19)
- Damage dealt per drill: 22.6 +/- 7.6 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.28

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.33 (11/33) | 0.36 |
| station | 0.14 (2/14) | 0.29 |
| citadel | 0.35 (6/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.86 |
| strafer | 0.38 (3/8) | 0.50 |
| gunship | 0.42 (11/26) | 0.08 |
| bomber | 0.31 (5/16) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.886 | met |
| goto_lift | 0.762 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.914 | met |
| defend_side | 0.992 | met |
| defend_flip | 0.984 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.625 | unset |
| dock_calm_lift | 0.578 | unset |
| dock_threat_docked | 0.297 | unset |
| dock_threat_docked_of_survivors | 0.452 | unset |
