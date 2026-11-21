# Order drills: kitedock_1000

**Gate: pass.** kitedock_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.90 +/- 0.02 (243/270) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.85 +/- 0.03 (121/142; 11 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (19/119; 34 killed first, not counted)
- Lift from seeing the order: +0.69
- Near: 0.80 +/- 0.05 (59/74; 5 killed first, not counted)
- Far: 0.91 +/- 0.03 (62/68; 6 killed first, not counted)
- Enemies around the route: 0.80 +/- 0.04 (64/80; 5 killed first, not counted)
- Deadline in the order: 0.88 (84/95)
- No deadline (judged by 2x + 10 s): 0.79 (37/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.74 (20/27) |
| medium (2.5 to 4.5) | 0.89 (34/38) |
| loose (over 4.5) | 1.00 (30/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 142 | 95 | 47 | 12 |
| In time | 0.85 | 0.88 | 0.79 | 0.92 |
| Near miss (within 60 m) | 0.12 | 0.11 | 0.15 | 0.08 |
| At the enemy instead | 0.01 | 0.00 | 0.04 | 0.00 |
| Neither | 0.01 | 0.01 | 0.02 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.91 +/- 0.02 (117/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 59.5 +/- 6.9 (n=128)
- On other enemies per pilot (not judged): 41.2 +/- 4.4 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (117/128)
- On the named ward's attackers per pilot: 76.8 +/- 6.6 (n=128)
- On the other's per pilot: 4.8 +/- 1.6 (n=128)
- Chose the named side: 0.99 +/- 0.01 (127/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.00 +/- 0.00 (0/128)
- Swap test, flipped with the order: 0.98 +/- 0.02 (63/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Dock, alone (64 drills)

- Docked: 0.08 +/- 0.03 (5/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.81 +/- 0.05 (52/64)
- Docked, of those not shot down: 0.09 +/- 0.04 (5/57)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.16 +/- 0.06 (5/32)
- Closest approach: median 30 m (10th to 90th percentile 1 to 97 m)
- Time from the order to the dock: median 24.2 s (10th to 90th percentile 16.7 to 28.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.20 +/- 0.05 (13/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.04 (n=5)
- Damage dealt per drill: 9.6 +/- 8.9 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.03

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.03 (1/32) | 0.12 |
| station | 0.07 (1/15) | 0.20 |
| citadel | 0.18 (3/17) | 0.00 |
| fighter | 0.00 (0/14) | 0.21 |
| strafer | 0.00 (0/19) | 0.16 |
| gunship | 0.20 (3/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.20 +/- 0.05 (13/64)
- Shot down first: 0.45 +/- 0.06 (29/64)
- Out of time: 0.34 +/- 0.06 (22/64)
- Docked, of those not shot down: 0.37 +/- 0.08 (13/35)
- Came within 30 m of the dock point: 0.48 +/- 0.06 (31/64); of those, docked: 0.42 +/- 0.09 (13/31)
- Closest approach: median 31 m (10th to 90th percentile 1 to 185 m)
- Time from the order to the dock: median 17.5 s (10th to 90th percentile 10.5 to 31.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.03 (n=13)
- Damage dealt per drill: 41.9 +/- 10.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.24 (8/33) | 0.48 |
| station | 0.14 (2/14) | 0.43 |
| citadel | 0.18 (3/17) | 0.41 |
| fighter | 0.00 (0/14) | 0.86 |
| strafer | 0.00 (0/8) | 0.75 |
| gunship | 0.46 (12/26) | 0.04 |
| bomber | 0.06 (1/16) | 0.62 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.852 | met |
| goto_lift | 0.692 | met |
| attack_target_hit | 0.914 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.914 | met |
| defend_side | 0.992 | met |
| defend_flip | 0.984 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.078 | unset |
| dock_calm_lift | 0.031 | unset |
| dock_threat_docked | 0.203 | unset |
| dock_threat_docked_of_survivors | 0.371 | unset |
