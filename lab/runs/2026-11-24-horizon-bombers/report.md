# Horizon and bombers: report (lab/runs/2026-11-24-horizon-bombers)

Measurements only (± is 95%). The parent's column is its full-size eval; the periodic columns are at the quick sizes (64 drills a kind, 96 recall matches) and have no order cost or wins against the script. Order cost: 3 v 3, the checkpoint's side ordered (`nearest`) or not (`none`) against a free pilot; cost is nearest minus none, paired match by match. Bomber swap: the same matches with side X's first gunship as it is and as a bomber, the checkpoint on every strike slot; the change is paired match by match.

## h999: the long horizon (gamma 0.999), bombers and mixed teammates (parent `parent_dock2676`)

| Measure | parent_dock2676 | h999_1000 | h999_2000 | h999_3000 | h999_4000 | h999_5000 | h999_final_5334 |
|---|---|---|---|---|---|---|---|
| calm dock drills: docked | 0.38 ± 0.08 | 0.47 ± 0.12 | 0.56 ± 0.12 | 0.50 ± 0.12 | 0.66 ± 0.12 | 0.56 ± 0.12 | 0.67 ± 0.08 |
| calm dock drills: lift over the order hidden | 0.35 ± 0.09 | 0.44 ± 0.13 | 0.53 ± 0.13 | 0.47 ± 0.13 | 0.62 ± 0.12 | 0.50 ± 0.14 | 0.60 ± 0.09 |
| calm dock drills: shot down | 0.15 ± 0.06 | 0.06 ± 0.06 | 0.05 ± 0.05 | 0.05 ± 0.05 | 0.06 ± 0.06 | 0.11 ± 0.08 | 0.05 ± 0.04 |
| threat dock drills: docked | 0.14 ± 0.06 | 0.20 ± 0.10 | 0.30 ± 0.11 | 0.25 ± 0.11 | 0.33 ± 0.12 | 0.23 ± 0.10 | 0.23 ± 0.07 |
| threat dock drills: docked of survivors | 0.27 ± 0.11 | 0.34 ± 0.15 | 0.44 ± 0.15 | 0.37 ± 0.14 | 0.48 ± 0.15 | 0.38 ± 0.15 | 0.39 ± 0.11 |
| threat dock drills: shot down | 0.48 ± 0.09 | 0.41 ± 0.12 | 0.33 ± 0.12 | 0.33 ± 0.12 | 0.31 ± 0.11 | 0.38 ± 0.12 | 0.41 ± 0.09 |
| carrier battle: recall completion | 0.03 ± 0.01 | 0.07 ± 0.03 | 0.04 ± 0.02 | 0.06 ± 0.02 | 0.09 ± 0.03 | 0.09 ± 0.03 | 0.06 ± 0.01 |
| station assault: recall completion | 0.07 ± 0.01 | 0.10 ± 0.03 | 0.10 ± 0.03 | 0.10 ± 0.03 | 0.13 ± 0.03 | 0.12 ± 0.03 | 0.09 ± 0.02 |
| order drills: goto_arrival | 0.85 ± 0.04 | 0.89 ± 0.05 | 0.88 ± 0.05 | 0.87 ± 0.05 | 0.87 ± 0.06 | 0.92 ± 0.05 | 0.88 ± 0.04 |
| order drills: goto_lift | 0.65 ± 0.06 | 0.74 ± 0.08 | 0.76 ± 0.08 | 0.75 ± 0.08 | 0.74 ± 0.08 | 0.80 ± 0.07 | 0.71 ± 0.06 |
| order drills: attack_target_hit | 0.96 ± 0.02 | 0.96 ± 0.03 | 0.94 ± 0.04 | 0.95 ± 0.04 | 0.96 ± 0.03 | 0.95 ± 0.04 | 0.95 ± 0.03 |
| order drills: attack_side | 0.94 ± 0.03 | 0.96 ± 0.03 | 0.91 ± 0.05 | 0.95 ± 0.04 | 0.96 ± 0.03 | 0.95 ± 0.04 | 0.94 ± 0.03 |
| order drills: attack_flip | 0.88 ± 0.06 | 0.92 ± 0.07 | 0.83 ± 0.09 | 0.91 ± 0.07 | 0.92 ± 0.07 | 0.89 ± 0.08 | 0.89 ± 0.05 |
| order drills: defend_more_on_named | 0.88 ± 0.04 | 0.93 ± 0.04 | 0.86 ± 0.06 | 0.88 ± 0.06 | 0.91 ± 0.05 | 0.95 ± 0.04 | 0.91 ± 0.04 |
| order drills: defend_side | 0.95 ± 0.03 | 0.93 ± 0.04 | 0.94 ± 0.04 | 0.94 ± 0.04 | 0.94 ± 0.04 | 0.92 ± 0.05 | 0.95 ± 0.03 |
| order drills: defend_flip | 0.90 ± 0.05 | 0.86 ± 0.09 | 0.88 ± 0.08 | 0.88 ± 0.08 | 0.88 ± 0.08 | 0.84 ± 0.09 | 0.89 ± 0.05 |
| bomber swap, 3 v 3 deathmatch: score change | -0.16 ± 0.04 | -0.18 ± 0.08 | +0.01 ± 0.08 | -0.12 ± 0.08 | -0.07 ± 0.08 | -0.14 ± 0.08 | -0.11 ± 0.04 |
| bomber swap, 3 v 3 deathmatch: bomber's damage to capital ships | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bomber swap, 3 v 3 deathmatch: bomber's damage to strike craft | 30 | 74 | 81 | 91 | 116 | 122 | 147 |
| bomber swap, 3 v 3 deathmatch: gunship's damage to capital ships | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bomber swap, carrier battle: score change | -0.18 ± 0.09 | -0.12 ± 0.18 | +0.08 ± 0.15 | -0.17 ± 0.20 | +0.12 ± 0.17 | +0.08 ± 0.17 | -0.05 ± 0.09 |
| bomber swap, carrier battle: bomber's damage to capital ships | 36 | 56 | 50 | 78 | 47 | 84 | 74 |
| bomber swap, carrier battle: bomber's damage to strike craft | 55 | 89 | 147 | 173 | 169 | 191 | 174 |
| bomber swap, carrier battle: gunship's damage to capital ships | 152 | 135 | 104 | 175 | 161 | 146 | 133 |
| order cost v free followers_school_1052: none | 0.592 ± 0.028 | - | - | - | - | - | 0.227 ± 0.024 |
| order cost v free followers_school_1052: nearest | 0.230 ± 0.024 | - | - | - | - | - | 0.059 ± 0.014 |
| order cost v free followers_school_1052: cost (nearest − none, paired) | -0.362 ± 0.033 | - | - | - | - | - | -0.168 ± 0.025 |
| order cost v free followers_school_1052: nearest, target in arc | 0.12 | - | - | - | - | - | 0.05 |
| order cost v free followers_school_1052: nearest, ships lost a match | 0.53 | - | - | - | - | - | 0.18 |
| order cost v free followers_school_1052: nearest, dealt to target | 62 | - | - | - | - | - | 13 |
| order cost v free followers_school_1052: nearest, taken from target | 71 | - | - | - | - | - | 40 |
| vs script: carrier_battle | 0.89 ± 0.05 | - | - | - | - | - | 0.73 ± 0.06 |
| vs script: convoy_escort | 0.99 ± 0.01 | - | - | - | - | - | 0.99 ± 0.01 |
| vs script: station_assault | 0.61 ± 0.07 | - | - | - | - | - | 0.88 ± 0.05 |
| vs script: fleet_v1, all | 0.88 ± 0.04 | - | - | - | - | - | 0.73 ± 0.05 |
| vs script: fleet 1v1 | 1.00 ± 0.00 | - | - | - | - | - | 0.98 ± 0.04 |
| vs script: fleet 2v2 | 0.98 ± 0.04 | - | - | - | - | - | 0.83 ± 0.11 |
| vs script: fleet 3v3 | 0.92 ± 0.08 | - | - | - | - | - | 0.69 ± 0.13 |
| vs script: fleet 4v4 | 0.78 ± 0.14 | - | - | - | - | - | 0.44 ± 0.17 |

