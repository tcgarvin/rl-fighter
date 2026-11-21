# Order drills: kitedock_1500

**Gate: pass.** kitedock_1500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.90 +/- 0.02 (245/271) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.90 +/- 0.02 (129/143; 10 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (21/130; 23 killed first, not counted)
- Lift from seeing the order: +0.74
- Near: 0.87 +/- 0.04 (65/75; 4 killed first, not counted)
- Far: 0.94 +/- 0.03 (64/68; 6 killed first, not counted)
- Enemies around the route: 0.89 +/- 0.04 (71/80; 5 killed first, not counted)
- Deadline in the order: 0.91 (88/97)
- No deadline (judged by 2x + 10 s): 0.89 (41/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.93 (26/28) |
| medium (2.5 to 4.5) | 0.89 (33/37) |
| loose (over 4.5) | 0.91 (29/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 143 | 97 | 46 | 15 |
| In time | 0.90 | 0.91 | 0.89 | 0.87 |
| Near miss (within 60 m) | 0.08 | 0.09 | 0.07 | 0.07 |
| At the enemy instead | 0.01 | 0.00 | 0.04 | 0.07 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (120/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.08 (16/19)
- Damage on the named target per pilot: 57.4 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 46.8 +/- 4.7 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.03 (110/128)
- On the named ward's attackers per pilot: 74.7 +/- 6.1 (n=128)
- On the other's per pilot: 7.4 +/- 2.0 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Dock, alone (64 drills)

- Docked: 0.08 +/- 0.03 (5/64)
- Shot down first: 0.03 +/- 0.02 (2/64)
- Out of time: 0.89 +/- 0.04 (57/64)
- Docked, of those not shot down: 0.08 +/- 0.03 (5/62)
- Came within 30 m of the dock point: 0.31 +/- 0.06 (20/64); of those, docked: 0.25 +/- 0.10 (5/20)
- Closest approach: median 41 m (10th to 90th percentile 9 to 80 m)
- Time from the order to the dock: median 16.6 s (10th to 90th percentile 13.1 to 24.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.06 (n=5)
- Damage dealt per drill: 1.2 +/- 1.2 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.05

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.03 (1/32) | 0.00 |
| station | 0.07 (1/15) | 0.07 |
| citadel | 0.18 (3/17) | 0.06 |
| fighter | 0.00 (0/14) | 0.07 |
| strafer | 0.11 (2/19) | 0.00 |
| gunship | 0.07 (1/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.12 +/- 0.04 (8/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.50 +/- 0.06 (32/64)
- Docked, of those not shot down: 0.20 +/- 0.06 (8/40)
- Came within 30 m of the dock point: 0.28 +/- 0.06 (18/64); of those, docked: 0.44 +/- 0.12 (8/18)
- Closest approach: median 52 m (10th to 90th percentile 6 to 179 m)
- Time from the order to the dock: median 32.2 s (10th to 90th percentile 12.9 to 35.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.04 (n=8)
- Damage dealt per drill: 31.3 +/- 8.6 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.09

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.09 (3/33) | 0.42 |
| station | 0.14 (2/14) | 0.36 |
| citadel | 0.18 (3/17) | 0.29 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.00 (0/8) | 0.75 |
| gunship | 0.27 (7/26) | 0.00 |
| bomber | 0.06 (1/16) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.902 | met |
| goto_lift | 0.741 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.859 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.078 | unset |
| dock_calm_lift | 0.047 | unset |
| dock_threat_docked | 0.125 | unset |
| dock_threat_docked_of_survivors | 0.200 | unset |
