# Order drills: fighters_pay1_school_821

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_821.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.00 +/- 0.00 (0/128)
- Shot down first: 0.59 +/- 0.04 (76/128)
- Out of time: 0.41 +/- 0.04 (52/128)
- Docked, of those not shot down: 0.00 +/- 0.00 (0/52)
- Came within 30 m of the dock point: 0.12 +/- 0.03 (15/128); of those, docked: 0.00 +/- 0.00 (0/15)
- Closest approach: median 106 m (10th to 90th percentile 29 to 233 m)
- Time from the order to the dock: none docked
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (3/128)
- Hull at the dock (fraction of its maximum): 0.00 +/- 0.00 (n=0)
- Damage dealt per drill: 151.4 +/- 18.1 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: -0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/60) | 0.55 |
| station | 0.00 (0/31) | 0.71 |
| citadel | 0.00 (0/37) | 0.57 |
| fighter | 0.00 (0/31) | 0.55 |
| strafer | 0.00 (0/34) | 0.62 |
| gunship | 0.00 (0/32) | 0.59 |
| bomber | 0.00 (0/31) | 0.61 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.00 +/- 0.00 (0/128)
- Shot down first: 0.70 +/- 0.04 (89/128)
- Out of time: 0.30 +/- 0.04 (39/128)
- Docked, of those not shot down: 0.00 +/- 0.00 (0/39)
- Came within 30 m of the dock point: 0.12 +/- 0.03 (16/128); of those, docked: 0.00 +/- 0.00 (0/16)
- Closest approach: median 146 m (10th to 90th percentile 27 to 274 m)
- Time from the order to the dock: none docked
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.04 +/- 0.02 (5/128)
- Hull at the dock (fraction of its maximum): 0.00 +/- 0.00 (n=0)
- Damage dealt per drill: 155.5 +/- 19.9 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.00

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/64) | 0.69 |
| station | 0.00 (0/34) | 0.71 |
| citadel | 0.00 (0/30) | 0.70 |
| fighter | 0.00 (0/27) | 0.89 |
| strafer | 0.00 (0/26) | 0.92 |
| gunship | 0.00 (0/39) | 0.49 |
| bomber | 0.00 (0/36) | 0.61 |

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
| dock_calm_lift | -0.008 | unset |
| dock_threat_docked | 0.000 | unset |
| dock_threat_docked_of_survivors | 0.000 | unset |
