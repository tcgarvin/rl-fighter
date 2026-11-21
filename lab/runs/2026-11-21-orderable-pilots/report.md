# Orderable pilots: report (lab/runs/2026-11-21-orderable-pilots)

Measurements only (± is 95%). The parent's column is its full-size eval; the periodic columns are at the quick sizes (64 drills a kind, 96 recall matches) and have no order cost or wins against the script. Order cost: 3 v 3, the checkpoint's side ordered (`nearest`, `scripted`) or not (`none`) against a free pilot; cost is nearest minus none, paired match by match.

## kitedock: kite 2205 (orderable) learning to dock (parent `parent_kite2205`)

| Measure | parent_kite2205 | kitedock_500 | kitedock_1000 | kitedock_1500 | kitedock_2000 | kitedock_final_2293 |
|---|---|---|---|---|---|---|
| calm dock drills: docked | 0.04 ± 0.03 | 0.02 ± 0.03 | 0.08 ± 0.07 | 0.08 ± 0.07 | 0.19 ± 0.10 | 0.18 ± 0.07 |
| calm dock drills: lift over the order hidden | 0.03 ± 0.04 | 0.00 ± 0.04 | 0.03 ± 0.08 | 0.05 ± 0.08 | 0.17 ± 0.10 | 0.16 ± 0.07 |
| calm dock drills: shot down | 0.21 ± 0.07 | 0.09 ± 0.07 | 0.11 ± 0.08 | 0.03 ± 0.04 | 0.06 ± 0.06 | 0.12 ± 0.06 |
| threat dock drills: docked | 0.02 ± 0.03 | 0.09 ± 0.07 | 0.20 ± 0.10 | 0.12 ± 0.08 | 0.17 ± 0.09 | 0.09 ± 0.05 |
| threat dock drills: docked of survivors | 0.05 ± 0.05 | 0.13 ± 0.10 | 0.37 ± 0.16 | 0.20 ± 0.12 | 0.26 ± 0.13 | 0.14 ± 0.08 |
| threat dock drills: shot down | 0.51 ± 0.09 | 0.30 ± 0.11 | 0.45 ± 0.12 | 0.38 ± 0.12 | 0.33 ± 0.12 | 0.39 ± 0.08 |
| carrier battle: recall completion | 0.03 ± 0.01 | 0.03 ± 0.02 | 0.02 ± 0.01 | 0.02 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.01 |
| station assault: recall completion | 0.02 ± 0.01 | 0.03 ± 0.02 | 0.05 ± 0.02 | 0.05 ± 0.02 | 0.06 ± 0.02 | 0.03 ± 0.01 |
| order drills: goto_arrival | 0.89 ± 0.03 | 0.87 ± 0.06 | 0.85 ± 0.06 | 0.90 ± 0.05 | 0.88 ± 0.05 | 0.86 ± 0.04 |
| order drills: goto_lift | 0.74 ± 0.05 | 0.66 ± 0.09 | 0.69 ± 0.09 | 0.74 ± 0.08 | 0.73 ± 0.08 | 0.70 ± 0.06 |
| order drills: attack_target_hit | 0.95 ± 0.03 | 0.91 ± 0.05 | 0.91 ± 0.05 | 0.94 ± 0.04 | 0.96 ± 0.03 | 0.96 ± 0.02 |
| order drills: attack_side | 0.98 ± 0.02 | 0.96 ± 0.03 | 0.96 ± 0.03 | 0.96 ± 0.03 | 0.98 ± 0.03 | 0.97 ± 0.02 |
| order drills: attack_flip | 0.96 ± 0.03 | 0.92 ± 0.07 | 0.92 ± 0.07 | 0.92 ± 0.07 | 0.95 ± 0.05 | 0.94 ± 0.04 |
| order drills: defend_more_on_named | 0.91 ± 0.04 | 0.88 ± 0.06 | 0.91 ± 0.05 | 0.86 ± 0.06 | 0.84 ± 0.06 | 0.89 ± 0.04 |
| order drills: defend_side | 0.97 ± 0.02 | 0.96 ± 0.03 | 0.99 ± 0.02 | 0.95 ± 0.04 | 0.95 ± 0.04 | 0.96 ± 0.02 |
| order drills: defend_flip | 0.95 ± 0.04 | 0.92 ± 0.07 | 0.98 ± 0.03 | 0.89 ± 0.08 | 0.91 ± 0.07 | 0.92 ± 0.05 |
| order cost v free followers_school_1052: none | 0.566 ± 0.029 | - | - | - | - | 0.339 ± 0.027 |
| order cost v free followers_school_1052: nearest | 0.421 ± 0.028 | - | - | - | - | 0.135 ± 0.020 |
| order cost v free followers_school_1052: scripted | 0.342 ± 0.027 | - | - | - | - | 0.153 ± 0.021 |
| order cost v free followers_school_1052: cost (nearest − none, paired) | -0.145 ± 0.039 | - | - | - | - | -0.204 ± 0.031 |
| order cost v free followers_school_1052: nearest, target in arc | 0.25 | - | - | - | - | 0.11 |
| order cost v free followers_school_1052: nearest, ships lost a match | 0.84 | - | - | - | - | 0.72 |
| order cost v free followers_school_1052: nearest, dealt to target | 146 | - | - | - | - | 54 |
| order cost v free followers_school_1052: nearest, taken from target | 139 | - | - | - | - | 96 |
| order cost v free f995_701: none | 0.631 ± 0.028 | - | - | - | - | 0.143 ± 0.020 |
| order cost v free f995_701: nearest | 0.465 ± 0.029 | - | - | - | - | 0.175 ± 0.022 |
| order cost v free f995_701: scripted | 0.438 ± 0.029 | - | - | - | - | 0.208 ± 0.023 |
| order cost v free f995_701: cost (nearest − none, paired) | -0.166 ± 0.039 | - | - | - | - | +0.032 ± 0.030 |
| order cost v free f995_701: nearest, target in arc | 0.13 | - | - | - | - | 0.13 |
| order cost v free f995_701: nearest, ships lost a match | 0.87 | - | - | - | - | 0.72 |
| order cost v free f995_701: nearest, dealt to target | 136 | - | - | - | - | 72 |
| order cost v free f995_701: nearest, taken from target | 105 | - | - | - | - | 108 |
| vs script: carrier_battle | 0.92 ± 0.04 | - | - | - | - | 0.82 ± 0.05 |
| vs script: convoy_escort | 0.99 ± 0.01 | - | - | - | - | 0.99 ± 0.01 |
| vs script: station_assault | 0.59 ± 0.07 | - | - | - | - | 0.54 ± 0.07 |
| vs script: fleet_v1, all | 0.83 ± 0.05 | - | - | - | - | 0.81 ± 0.05 |
| vs script: fleet 1v1 | 0.97 ± 0.05 | - | - | - | - | 0.98 ± 0.04 |
| vs script: fleet 2v2 | 0.74 ± 0.12 | - | - | - | - | 0.77 ± 0.12 |
| vs script: fleet 3v3 | 0.85 ± 0.10 | - | - | - | - | 0.85 ± 0.10 |
| vs script: fleet 4v4 | 0.89 ± 0.11 | - | - | - | - | 0.72 ± 0.16 |