Training (log.jsonl), windows of updates:

| Updates | calm dock: docked (n) | threat dock: docked (n) | carrier: recalls / docks a match (n) | kite: pass (n) | kite: pilots lost | kite: dealt / taken, target | attack: pass | drill rows |
|---|---|---|---|---|---|---|---|---|
| 1-250 | 0.32 (777) | 0.08 (743) | 0.98 / 0.02 (410) | - | - | - / - | 0.84 | 0.17 |
| 251-500 | 0.40 (753) | 0.10 (764) | 1.02 / 0.04 (433) | - | - | - / - | 0.88 | 0.17 |
| 501-750 | 0.44 (765) | 0.11 (768) | 0.93 / 0.04 (415) | - | - | - / - | 0.85 | 0.16 |
| 751-1000 | 0.47 (718) | 0.16 (759) | 1.08 / 0.05 (429) | - | - | - / - | 0.89 | 0.17 |
| 1001-1250 | 0.48 (743) | 0.12 (693) | 1.07 / 0.06 (427) | - | - | - / - | 0.88 | 0.16 |
| 1251-1500 | 0.53 (763) | 0.12 (749) | 0.97 / 0.07 (421) | - | - | - / - | 0.88 | 0.16 |
| 1501-1750 | 0.52 (735) | 0.15 (751) | 1.00 / 0.08 (391) | - | - | - / - | 0.84 | 0.16 |
| 1751-2000 | 0.64 (742) | 0.17 (738) | 1.14 / 0.07 (430) | - | - | - / - | 0.82 | 0.16 |
| 2001-2250 | 0.62 (749) | 0.17 (698) | 1.21 / 0.06 (401) | - | - | - / - | 0.83 | 0.15 |
| 2251-2500 | 0.57 (706) | 0.19 (721) | 1.07 / 0.07 (377) | - | - | - / - | 0.91 | 0.16 |
| 2501-2750 | 0.55 (732) | 0.17 (720) | 0.98 / 0.05 (377) | - | - | - / - | 0.86 | 0.16 |
| 2751-3000 | 0.52 (766) | 0.19 (721) | 0.99 / 0.10 (389) | - | - | - / - | 0.89 | 0.17 |
| 3001-3250 | 0.57 (764) | 0.19 (760) | 1.01 / 0.06 (379) | - | - | - / - | 0.91 | 0.18 |
| 3251-3500 | 0.57 (740) | 0.17 (753) | 0.89 / 0.04 (388) | - | - | - / - | 0.81 | 0.17 |
| 3501-3750 | 0.64 (682) | 0.22 (679) | 1.10 / 0.07 (409) | - | - | - / - | 0.87 | 0.16 |
| 3751-4000 | 0.65 (713) | 0.21 (705) | 1.09 / 0.07 (438) | - | - | - / - | 0.90 | 0.16 |
| 4001-4250 | 0.60 (775) | 0.21 (716) | 0.97 / 0.05 (397) | - | - | - / - | 0.85 | 0.17 |
| 4251-4500 | 0.59 (737) | 0.25 (773) | 1.10 / 0.08 (382) | - | - | - / - | 0.84 | 0.17 |
| 4501-4750 | 0.63 (746) | 0.22 (748) | 1.04 / 0.06 (387) | - | - | - / - | 0.90 | 0.17 |
| 4751-5000 | 0.63 (779) | 0.21 (787) | 0.85 / 0.08 (402) | - | - | - / - | 0.89 | 0.17 |
| 5001-5250 | 0.67 (756) | 0.24 (790) | 0.87 / 0.07 (403) | - | - | - / - | 0.87 | 0.17 |
| 5251-5334 | 0.67 (257) | 0.27 (236) | 0.95 / 0.07 (154) | - | - | - / - | 0.86 | 0.15 |

