# Order drills: nobomb_2000

**Gate: pass.** nobomb_2000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.02 (242/272) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (125/144; 9 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (21/128; 25 killed first, not counted)
- Lift from seeing the order: +0.70
- Near: 0.83 +/- 0.04 (63/76; 3 killed first, not counted)
- Far: 0.91 +/- 0.03 (62/68; 6 killed first, not counted)
- Enemies around the route: 0.81 +/- 0.04 (64/79; 6 killed first, not counted)
- Deadline in the order: 0.91 (88/97)
- No deadline (judged by 2x + 10 s): 0.79 (37/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.78 (21/27) |
| medium (2.5 to 4.5) | 0.92 (35/38) |
| loose (over 4.5) | 1.00 (32/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 144 | 97 | 47 | 12 |
| In time | 0.87 | 0.91 | 0.79 | 0.75 |
| Near miss (within 60 m) | 0.12 | 0.08 | 0.19 | 0.17 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.97 +/- 0.02 (124/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 61.1 +/- 6.1 (n=128)
- On other enemies per pilot (not judged): 42.9 +/- 4.7 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.03 (116/128)
- On the named ward's attackers per pilot: 77.3 +/- 6.4 (n=128)
- On the other's per pilot: 4.8 +/- 1.6 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.52 +/- 0.06 (33/64)
- Shot down first: 0.12 +/- 0.04 (8/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.59 +/- 0.07 (33/56)
- Came within 30 m of the dock point: 0.70 +/- 0.06 (45/64); of those, docked: 0.73 +/- 0.07 (33/45)
- Closest approach: median 10 m (10th to 90th percentile 2 to 44 m)
- Time from the order to the dock: median 11.3 s (10th to 90th percentile 7.0 to 18.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.16 +/- 0.05 (10/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=33)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.47

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (19/32) | 0.03 |
| station | 0.60 (9/15) | 0.07 |
| citadel | 0.29 (5/17) | 0.35 |
| fighter | 0.50 (7/14) | 0.36 |
| strafer | 0.89 (17/19) | 0.11 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.19 +/- 0.05 (12/64)
- Shot down first: 0.31 +/- 0.06 (20/64)
- Out of time: 0.50 +/- 0.06 (32/64)
- Docked, of those not shot down: 0.27 +/- 0.07 (12/44)
- Came within 30 m of the dock point: 0.53 +/- 0.06 (34/64); of those, docked: 0.35 +/- 0.08 (12/34)
- Closest approach: median 29 m (10th to 90th percentile 3 to 179 m)
- Time from the order to the dock: median 21.2 s (10th to 90th percentile 8.7 to 33.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.16 +/- 0.05 (10/64)
- Hull at the dock (fraction of its maximum): 0.23 +/- 0.04 (n=12)
- Damage dealt per drill: 31.0 +/- 10.6 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.16

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.33 |
| station | 0.00 (0/14) | 0.21 |
| citadel | 0.29 (5/17) | 0.35 |
| fighter | 0.14 (2/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.27 (7/26) | 0.00 |
| bomber | 0.06 (1/16) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.868 | met |
| goto_lift | 0.704 | met |
| attack_target_hit | 0.969 | met |
| attack_side | 0.953 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.516 | unset |
| dock_calm_lift | 0.469 | unset |
| dock_threat_docked | 0.188 | unset |
| dock_threat_docked_of_survivors | 0.273 | unset |