Training (log.jsonl), windows of updates:

| Updates | calm dock: docked (n) | threat dock: docked (n) | carrier: recalls / docks a match (n) | kite: pass (n) | kite: pilots lost | kite: dealt / taken, target | attack: pass | drill rows |
|---|---|---|---|---|---|---|---|---|
| 1-250 | 0.05 (647) | 0.02 (668) | 1.47 / 0.03 (418) | 0.89 (364) | 0.92 | 110 / 169 | 0.96 | 0.15 |
| 251-500 | 0.03 (637) | 0.02 (650) | 1.48 / 0.05 (469) | 0.85 (352) | 0.88 | 98 / 157 | 0.94 | 0.15 |
| 501-750 | 0.06 (635) | 0.06 (619) | 1.43 / 0.03 (451) | 0.83 (355) | 0.90 | 101 / 167 | 0.91 | 0.15 |
| 751-1000 | 0.09 (682) | 0.06 (624) | 1.52 / 0.02 (426) | 0.84 (373) | 0.87 | 100 / 163 | 0.94 | 0.15 |
| 1001-1250 | 0.12 (638) | 0.06 (630) | 1.32 / 0.03 (440) | 0.86 (341) | 0.90 | 109 / 165 | 0.93 | 0.14 |
| 1251-1500 | 0.13 (623) | 0.06 (693) | 1.43 / 0.05 (426) | 0.84 (381) | 0.88 | 108 / 160 | 0.91 | 0.15 |
| 1501-1750 | 0.15 (644) | 0.08 (673) | 1.57 / 0.04 (441) | 0.86 (367) | 0.88 | 115 / 157 | 0.92 | 0.15 |
| 1751-2000 | 0.18 (650) | 0.12 (656) | 1.45 / 0.04 (462) | 0.84 (397) | 0.91 | 106 / 163 | 0.93 | 0.15 |
| 2001-2250 | 0.21 (657) | 0.09 (615) | 1.34 / 0.03 (443) | 0.86 (366) | 0.89 | 115 / 166 | 0.93 | 0.15 |
| 2251-2293 | 0.23 (102) | 0.07 (108) | 1.30 / 0.04 (73) | 0.83 (63) | 0.85 | 84 / 172 | 0.90 | 0.15 |

