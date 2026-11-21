# Order drills: kitedock_2000

**Gate: fail.** kitedock_2000 failed the drill gate: defend_more_on_named.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.91 +/- 0.02 (239/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (120/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (20/130; 23 killed first, not counted)
- Lift from seeing the order: +0.73
- Near: 0.84 +/- 0.04 (61/73; 6 killed first, not counted)
- Far: 0.94 +/- 0.03 (59/63; 11 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (64/76; 9 killed first, not counted)
- Deadline in the order: 0.88 (80/91)
- No deadline (judged by 2x + 10 s): 0.89 (40/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (21/26) |
| medium (2.5 to 4.5) | 0.86 (32/37) |
| loose (over 4.5) | 0.96 (27/28) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 91 | 45 | 13 |
| In time | 0.88 | 0.88 | 0.89 | 0.85 |
| Near miss (within 60 m) | 0.10 | 0.10 | 0.09 | 0.08 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.08 |
| Neither | 0.01 | 0.01 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 65.4 +/- 6.9 (n=128)
- On other enemies per pilot (not judged): 47.5 +/- 4.7 (n=128)
- Chose the named side: 0.98 +/- 0.01 (125/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.95 +/- 0.03 (61/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.03 (108/128)
- On the named ward's attackers per pilot: 80.4 +/- 7.4 (n=128)
- On the other's per pilot: 9.5 +/- 2.2 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Dock, alone (64 drills)

- Docked: 0.19 +/- 0.05 (12/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.75 +/- 0.05 (48/64)
- Docked, of those not shot down: 0.20 +/- 0.05 (12/60)
- Came within 30 m of the dock point: 0.34 +/- 0.06 (22/64); of those, docked: 0.55 +/- 0.11 (12/22)
- Closest approach: median 39 m (10th to 90th percentile 8 to 62 m)
- Time from the order to the dock: median 20.1 s (10th to 90th percentile 7.6 to 28.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.05 +/- 0.03 (3/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.03 (n=12)
- Damage dealt per drill: 1.0 +/- 1.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.12 (4/32) | 0.06 |
| station | 0.13 (2/15) | 0.13 |
| citadel | 0.35 (6/17) | 0.00 |
| fighter | 0.07 (1/14) | 0.14 |
| strafer | 0.11 (2/19) | 0.11 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.17 +/- 0.05 (11/64)
- Shot down first: 0.33 +/- 0.06 (21/64)
- Out of time: 0.50 +/- 0.06 (32/64)
- Docked, of those not shot down: 0.26 +/- 0.07 (11/43)
- Came within 30 m of the dock point: 0.38 +/- 0.06 (24/64); of those, docked: 0.46 +/- 0.10 (11/24)
- Closest approach: median 55 m (10th to 90th percentile 7 to 177 m)
- Time from the order to the dock: median 28.2 s (10th to 90th percentile 8.3 to 45.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.30 +/- 0.03 (n=11)
- Damage dealt per drill: 23.2 +/- 6.3 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.14

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.12 (4/33) | 0.36 |
| station | 0.07 (1/14) | 0.29 |
| citadel | 0.35 (6/17) | 0.29 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.00 (0/8) | 0.75 |
| gunship | 0.42 (11/26) | 0.00 |
| bomber | 0.00 (0/16) | 0.31 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.882 | met |
| goto_lift | 0.729 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.977 | met |
| attack_flip | 0.953 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.188 | unset |
| dock_calm_lift | 0.172 | unset |
| dock_threat_docked | 0.172 | unset |
| dock_threat_docked_of_survivors | 0.256 | unset |
