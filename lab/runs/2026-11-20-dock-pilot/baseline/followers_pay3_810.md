# Order drills: followers_pay3_810

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_810.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.03 +/- 0.02 (4/128)
- Shot down first: 0.09 +/- 0.02 (11/128)
- Out of time: 0.88 +/- 0.03 (113/128)
- Docked, of those not shot down: 0.03 +/- 0.02 (4/117)
- Came within 30 m of the dock point: 0.06 +/- 0.02 (8/128); of those, docked: 0.50 +/- 0.18 (4/8)
- Closest approach: median 105 m (10th to 90th percentile 33 to 183 m)
- Time from the order to the dock: median 26.4 s (10th to 90th percentile 17.3 to 31.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (3/128)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.04 (n=4)
- Damage dealt per drill: 29.2 +/- 9.1 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: +0.02

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.03 (2/60) | 0.07 |
| station | 0.03 (1/31) | 0.10 |
| citadel | 0.03 (1/37) | 0.11 |
| fighter | 0.00 (0/31) | 0.06 |
| strafer | 0.00 (0/34) | 0.09 |
| gunship | 0.09 (3/32) | 0.12 |
| bomber | 0.03 (1/31) | 0.06 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.05 +/- 0.02 (6/128)
- Shot down first: 0.55 +/- 0.04 (71/128)
- Out of time: 0.40 +/- 0.04 (51/128)
- Docked, of those not shot down: 0.11 +/- 0.04 (6/57)
- Came within 30 m of the dock point: 0.16 +/- 0.03 (21/128); of those, docked: 0.29 +/- 0.10 (6/21)
- Closest approach: median 115 m (10th to 90th percentile 25 to 244 m)
- Time from the order to the dock: median 13.3 s (10th to 90th percentile 6.0 to 22.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.05 +/- 0.02 (7/128)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.02 (n=6)
- Damage dealt per drill: 71.2 +/- 9.4 (n=128)
- Same drills, order hidden, docked: 0.04 +/- 0.02 (5/128)
- Lift from seeing the order: +0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.06 (4/64) | 0.55 |
| station | 0.03 (1/34) | 0.50 |
| citadel | 0.03 (1/30) | 0.63 |
| fighter | 0.00 (0/27) | 0.74 |
| strafer | 0.00 (0/26) | 0.77 |
| gunship | 0.10 (4/39) | 0.21 |
| bomber | 0.06 (2/36) | 0.64 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | n/a | unset |
| goto_lift | n/a | unset |
| attack_target_hit | n/a | unset |
| attack_side | n/a | unset |
| attack_flip | n/a | unset |
| defend_more_on_named | n/a | unset |
| defend_side | n/a | unset |
| defend_flip | n/a | unset |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.031 | unset |
| dock_calm_lift | 0.016 | unset |
| dock_threat_docked | 0.047 | unset |
| dock_threat_docked_of_survivors | 0.105 | unset |