## dockkite: dock600 2624 (dockable) learning kite drills (parent `parent_dock2624`)

| Measure | parent_dock2624 | dockkite_500 | dockkite_1000 | dockkite_1500 | dockkite_2000 | dockkite_final_2286 |
|---|---|---|---|---|---|---|
| calm dock drills: docked | 0.57 ± 0.09 | 0.53 ± 0.12 | 0.44 ± 0.12 | 0.48 ± 0.12 | 0.38 ± 0.12 | 0.44 ± 0.09 |
| calm dock drills: lift over the order hidden | 0.52 ± 0.09 | 0.52 ± 0.13 | 0.39 ± 0.13 | 0.42 ± 0.14 | 0.34 ± 0.13 | 0.44 ± 0.09 |
| calm dock drills: shot down | 0.09 ± 0.05 | 0.08 ± 0.07 | 0.08 ± 0.07 | 0.06 ± 0.06 | 0.20 ± 0.10 | 0.16 ± 0.06 |
| threat dock drills: docked | 0.27 ± 0.08 | 0.25 ± 0.11 | 0.22 ± 0.10 | 0.33 ± 0.12 | 0.20 ± 0.10 | 0.17 ± 0.07 |
| threat dock drills: docked of survivors | 0.53 ± 0.12 | 0.40 ± 0.15 | 0.38 ± 0.16 | 0.50 ± 0.15 | 0.35 ± 0.15 | 0.31 ± 0.11 |
| threat dock drills: shot down | 0.50 ± 0.09 | 0.38 ± 0.12 | 0.42 ± 0.12 | 0.34 ± 0.12 | 0.42 ± 0.12 | 0.44 ± 0.09 |
| carrier battle: recall completion | 0.05 ± 0.01 | 0.04 ± 0.02 | 0.03 ± 0.02 | 0.03 ± 0.02 | 0.03 ± 0.01 | 0.02 ± 0.01 |
| station assault: recall completion | 0.08 ± 0.01 | 0.04 ± 0.02 | 0.05 ± 0.02 | 0.05 ± 0.02 | 0.04 ± 0.02 | 0.05 ± 0.01 |
| order drills: goto_arrival | 0.84 ± 0.04 | 0.84 ± 0.06 | 0.79 ± 0.07 | 0.85 ± 0.06 | 0.83 ± 0.06 | 0.84 ± 0.04 |
| order drills: goto_lift | 0.68 ± 0.06 | 0.69 ± 0.09 | 0.66 ± 0.09 | 0.73 ± 0.08 | 0.73 ± 0.08 | 0.69 ± 0.06 |
| order drills: attack_target_hit | 0.95 ± 0.03 | 0.93 ± 0.04 | 0.91 ± 0.05 | 0.95 ± 0.04 | 0.95 ± 0.04 | 0.96 ± 0.02 |
| order drills: attack_side | 0.94 ± 0.03 | 0.94 ± 0.04 | 0.97 ± 0.03 | 0.95 ± 0.04 | 0.89 ± 0.05 | 0.89 ± 0.04 |
| order drills: attack_flip | 0.88 ± 0.06 | 0.88 ± 0.08 | 0.94 ± 0.06 | 0.91 ± 0.07 | 0.80 ± 0.10 | 0.80 ± 0.07 |
| order drills: defend_more_on_named | 0.84 ± 0.04 | 0.85 ± 0.06 | 0.86 ± 0.06 | 0.88 ± 0.06 | 0.85 ± 0.06 | 0.83 ± 0.05 |
| order drills: defend_side | 0.93 ± 0.03 | 0.95 ± 0.04 | 0.91 ± 0.05 | 0.86 ± 0.06 | 0.92 ± 0.05 | 0.88 ± 0.04 |
| order drills: defend_flip | 0.86 ± 0.06 | 0.91 ± 0.07 | 0.83 ± 0.09 | 0.73 ± 0.11 | 0.84 ± 0.09 | 0.78 ± 0.07 |
| order cost v free followers_school_1052: none | 0.333 ± 0.027 | - | - | - | - | 0.344 ± 0.027 |
| order cost v free followers_school_1052: nearest | 0.236 ± 0.025 | - | - | - | - | 0.404 ± 0.028 |
| order cost v free followers_school_1052: scripted | 0.239 ± 0.025 | - | - | - | - | 0.390 ± 0.028 |
| order cost v free followers_school_1052: cost (nearest − none, paired) | -0.097 ± 0.036 | - | - | - | - | +0.060 ± 0.034 |
| order cost v free followers_school_1052: nearest, target in arc | 0.13 | - | - | - | - | 0.08 |
| order cost v free followers_school_1052: nearest, ships lost a match | 0.98 | - | - | - | - | 0.54 |
| order cost v free followers_school_1052: nearest, dealt to target | 106 | - | - | - | - | 68 |
| order cost v free followers_school_1052: nearest, taken from target | 135 | - | - | - | - | 85 |
| order cost v free f995_701: none | 0.433 ± 0.029 | - | - | - | - | 0.417 ± 0.028 |
| order cost v free f995_701: nearest | 0.539 ± 0.029 | - | - | - | - | 0.296 ± 0.026 |
| order cost v free f995_701: scripted | 0.539 ± 0.029 | - | - | - | - | 0.339 ± 0.027 |
| order cost v free f995_701: cost (nearest − none, paired) | +0.105 ± 0.041 | - | - | - | - | -0.120 ± 0.038 |
| order cost v free f995_701: nearest, target in arc | 0.13 | - | - | - | - | 0.12 |
| order cost v free f995_701: nearest, ships lost a match | 0.83 | - | - | - | - | 0.71 |
| order cost v free f995_701: nearest, dealt to target | 134 | - | - | - | - | 97 |
| order cost v free f995_701: nearest, taken from target | 117 | - | - | - | - | 110 |
| vs script: carrier_battle | 0.82 ± 0.05 | - | - | - | - | 0.90 ± 0.04 |
| vs script: convoy_escort | 1.00 ± 0.00 | - | - | - | - | 1.00 ± 0.00 |
| vs script: station_assault | 0.66 ± 0.07 | - | - | - | - | 0.64 ± 0.07 |
| vs script: fleet_v1, all | 0.83 ± 0.05 | - | - | - | - | 0.82 ± 0.05 |
| vs script: fleet 1v1 | 0.98 ± 0.04 | - | - | - | - | 0.92 ± 0.08 |
| vs script: fleet 2v2 | 0.90 ± 0.09 | - | - | - | - | 0.92 ± 0.08 |
| vs script: fleet 3v3 | 0.90 ± 0.09 | - | - | - | - | 0.98 ± 0.04 |
| vs script: fleet 4v4 | 0.75 ± 0.15 | - | - | - | - | 0.66 ± 0.16 |

