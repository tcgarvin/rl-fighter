# Order drills: nobomb_1000

**Gate: pass.** nobomb_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.87 +/- 0.02 (236/270) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.82 +/- 0.03 (116/142; 11 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (21/132; 21 killed first, not counted)
- Lift from seeing the order: +0.66
- Near: 0.78 +/- 0.05 (59/76; 3 killed first, not counted)
- Far: 0.86 +/- 0.04 (57/66; 8 killed first, not counted)
- Enemies around the route: 0.73 +/- 0.05 (58/79; 6 killed first, not counted)
- Deadline in the order: 0.85 (82/97)
- No deadline (judged by 2x + 10 s): 0.76 (34/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.70 (19/27) |
| medium (2.5 to 4.5) | 0.88 (35/40) |
| loose (over 4.5) | 0.93 (28/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 142 | 97 | 45 | 9 |
| In time | 0.82 | 0.85 | 0.76 | 0.78 |
| Near miss (within 60 m) | 0.15 | 0.12 | 0.22 | 0.11 |
| At the enemy instead | 0.03 | 0.03 | 0.02 | 0.11 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 63.0 +/- 6.4 (n=128)
- On other enemies per pilot (not judged): 49.1 +/- 5.2 (n=128)
- Chose the named side: 0.98 +/- 0.01 (125/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.95 +/- 0.03 (61/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (117/128)
- On the named ward's attackers per pilot: 89.2 +/- 7.1 (n=128)
- On the other's per pilot: 7.1 +/- 1.7 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.53 +/- 0.06 (34/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.60 +/- 0.06 (34/57)
- Came within 30 m of the dock point: 0.55 +/- 0.06 (35/64); of those, docked: 0.97 +/- 0.03 (34/35)
- Closest approach: median 24 m (10th to 90th percentile 5 to 144 m)
- Time from the order to the dock: median 11.8 s (10th to 90th percentile 6.2 to 21.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=34)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.50

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.56 (18/32) | 0.06 |
| station | 0.53 (8/15) | 0.07 |
| citadel | 0.47 (8/17) | 0.24 |
| fighter | 0.79 (11/14) | 0.21 |
| strafer | 0.79 (15/19) | 0.11 |
| gunship | 0.40 (6/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.12 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.23 +/- 0.05 (15/64)
- Shot down first: 0.36 +/- 0.06 (23/64)
- Out of time: 0.41 +/- 0.06 (26/64)
- Docked, of those not shot down: 0.37 +/- 0.08 (15/41)
- Came within 30 m of the dock point: 0.41 +/- 0.06 (26/64); of those, docked: 0.58 +/- 0.10 (15/26)
- Closest approach: median 36 m (10th to 90th percentile 3 to 204 m)
- Time from the order to the dock: median 23.2 s (10th to 90th percentile 13.6 to 32.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.19 +/- 0.05 (12/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=15)
- Damage dealt per drill: 38.4 +/- 11.0 (n=64)
- Same drills, order hidden, docked: 0.11 +/- 0.04 (7/64)
- Lift from seeing the order: +0.12

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.24 (8/33) | 0.39 |
| station | 0.14 (2/14) | 0.36 |
| citadel | 0.29 (5/17) | 0.29 |
| fighter | 0.14 (2/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.35 (9/26) | 0.00 |
| bomber | 0.12 (2/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.817 | met |
| goto_lift | 0.658 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.977 | met |
| attack_flip | 0.953 | met |
| defend_more_on_named | 0.914 | met |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.531 | unset |
| dock_calm_lift | 0.500 | unset |
| dock_threat_docked | 0.234 | unset |
| dock_threat_docked_of_survivors | 0.366 | unset |
