# Order drills: fighters_pay1_462

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_462.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.01 +/- 0.01 (1/128)
- Shot down first: 0.78 +/- 0.04 (100/128)
- Out of time: 0.21 +/- 0.04 (27/128)
- Docked, of those not shot down: 0.04 +/- 0.04 (1/28)
- Came within 30 m of the dock point: 0.05 +/- 0.02 (6/128); of those, docked: 0.17 +/- 0.15 (1/6)
- Closest approach: median 159 m (10th to 90th percentile 55 to 246 m)
- Time from the order to the dock: median 5.8 s (10th to 90th percentile 5.8 to 5.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (2/128)
- Hull at the dock (fraction of its maximum): 0.45 +/- 0.00 (n=1)
- Damage dealt per drill: 300.8 +/- 36.7 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/60) | 0.75 |
| station | 0.03 (1/31) | 0.81 |
| citadel | 0.00 (0/37) | 0.81 |
| fighter | 0.00 (0/31) | 1.00 |
| strafer | 0.00 (0/34) | 1.00 |
| gunship | 0.00 (0/32) | 0.38 |
| bomber | 0.03 (1/31) | 0.74 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.01 +/- 0.01 (1/128)
- Shot down first: 0.74 +/- 0.04 (95/128)
- Out of time: 0.25 +/- 0.04 (32/128)
- Docked, of those not shot down: 0.03 +/- 0.03 (1/33)
- Came within 30 m of the dock point: 0.08 +/- 0.02 (10/128); of those, docked: 0.10 +/- 0.09 (1/10)
- Closest approach: median 166 m (10th to 90th percentile 39 to 277 m)
- Time from the order to the dock: median 8.7 s (10th to 90th percentile 8.7 to 8.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.01 +/- 0.01 (1/128)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.00 (n=1)
- Damage dealt per drill: 231.0 +/- 32.0 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.02 (1/64) | 0.70 |
| station | 0.00 (0/34) | 0.76 |
| citadel | 0.00 (0/30) | 0.80 |
| fighter | 0.00 (0/27) | 0.96 |
| strafer | 0.00 (0/26) | 1.00 |
| gunship | 0.03 (1/39) | 0.26 |
| bomber | 0.00 (0/36) | 0.92 |

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
| dock_calm_docked | 0.008 | unset |
| dock_calm_lift | 0.008 | unset |
| dock_threat_docked | 0.008 | unset |
| dock_threat_docked_of_survivors | 0.030 | unset |