## h995: the parent's horizon (gamma 0.995), bombers and mixed teammates (parent `parent_dock2676`)

| Measure | parent_dock2676 | h995_1000 | h995_2000 | h995_3000 | h995_4000 | h995_5000 | h995_final_5374 |
|---|---|---|---|---|---|---|---|
| calm dock drills: docked | 0.38 ± 0.08 | 0.47 ± 0.12 | 0.52 ± 0.12 | 0.62 ± 0.12 | 0.61 ± 0.12 | 0.48 ± 0.12 | 0.73 ± 0.08 |
| calm dock drills: lift over the order hidden | 0.35 ± 0.09 | 0.44 ± 0.13 | 0.52 ± 0.12 | 0.58 ± 0.13 | 0.58 ± 0.13 | 0.47 ± 0.13 | 0.73 ± 0.08 |
| calm dock drills: shot down | 0.15 ± 0.06 | 0.06 ± 0.06 | 0.11 ± 0.08 | 0.06 ± 0.06 | 0.16 ± 0.09 | 0.23 ± 0.10 | 0.05 ± 0.04 |
| threat dock drills: docked | 0.14 ± 0.06 | 0.14 ± 0.09 | 0.16 ± 0.09 | 0.30 ± 0.11 | 0.33 ± 0.12 | 0.31 ± 0.11 | 0.34 ± 0.08 |
| threat dock drills: docked of survivors | 0.27 ± 0.11 | 0.21 ± 0.12 | 0.26 ± 0.14 | 0.45 ± 0.15 | 0.58 ± 0.16 | 0.47 ± 0.15 | 0.61 ± 0.11 |
| threat dock drills: shot down | 0.48 ± 0.09 | 0.34 ± 0.12 | 0.41 ± 0.12 | 0.34 ± 0.12 | 0.44 ± 0.12 | 0.33 ± 0.12 | 0.45 ± 0.09 |
| carrier battle: recall completion | 0.03 ± 0.01 | 0.05 ± 0.02 | 0.04 ± 0.02 | 0.05 ± 0.02 | 0.07 ± 0.02 | 0.03 ± 0.02 | 0.05 ± 0.01 |
| station assault: recall completion | 0.07 ± 0.01 | 0.07 ± 0.02 | 0.08 ± 0.02 | 0.08 ± 0.02 | 0.13 ± 0.03 | 0.09 ± 0.02 | 0.08 ± 0.01 |
| order drills: goto_arrival | 0.85 ± 0.04 | 0.81 ± 0.07 | 0.88 ± 0.06 | 0.89 ± 0.05 | 0.88 ± 0.05 | 0.87 ± 0.06 | 0.92 ± 0.03 |
| order drills: goto_lift | 0.65 ± 0.06 | 0.65 ± 0.09 | 0.76 ± 0.08 | 0.76 ± 0.08 | 0.68 ± 0.09 | 0.72 ± 0.08 | 0.80 ± 0.05 |
| order drills: attack_target_hit | 0.96 ± 0.02 | 0.97 ± 0.03 | 0.95 ± 0.04 | 0.95 ± 0.04 | 0.96 ± 0.03 | 0.96 ± 0.03 | 0.91 ± 0.04 |
| order drills: attack_side | 0.94 ± 0.03 | 0.93 ± 0.04 | 0.94 ± 0.04 | 0.93 ± 0.04 | 0.91 ± 0.05 | 0.93 ± 0.04 | 0.94 ± 0.03 |
| order drills: attack_flip | 0.88 ± 0.06 | 0.86 ± 0.09 | 0.91 ± 0.07 | 0.88 ± 0.08 | 0.84 ± 0.09 | 0.86 ± 0.09 | 0.89 ± 0.05 |
| order drills: defend_more_on_named | 0.88 ± 0.04 | 0.89 ± 0.05 | 0.87 ± 0.06 | 0.91 ± 0.05 | 0.88 ± 0.06 | 0.88 ± 0.06 | 0.84 ± 0.04 |
| order drills: defend_side | 0.95 ± 0.03 | 0.91 ± 0.05 | 0.97 ± 0.03 | 0.99 ± 0.02 | 0.91 ± 0.05 | 0.92 ± 0.05 | 0.96 ± 0.02 |
| order drills: defend_flip | 0.90 ± 0.05 | 0.83 ± 0.09 | 0.94 ± 0.06 | 0.98 ± 0.03 | 0.83 ± 0.09 | 0.84 ± 0.09 | 0.92 ± 0.05 |
| bomber swap, 3 v 3 deathmatch: score change | -0.16 ± 0.04 | -0.13 ± 0.09 | +0.04 ± 0.09 | -0.02 ± 0.08 | -0.04 ± 0.08 | -0.07 ± 0.08 | -0.03 ± 0.04 |
| bomber swap, 3 v 3 deathmatch: bomber's damage to capital ships | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bomber swap, 3 v 3 deathmatch: bomber's damage to strike craft | 30 | 54 | 85 | 129 | 150 | 142 | 144 |
| bomber swap, 3 v 3 deathmatch: gunship's damage to capital ships | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bomber swap, carrier battle: score change | -0.18 ± 0.09 | -0.21 ± 0.17 | +0.02 ± 0.18 | +0.02 ± 0.19 | +0.02 ± 0.19 | +0.04 ± 0.18 | -0.08 ± 0.09 |
| bomber swap, carrier battle: bomber's damage to capital ships | 36 | 44 | 47 | 66 | 106 | 84 | 101 |
| bomber swap, carrier battle: bomber's damage to strike craft | 55 | 83 | 145 | 186 | 220 | 189 | 223 |
| bomber swap, carrier battle: gunship's damage to capital ships | 152 | 200 | 154 | 159 | 186 | 179 | 170 |
| order cost v free followers_school_1052: none | 0.592 ± 0.028 | - | - | - | - | - | 0.106 ± 0.018 |
| order cost v free followers_school_1052: nearest | 0.230 ± 0.024 | - | - | - | - | - | 0.085 ± 0.016 |
| order cost v free followers_school_1052: cost (nearest − none, paired) | -0.362 ± 0.033 | - | - | - | - | - | -0.021 ± 0.023 |
| order cost v free followers_school_1052: nearest, target in arc | 0.12 | - | - | - | - | - | 0.08 |
| order cost v free followers_school_1052: nearest, ships lost a match | 0.53 | - | - | - | - | - | 0.77 |
| order cost v free followers_school_1052: nearest, dealt to target | 62 | - | - | - | - | - | 47 |
| order cost v free followers_school_1052: nearest, taken from target | 71 | - | - | - | - | - | 83 |
| vs script: carrier_battle | 0.89 ± 0.05 | - | - | - | - | - | 0.66 ± 0.07 |
| vs script: convoy_escort | 0.99 ± 0.01 | - | - | - | - | - | 0.99 ± 0.01 |
| vs script: station_assault | 0.61 ± 0.07 | - | - | - | - | - | 0.93 ± 0.04 |
| vs script: fleet_v1, all | 0.88 ± 0.04 | - | - | - | - | - | 0.74 ± 0.05 |
| vs script: fleet 1v1 | 1.00 ± 0.00 | - | - | - | - | - | 1.00 ± 0.00 |
| vs script: fleet 2v2 | 0.98 ± 0.04 | - | - | - | - | - | 0.81 ± 0.11 |
| vs script: fleet 3v3 | 0.92 ± 0.08 | - | - | - | - | - | 0.77 ± 0.12 |
| vs script: fleet 4v4 | 0.78 ± 0.14 | - | - | - | - | - | 0.53 ± 0.17 |

