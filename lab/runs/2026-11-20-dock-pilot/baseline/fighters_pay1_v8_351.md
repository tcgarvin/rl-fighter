# Order drills: fighters_pay1_v8_351

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_351.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.00 +/- 0.00 (0/128)
- Shot down first: 0.62 +/- 0.04 (80/128)
- Out of time: 0.38 +/- 0.04 (48/128)
- Docked, of those not shot down: 0.00 +/- 0.00 (0/48)
- Came within 30 m of the dock point: 0.06 +/- 0.02 (8/128); of those, docked: 0.00 +/- 0.00 (0/8)
- Closest approach: median 124 m (10th to 90th percentile 38 to 227 m)
- Time from the order to the dock: none docked
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (2/128)
- Hull at the dock (fraction of its maximum): 0.00 +/- 0.00 (n=0)
- Damage dealt per drill: 180.2 +/- 21.5 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.00

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/60) | 0.60 |
| station | 0.00 (0/31) | 0.61 |
| citadel | 0.00 (0/37) | 0.68 |
| fighter | 0.00 (0/31) | 0.55 |
| strafer | 0.00 (0/34) | 0.71 |
| gunship | 0.00 (0/32) | 0.72 |
| bomber | 0.00 (0/31) | 0.52 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.00 +/- 0.00 (0/128)
- Shot down first: 0.68 +/- 0.04 (87/128)
- Out of time: 0.32 +/- 0.04 (41/128)
- Docked, of those not shot down: 0.00 +/- 0.00 (0/41)
- Came within 30 m of the dock point: 0.05 +/- 0.02 (7/128); of those, docked: 0.00 +/- 0.00 (0/7)
- Closest approach: median 158 m (10th to 90th percentile 56 to 281 m)
- Time from the order to the dock: none docked
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (2/128)
- Hull at the dock (fraction of its maximum): 0.00 +/- 0.00 (n=0)
- Damage dealt per drill: 144.3 +/- 18.7 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: -0.02

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/64) | 0.66 |
| station | 0.00 (0/34) | 0.71 |
| citadel | 0.00 (0/30) | 0.70 |
| fighter | 0.00 (0/27) | 0.78 |
| strafer | 0.00 (0/26) | 0.85 |
| gunship | 0.00 (0/39) | 0.54 |
| bomber | 0.00 (0/36) | 0.64 |

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
| dock_calm_docked | 0.000 | unset |
| dock_calm_lift | 0.000 | unset |
| dock_threat_docked | 0.000 | unset |
| dock_threat_docked_of_survivors | 0.000 | unset |
