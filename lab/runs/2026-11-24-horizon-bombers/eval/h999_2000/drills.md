# Order drills: h999_2000

**Gate: pass.** h999_2000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.87 +/- 0.02 (232/268) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (123/140; 13 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (16/132; 21 killed first, not counted)
- Lift from seeing the order: +0.76
- Near: 0.80 +/- 0.05 (60/75; 4 killed first, not counted)
- Far: 0.97 +/- 0.02 (63/65; 9 killed first, not counted)
- Enemies around the route: 0.81 +/- 0.05 (62/77; 8 killed first, not counted)
- Deadline in the order: 0.89 (83/93)
- No deadline (judged by 2x + 10 s): 0.85 (40/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (23/27) |
| medium (2.5 to 4.5) | 0.84 (31/37) |
| loose (over 4.5) | 1.00 (29/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 140 | 93 | 47 | 11 |
| In time | 0.88 | 0.89 | 0.85 | 0.73 |
| Near miss (within 60 m) | 0.11 | 0.09 | 0.15 | 0.18 |
| At the enemy instead | 0.01 | 0.02 | 0.00 | 0.09 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (120/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.58 +/- 0.11 (11/19)
- Damage on the named target per pilot: 42.2 +/- 4.6 (n=128)
- On other enemies per pilot (not judged): 32.0 +/- 3.3 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.05 +/- 0.02 (6/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.09 +/- 0.04 (6/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.03 (110/128)
- On the named ward's attackers per pilot: 51.6 +/- 4.1 (n=128)
- On the other's per pilot: 6.4 +/- 1.4 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Dock, alone (64 drills)

- Docked: 0.56 +/- 0.06 (36/64)
- Shot down first: 0.05 +/- 0.03 (3/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.59 +/- 0.06 (36/61)
- Came within 30 m of the dock point: 0.67 +/- 0.06 (43/64); of those, docked: 0.84 +/- 0.06 (36/43)
- Closest approach: median 10 m (10th to 90th percentile 5 to 57 m)
- Time from the order to the dock: median 14.1 s (10th to 90th percentile 8.0 to 25.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=36)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.53

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (19/32) | 0.03 |
| station | 0.67 (10/15) | 0.07 |
| citadel | 0.41 (7/17) | 0.06 |
| fighter | 1.00 (14/14) | 0.00 |
| strafer | 0.74 (14/19) | 0.16 |
| gunship | 0.13 (2/15) | 0.00 |
| bomber | 0.38 (6/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.30 +/- 0.06 (19/64)
- Shot down first: 0.33 +/- 0.06 (21/64)
- Out of time: 0.38 +/- 0.06 (24/64)
- Docked, of those not shot down: 0.44 +/- 0.08 (19/43)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.59 +/- 0.09 (19/32)
- Closest approach: median 30 m (10th to 90th percentile 5 to 175 m)
- Time from the order to the dock: median 23.3 s (10th to 90th percentile 11.0 to 33.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.02 (n=19)
- Damage dealt per drill: 25.2 +/- 8.8 (n=64)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/64)
- Lift from seeing the order: +0.30

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.30 (10/33) | 0.39 |
| station | 0.50 (7/14) | 0.21 |
| citadel | 0.12 (2/17) | 0.29 |
| fighter | 0.07 (1/14) | 0.71 |
| strafer | 0.12 (1/8) | 0.75 |
| gunship | 0.58 (15/26) | 0.04 |
| bomber | 0.12 (2/16) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.879 | met |
| goto_lift | 0.757 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.914 | met |
| attack_flip | 0.828 | met |
| defend_more_on_named | 0.859 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.562 | unset |
| dock_calm_lift | 0.531 | unset |
| dock_threat_docked | 0.297 | unset |
| dock_threat_docked_of_survivors | 0.442 | unset |
