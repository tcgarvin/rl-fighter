**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.572

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.562 | 0.593 | 0.531 | 0.000 | 0.027 | 0.000 | 116 | 139 | time_limit 0.03, carrier_destroyed 0.97 |
| convoy_escort | 516 | 0.581 | 0.438 | 0.725 | 0.000 | 0.000 | 0.000 | 62 | 72 | eliminated 0.01, convoy_through 0.34, convoy_destroyed 0.64 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 59.7 | 44.0 | 0.03 | 0.292 | 0.81 | 0.0070 | 0.19 | 1.87 | 0.383 |
| carrier_battle | a | gunship | 860 | 393.5 | 166.6 | 0.33 | 0.287 | 0.84 | 0.0013 | 0.52 | 2.70 | 0.517 |
| carrier_battle | a | strafer | 1032 | 106.3 | 94.6 | 0.03 | 0.213 | 0.73 | 0.0121 | 0.24 | 2.42 | 0.506 |
| carrier_battle | a | all | 3956 | 144.4 | 83.8 | 0.10 | 0.260 | 0.80 | 0.0062 | 0.31 | 2.19 | 0.459 |
| carrier_battle | b | fighter | 2064 | 53.8 | 42.4 | 0.03 | 0.284 | 0.81 | 0.0095 | 0.17 | 1.81 | 0.372 |
| carrier_battle | b | gunship | 860 | 352.2 | 165.4 | 0.27 | 0.268 | 0.85 | 0.0015 | 0.49 | 2.66 | 0.523 |
| carrier_battle | b | strafer | 1032 | 89.6 | 91.1 | 0.04 | 0.200 | 0.69 | 0.0212 | 0.26 | 2.45 | 0.466 |
| carrier_battle | b | all | 3956 | 128.0 | 81.8 | 0.08 | 0.245 | 0.79 | 0.0096 | 0.30 | 2.16 | 0.448 |
| convoy_escort | a | fighter | 1462 | 168.2 | 65.3 | 0.35 | 0.375 | 0.89 | 0.0061 | 0.19 | 1.75 | 0.428 |
| convoy_escort | a | gunship | 430 | 410.8 | 163.1 | 0.72 | 0.250 | 0.90 | 0.0017 | 0.46 | 1.98 | 0.605 |
| convoy_escort | a | strafer | 688 | 109.4 | 38.8 | 0.59 | 0.138 | 0.59 | 0.0229 | 0.28 | 2.58 | 0.325 |
| convoy_escort | a | all | 2580 | 193.0 | 74.5 | 0.48 | 0.243 | 0.81 | 0.0097 | 0.27 | 2.01 | 0.438 |
| convoy_escort | b | fighter | 1462 | 153.9 | 68.7 | 0.34 | 0.363 | 0.86 | 0.0101 | 0.18 | 1.79 | 0.400 |
| convoy_escort | b | gunship | 430 | 406.8 | 175.5 | 0.63 | 0.267 | 0.91 | 0.0014 | 0.43 | 1.78 | 0.615 |
| convoy_escort | b | strafer | 688 | 73.2 | 36.1 | 0.62 | 0.113 | 0.49 | 0.0436 | 0.33 | 2.52 | 0.261 |
| convoy_escort | b | all | 2580 | 174.5 | 77.8 | 0.46 | 0.240 | 0.77 | 0.0179 | 0.27 | 1.98 | 0.403 |