Training (log.jsonl), windows of updates:

| Updates | calm dock: docked (n) | threat dock: docked (n) | carrier: recalls / docks a match (n) | kite: pass (n) | kite: pilots lost | kite: dealt / taken, target | attack: pass | drill rows |
|---|---|---|---|---|---|---|---|---|
| 1-250 | 0.35 (821) | 0.09 (790) | 1.03 / 0.06 (385) | - | - | - / - | 0.88 | 0.18 |
| 251-500 | 0.39 (728) | 0.12 (754) | 1.21 / 0.05 (395) | - | - | - / - | 0.87 | 0.15 |
| 501-750 | 0.40 (786) | 0.14 (755) | 1.18 / 0.05 (404) | - | - | - / - | 0.86 | 0.17 |
| 751-1000 | 0.40 (699) | 0.11 (709) | 1.18 / 0.03 (385) | - | - | - / - | 0.87 | 0.15 |
| 1001-1250 | 0.43 (751) | 0.16 (754) | 1.32 / 0.06 (363) | - | - | - / - | 0.83 | 0.17 |
| 1251-1500 | 0.47 (793) | 0.20 (778) | 1.25 / 0.04 (369) | - | - | - / - | 0.89 | 0.17 |
| 1501-1750 | 0.45 (740) | 0.18 (710) | 1.23 / 0.04 (368) | - | - | - / - | 0.83 | 0.16 |
| 1751-2000 | 0.43 (717) | 0.17 (768) | 1.10 / 0.04 (386) | - | - | - / - | 0.89 | 0.16 |
| 2001-2250 | 0.48 (736) | 0.19 (754) | 1.24 / 0.07 (383) | - | - | - / - | 0.81 | 0.16 |
| 2251-2500 | 0.54 (731) | 0.21 (701) | 1.22 / 0.07 (406) | - | - | - / - | 0.87 | 0.15 |
| 2501-2750 | 0.56 (776) | 0.19 (783) | 1.23 / 0.05 (447) | - | - | - / - | 0.80 | 0.15 |
| 2751-3000 | 0.55 (773) | 0.16 (754) | 1.05 / 0.05 (370) | - | - | - / - | 0.86 | 0.16 |
| 3001-3250 | 0.59 (697) | 0.21 (719) | 1.09 / 0.03 (421) | - | - | - / - | 0.87 | 0.14 |
| 3251-3500 | 0.60 (740) | 0.23 (722) | 1.21 / 0.03 (390) | - | - | - / - | 0.84 | 0.16 |
| 3501-3750 | 0.56 (726) | 0.23 (781) | 1.08 / 0.06 (394) | - | - | - / - | 0.81 | 0.16 |
| 3751-4000 | 0.59 (754) | 0.21 (766) | 1.29 / 0.07 (400) | - | - | - / - | 0.87 | 0.15 |
| 4001-4250 | 0.62 (779) | 0.22 (753) | 1.27 / 0.06 (389) | - | - | - / - | 0.85 | 0.16 |
| 4251-4500 | 0.57 (693) | 0.20 (747) | 1.06 / 0.05 (421) | - | - | - / - | 0.82 | 0.16 |
| 4501-4750 | 0.62 (716) | 0.24 (747) | 1.17 / 0.06 (439) | - | - | - / - | 0.87 | 0.15 |
| 4751-5000 | 0.55 (755) | 0.26 (725) | 1.32 / 0.07 (410) | - | - | - / - | 0.87 | 0.16 |
| 5001-5250 | 0.59 (742) | 0.26 (754) | 1.30 / 0.06 (412) | - | - | - / - | 0.84 | 0.15 |
| 5251-5374 | 0.69 (375) | 0.25 (371) | 1.18 / 0.04 (181) | - | - | - / - | 0.85 | 0.16 |

