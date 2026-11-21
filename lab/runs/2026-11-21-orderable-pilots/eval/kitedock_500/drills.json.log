# Order drills: kitedock_500

**Gate: pass.** kitedock_500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.02 (236/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (118/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.21 +/- 0.04 (27/130; 23 killed first, not counted)
- Lift from seeing the order: +0.66
- Near: 0.83 +/- 0.04 (60/72; 7 killed first, not counted)
- Far: 0.91 +/- 0.04 (58/64; 10 killed first, not counted)
- Enemies around the route: 0.86 +/- 0.04 (64/74; 11 killed first, not counted)
- Deadline in the order: 0.88 (79/90)
- No deadline (judged by 2x + 10 s): 0.85 (39/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (21/26) |
| medium (2.5 to 4.5) | 0.86 (31/36) |
| loose (over 4.5) | 0.96 (27/28) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 90 | 46 | 12 |
| In time | 0.87 | 0.88 | 0.85 | 0.83 |
| Near miss (within 60 m) | 0.10 | 0.08 | 0.13 | 0.17 |
| At the enemy instead | 0.04 | 0.04 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.91 +/- 0.02 (117/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 65.7 +/- 7.4 (n=128)
- On other enemies per pilot (not judged): 46.2 +/- 5.3 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 80.0 +/- 6.0 (n=128)
- On the other's per pilot: 8.1 +/- 2.5 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Dock, alone (64 drills)

- Docked: 0.02 +/- 0.02 (1/64)
- Shot down first: 0.09 +/- 0.04 (6/64)
- Out of time: 0.89 +/- 0.04 (57/64)
- Docked, of those not shot down: 0.02 +/- 0.02 (1/58)
- Came within 30 m of the dock point: 0.20 +/- 0.05 (13/64); of those, docked: 0.08 +/- 0.07 (1/13)
- Closest approach: median 59 m (10th to 90th percentile 11 to 127 m)
- Time from the order to the dock: median 11.0 s (10th to 90th percentile 11.0 to 11.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.00 (n=1)
- Damage dealt per drill: 3.3 +/- 2.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.00

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/32) | 0.06 |
| station | 0.00 (0/15) | 0.20 |
| citadel | 0.06 (1/17) | 0.06 |
| fighter | 0.00 (0/14) | 0.14 |
| strafer | 0.00 (0/19) | 0.16 |
| gunship | 0.07 (1/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.09 +/- 0.04 (6/64)
- Shot down first: 0.30 +/- 0.06 (19/64)
- Out of time: 0.61 +/- 0.06 (39/64)
- Docked, of those not shot down: 0.13 +/- 0.05 (6/45)
- Came within 30 m of the dock point: 0.34 +/- 0.06 (22/64); of those, docked: 0.27 +/- 0.09 (6/22)
- Closest approach: median 49 m (10th to 90th percentile 5 to 209 m)
- Time from the order to the dock: median 12.5 s (10th to 90th percentile 6.1 to 28.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.17 +/- 0.04 (n=6)
- Damage dealt per drill: 38.6 +/- 7.6 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.08

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.09 (3/33) | 0.36 |
| station | 0.14 (2/14) | 0.21 |
| citadel | 0.06 (1/17) | 0.24 |
| fighter | 0.00 (0/14) | 0.50 |
| strafer | 0.00 (0/8) | 0.50 |
| gunship | 0.19 (5/26) | 0.08 |
| bomber | 0.06 (1/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.868 | met |
| goto_lift | 0.660 | met |
| attack_target_hit | 0.914 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.016 | unset |
| dock_calm_lift | 0.000 | unset |
| dock_threat_docked | 0.094 | unset |
| dock_threat_docked_of_survivors | 0.133 | unset |
