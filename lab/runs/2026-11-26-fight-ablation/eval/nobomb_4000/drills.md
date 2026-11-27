# Order drills: nobomb_4000

**Gate: fail.** nobomb_4000 failed the drill gate: defend_more_on_named.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.90 +/- 0.02 (239/267) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.93 +/- 0.02 (129/139; 14 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (17/133; 20 killed first, not counted)
- Lift from seeing the order: +0.80
- Near: 0.89 +/- 0.04 (65/73; 6 killed first, not counted)
- Far: 0.97 +/- 0.02 (64/66; 8 killed first, not counted)
- Enemies around the route: 0.92 +/- 0.03 (70/76; 9 killed first, not counted)
- Deadline in the order: 0.92 (85/92)
- No deadline (judged by 2x + 10 s): 0.94 (44/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (23/27) |
| medium (2.5 to 4.5) | 0.97 (35/36) |
| loose (over 4.5) | 0.93 (27/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 139 | 92 | 47 | 13 |
| In time | 0.93 | 0.92 | 0.94 | 0.85 |
| Near miss (within 60 m) | 0.06 | 0.08 | 0.04 | 0.15 |
| At the enemy instead | 0.01 | 0.00 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (120/128)
- Swap test, flipped, groups busy with a freighter: 0.91 +/- 0.04 (41/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 58.0 +/- 6.6 (n=128)
- On other enemies per pilot (not judged): 39.8 +/- 4.2 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.03 (106/128)
- On the named ward's attackers per pilot: 71.2 +/- 6.1 (n=128)
- On the other's per pilot: 7.9 +/- 1.8 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Dock, alone (64 drills)

- Docked: 0.44 +/- 0.06 (28/64)
- Shot down first: 0.16 +/- 0.05 (10/64)
- Out of time: 0.41 +/- 0.06 (26/64)
- Docked, of those not shot down: 0.52 +/- 0.07 (28/54)
- Came within 30 m of the dock point: 0.72 +/- 0.06 (46/64); of those, docked: 0.61 +/- 0.07 (28/46)
- Closest approach: median 10 m (10th to 90th percentile 3 to 76 m)
- Time from the order to the dock: median 12.5 s (10th to 90th percentile 7.0 to 23.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=28)
- Damage dealt per drill: 2.0 +/- 2.0 (n=64)
- Same drills, order hidden, docked: 0.19 +/- 0.05 (12/64)
- Lift from seeing the order: +0.25

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.06 |
| station | 0.33 (5/15) | 0.20 |
| citadel | 0.41 (7/17) | 0.29 |
| fighter | 0.64 (9/14) | 0.29 |
| strafer | 0.63 (12/19) | 0.32 |
| gunship | 0.33 (5/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.31 +/- 0.06 (20/64)
- Shot down first: 0.31 +/- 0.06 (20/64)
- Out of time: 0.38 +/- 0.06 (24/64)
- Docked, of those not shot down: 0.45 +/- 0.08 (20/44)
- Came within 30 m of the dock point: 0.48 +/- 0.06 (31/64); of those, docked: 0.65 +/- 0.09 (20/31)
- Closest approach: median 31 m (10th to 90th percentile 5 to 175 m)
- Time from the order to the dock: median 15.9 s (10th to 90th percentile 7.0 to 33.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.02 (n=20)
- Damage dealt per drill: 41.0 +/- 13.2 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.27

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.27 (9/33) | 0.33 |
| station | 0.14 (2/14) | 0.36 |
| citadel | 0.53 (9/17) | 0.24 |
| fighter | 0.07 (1/14) | 0.79 |
| strafer | 0.38 (3/8) | 0.62 |
| gunship | 0.46 (12/26) | 0.04 |
| bomber | 0.25 (4/16) | 0.19 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.928 | met |
| goto_lift | 0.800 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.828 | failed |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.438 | unset |
| dock_calm_lift | 0.250 | unset |
| dock_threat_docked | 0.312 | unset |
| dock_threat_docked_of_survivors | 0.455 | unset |
