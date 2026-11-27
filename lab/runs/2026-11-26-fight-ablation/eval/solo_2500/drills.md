# Order drills: solo_2500

**Gate: pass.** solo_2500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.84 +/- 0.02 (225/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.82 +/- 0.03 (115/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.03 (17/125; 28 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.75 +/- 0.05 (55/73; 6 killed first, not counted)
- Far: 0.88 +/- 0.04 (60/68; 6 killed first, not counted)
- Enemies around the route: 0.76 +/- 0.05 (60/79; 6 killed first, not counted)
- Deadline in the order: 0.84 (81/97)
- No deadline (judged by 2x + 10 s): 0.77 (34/44)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.70 (19/27) |
| medium (2.5 to 4.5) | 0.85 (35/41) |
| loose (over 4.5) | 0.93 (27/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 97 | 44 | 12 |
| In time | 0.82 | 0.84 | 0.77 | 0.67 |
| Near miss (within 60 m) | 0.15 | 0.12 | 0.20 | 0.33 |
| At the enemy instead | 0.04 | 0.04 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (122/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.53 +/- 0.11 (10/19)
- Damage on the named target per pilot: 51.7 +/- 5.9 (n=128)
- On other enemies per pilot (not judged): 29.9 +/- 3.5 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.11 +/- 0.04 (7/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.93 +/- 0.02 (119/128)
- On the named ward's attackers per pilot: 73.0 +/- 6.7 (n=128)
- On the other's per pilot: 2.7 +/- 0.9 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.33 +/- 0.06 (21/64)
- Shot down first: 0.14 +/- 0.04 (9/64)
- Out of time: 0.53 +/- 0.06 (34/64)
- Docked, of those not shot down: 0.38 +/- 0.07 (21/55)
- Came within 30 m of the dock point: 0.62 +/- 0.06 (40/64); of those, docked: 0.53 +/- 0.08 (21/40)
- Closest approach: median 18 m (10th to 90th percentile 1 to 141 m)
- Time from the order to the dock: median 14.3 s (10th to 90th percentile 6.6 to 27.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.12 +/- 0.04 (8/64)
- Hull at the dock (fraction of its maximum): 0.35 +/- 0.02 (n=21)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.09 +/- 0.04 (6/64)
- Lift from seeing the order: +0.23

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.34 (11/32) | 0.06 |
| station | 0.27 (4/15) | 0.20 |
| citadel | 0.35 (6/17) | 0.24 |
| fighter | 0.29 (4/14) | 0.43 |
| strafer | 0.58 (11/19) | 0.16 |
| gunship | 0.33 (5/15) | 0.00 |
| bomber | 0.06 (1/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.14 +/- 0.04 (9/64)
- Shot down first: 0.41 +/- 0.06 (26/64)
- Out of time: 0.45 +/- 0.06 (29/64)
- Docked, of those not shot down: 0.24 +/- 0.07 (9/38)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.28 +/- 0.08 (9/32)
- Closest approach: median 31 m (10th to 90th percentile 6 to 159 m)
- Time from the order to the dock: median 16.8 s (10th to 90th percentile 11.2 to 36.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.04 (n=9)
- Damage dealt per drill: 48.5 +/- 11.9 (n=64)
- Same drills, order hidden, docked: 0.08 +/- 0.03 (5/64)
- Lift from seeing the order: +0.06

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.09 (3/33) | 0.39 |
| station | 0.07 (1/14) | 0.43 |
| citadel | 0.29 (5/17) | 0.41 |
| fighter | 0.00 (0/14) | 0.79 |
| strafer | 0.12 (1/8) | 0.88 |
| gunship | 0.31 (8/26) | 0.00 |
| bomber | 0.00 (0/16) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.816 | met |
| goto_lift | 0.680 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.914 | met |
| attack_flip | 0.828 | met |
| defend_more_on_named | 0.930 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.328 | unset |
| dock_calm_lift | 0.234 | unset |
| dock_threat_docked | 0.141 | unset |
| dock_threat_docked_of_survivors | 0.237 | unset |
