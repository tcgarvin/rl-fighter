# Order drills: h995_4000

**Gate: pass.** h995_4000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.86 +/- 0.02 (229/267) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (122/139; 14 killed first, not counted)
- Same seeds, order hidden: 0.20 +/- 0.04 (26/129; 24 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.86 +/- 0.04 (61/71; 8 killed first, not counted)
- Far: 0.90 +/- 0.04 (61/68; 6 killed first, not counted)
- Enemies around the route: 0.87 +/- 0.04 (65/75; 10 killed first, not counted)
- Deadline in the order: 0.91 (84/92)
- No deadline (judged by 2x + 10 s): 0.81 (38/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.91 (32/35) |
| loose (over 4.5) | 0.97 (30/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 139 | 92 | 47 | 11 |
| In time | 0.88 | 0.91 | 0.81 | 0.82 |
| Near miss (within 60 m) | 0.11 | 0.08 | 0.17 | 0.09 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.09 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 57.9 +/- 6.5 (n=128)
- On other enemies per pilot (not judged): 36.2 +/- 4.0 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (112/128)
- On the named ward's attackers per pilot: 63.4 +/- 6.0 (n=128)
- On the other's per pilot: 10.4 +/- 2.8 (n=128)
- Chose the named side: 0.91 +/- 0.03 (116/128)
- Chose the other side: 0.05 +/- 0.02 (6/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.09 +/- 0.04 (6/64)

## Dock, alone (64 drills)

- Docked: 0.61 +/- 0.06 (39/64)
- Shot down first: 0.16 +/- 0.05 (10/64)
- Out of time: 0.23 +/- 0.05 (15/64)
- Docked, of those not shot down: 0.72 +/- 0.06 (39/54)
- Came within 30 m of the dock point: 0.92 +/- 0.03 (59/64); of those, docked: 0.66 +/- 0.06 (39/59)
- Closest approach: median 10 m (10th to 90th percentile 2 to 28 m)
- Time from the order to the dock: median 13.9 s (10th to 90th percentile 6.1 to 27.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.16 +/- 0.05 (10/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=39)
- Damage dealt per drill: 3.7 +/- 2.7 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.58

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.66 (21/32) | 0.06 |
| station | 0.53 (8/15) | 0.27 |
| citadel | 0.59 (10/17) | 0.24 |
| fighter | 0.79 (11/14) | 0.21 |
| strafer | 0.53 (10/19) | 0.32 |
| gunship | 0.67 (10/15) | 0.00 |
| bomber | 0.50 (8/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.33 +/- 0.06 (21/64)
- Shot down first: 0.44 +/- 0.06 (28/64)
- Out of time: 0.23 +/- 0.05 (15/64)
- Docked, of those not shot down: 0.58 +/- 0.08 (21/36)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.72 +/- 0.08 (21/29)
- Closest approach: median 32 m (10th to 90th percentile 3 to 164 m)
- Time from the order to the dock: median 17.2 s (10th to 90th percentile 11.8 to 33.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.30 +/- 0.02 (n=21)
- Damage dealt per drill: 31.4 +/- 9.2 (n=64)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/64)
- Lift from seeing the order: +0.33

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.36 (12/33) | 0.48 |
| station | 0.29 (4/14) | 0.43 |
| citadel | 0.29 (5/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.86 |
| strafer | 0.00 (0/8) | 1.00 |
| gunship | 0.65 (17/26) | 0.12 |
| bomber | 0.25 (4/16) | 0.31 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.878 | met |
| goto_lift | 0.676 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.914 | met |
| attack_flip | 0.844 | met |
| defend_more_on_named | 0.875 | met |
| defend_side | 0.906 | met |
| defend_flip | 0.828 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.609 | unset |
| dock_calm_lift | 0.578 | unset |
| dock_threat_docked | 0.328 | unset |
| dock_threat_docked_of_survivors | 0.583 | unset |
