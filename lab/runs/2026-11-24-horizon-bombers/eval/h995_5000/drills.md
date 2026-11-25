# Order drills: h995_5000

**Gate: pass.** h995_5000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_5000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.86 +/- 0.02 (229/266) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (120/138; 15 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (19/128; 25 killed first, not counted)
- Lift from seeing the order: +0.72
- Near: 0.86 +/- 0.04 (60/70; 9 killed first, not counted)
- Far: 0.88 +/- 0.04 (60/68; 6 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (61/73; 12 killed first, not counted)
- Deadline in the order: 0.90 (84/93)
- No deadline (judged by 2x + 10 s): 0.80 (36/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.75 (18/24) |
| medium (2.5 to 4.5) | 0.95 (36/38) |
| loose (over 4.5) | 0.97 (30/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 138 | 93 | 45 | 12 |
| In time | 0.87 | 0.90 | 0.80 | 0.75 |
| Near miss (within 60 m) | 0.12 | 0.09 | 0.20 | 0.25 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 59.5 +/- 6.4 (n=128)
- On other enemies per pilot (not judged): 32.8 +/- 3.7 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (112/128)
- On the named ward's attackers per pilot: 72.1 +/- 5.7 (n=128)
- On the other's per pilot: 6.4 +/- 1.4 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Dock, alone (64 drills)

- Docked: 0.48 +/- 0.06 (31/64)
- Shot down first: 0.23 +/- 0.05 (15/64)
- Out of time: 0.28 +/- 0.06 (18/64)
- Docked, of those not shot down: 0.63 +/- 0.07 (31/49)
- Came within 30 m of the dock point: 0.81 +/- 0.05 (52/64); of those, docked: 0.60 +/- 0.07 (31/52)
- Closest approach: median 11 m (10th to 90th percentile 2 to 34 m)
- Time from the order to the dock: median 14.6 s (10th to 90th percentile 7.3 to 27.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=31)
- Damage dealt per drill: 2.8 +/- 2.4 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.47

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.44 (14/32) | 0.22 |
| station | 0.33 (5/15) | 0.33 |
| citadel | 0.71 (12/17) | 0.18 |
| fighter | 0.64 (9/14) | 0.29 |
| strafer | 0.42 (8/19) | 0.47 |
| gunship | 0.73 (11/15) | 0.00 |
| bomber | 0.19 (3/16) | 0.12 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.31 +/- 0.06 (20/64)
- Shot down first: 0.33 +/- 0.06 (21/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.47 +/- 0.08 (20/43)
- Came within 30 m of the dock point: 0.53 +/- 0.06 (34/64); of those, docked: 0.59 +/- 0.08 (20/34)
- Closest approach: median 27 m (10th to 90th percentile 1 to 192 m)
- Time from the order to the dock: median 20.8 s (10th to 90th percentile 11.0 to 33.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.12 +/- 0.04 (8/64)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.02 (n=20)
- Damage dealt per drill: 41.6 +/- 14.1 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.28

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.33 (11/33) | 0.39 |
| station | 0.21 (3/14) | 0.14 |
| citadel | 0.35 (6/17) | 0.35 |
| fighter | 0.07 (1/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.58 (15/26) | 0.00 |
| bomber | 0.12 (2/16) | 0.31 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.870 | met |
| goto_lift | 0.721 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.859 | met |
| defend_more_on_named | 0.875 | met |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.484 | unset |
| dock_calm_lift | 0.469 | unset |
| dock_threat_docked | 0.312 | unset |
| dock_threat_docked_of_survivors | 0.465 | unset |
