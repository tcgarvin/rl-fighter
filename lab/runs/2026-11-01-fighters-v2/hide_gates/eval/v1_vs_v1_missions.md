**policy:ppo_bc_400.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.498

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.496 | 0.504 | 0.488 | 0.000 | 0.019 | 0.000 | 115 | 139 | time_limit 0.02, carrier_destroyed 0.98 |
| convoy_escort | 516 | 0.500 | 0.996 | 0.004 | 0.000 | 0.000 | 0.000 | 75 | 75 | eliminated 0.19, convoy_through 0.81, convoy_destroyed 0.00 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 55.1 | 45.5 | 0.03 | 0.286 | 0.81 | 0.0129 | 0.17 | 1.87 | 0.369 |
| carrier_battle | a | gunship | 860 | 367.0 | 160.5 | 0.30 | 0.265 | 0.86 | 0.0020 | 0.50 | 2.82 | 0.518 |
| carrier_battle | a | strafer | 1032 | 94.4 | 99.5 | 0.05 | 0.210 | 0.68 | 0.0288 | 0.27 | 2.50 | 0.446 |
| carrier_battle | a | all | 3956 | 133.1 | 84.6 | 0.09 | 0.248 | 0.80 | 0.0129 | 0.31 | 2.24 | 0.440 |
| carrier_battle | b | fighter | 2064 | 54.7 | 45.4 | 0.03 | 0.281 | 0.81 | 0.0110 | 0.17 | 1.87 | 0.368 |
| carrier_battle | b | gunship | 860 | 377.9 | 165.4 | 0.32 | 0.267 | 0.85 | 0.0016 | 0.50 | 2.88 | 0.515 |
| carrier_battle | b | strafer | 1032 | 93.0 | 95.2 | 0.05 | 0.205 | 0.69 | 0.0224 | 0.27 | 2.50 | 0.462 |
| carrier_battle | b | all | 3956 | 135.0 | 84.5 | 0.10 | 0.247 | 0.80 | 0.0103 | 0.31 | 2.26 | 0.443 |
| convoy_escort | a | fighter | 1548 | 79.5 | 66.6 | 0.18 | 0.243 | 0.69 | 0.0150 | 0.19 | 1.69 | 0.350 |
| convoy_escort | a | gunship | 516 | 209.1 | 131.9 | 0.53 | 0.171 | 0.72 | 0.0022 | 0.44 | 1.90 | 0.564 |
| convoy_escort | a | strafer | 1032 | 82.6 | 73.8 | 0.53 | 0.134 | 0.51 | 0.0469 | 0.36 | 2.84 | 0.266 |
| convoy_escort | a | all | 3096 | 102.1 | 79.9 | 0.35 | 0.170 | 0.62 | 0.0247 | 0.30 | 2.11 | 0.357 |
| convoy_escort | b | fighter | 1548 | 78.6 | 59.8 | 0.19 | 0.235 | 0.67 | 0.0146 | 0.19 | 1.73 | 0.344 |
| convoy_escort | b | gunship | 516 | 212.8 | 140.8 | 0.50 | 0.174 | 0.72 | 0.0026 | 0.43 | 1.89 | 0.569 |
| convoy_escort | b | strafer | 1032 | 88.4 | 79.5 | 0.53 | 0.143 | 0.51 | 0.0431 | 0.35 | 2.75 | 0.279 |
| convoy_escort | b | all | 3096 | 104.2 | 79.9 | 0.35 | 0.173 | 0.62 | 0.0230 | 0.29 | 2.10 | 0.361 |