Training (log.jsonl), windows of updates:

| Updates | calm dock: docked (n) | threat dock: docked (n) | carrier: recalls / docks a match (n) | kite: pass (n) | kite: pilots lost | kite: dealt / taken, target | attack: pass | drill rows |
|---|---|---|---|---|---|---|---|---|
| 1-250 | 0.52 (666) | 0.17 (690) | 1.66 / 0.06 (439) | 0.90 (385) | 0.88 | 111 / 149 | 0.95 | 0.15 |
| 251-500 | 0.51 (709) | 0.16 (581) | 1.60 / 0.04 (453) | 0.91 (351) | 0.91 | 121 / 153 | 0.93 | 0.14 |
| 501-750 | 0.48 (702) | 0.17 (708) | 1.66 / 0.03 (459) | 0.91 (352) | 0.87 | 102 / 152 | 0.94 | 0.15 |
| 751-1000 | 0.46 (653) | 0.16 (617) | 1.61 / 0.05 (423) | 0.88 (364) | 0.89 | 102 / 144 | 0.92 | 0.15 |
| 1001-1250 | 0.56 (646) | 0.18 (626) | 1.58 / 0.06 (408) | 0.88 (370) | 0.89 | 109 / 150 | 0.92 | 0.15 |
| 1251-1500 | 0.50 (607) | 0.15 (607) | 1.68 / 0.05 (460) | 0.89 (383) | 0.87 | 116 / 144 | 0.92 | 0.14 |
| 1501-1750 | 0.47 (692) | 0.22 (680) | 1.69 / 0.04 (444) | 0.90 (368) | 0.85 | 107 / 141 | 0.92 | 0.16 |
| 1751-2000 | 0.44 (616) | 0.17 (654) | 1.58 / 0.05 (479) | 0.89 (354) | 0.88 | 111 / 142 | 0.95 | 0.14 |
| 2001-2250 | 0.44 (718) | 0.17 (670) | 1.64 / 0.02 (434) | 0.87 (390) | 0.86 | 107 / 144 | 0.95 | 0.16 |
| 2251-2286 | 0.51 (93) | 0.17 (96) | 1.54 / 0.02 (82) | 0.95 (38) | 0.86 | 109 / 175 | 0.90 | 0.15 |

