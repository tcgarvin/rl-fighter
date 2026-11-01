**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.668

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.661 | 0.682 | 0.640 | 0.000 | 0.010 | 0.000 | 108 | 133 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.674 | 0.996 | 0.353 | 0.000 | 0.000 | 0.000 | 71 | 75 | eliminated 0.35, convoy_through 0.47, convoy_destroyed 0.18 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 64.2 | 57.5 | 0.05 | 0.318 | 0.82 | 0.0094 | 0.14 | 1.85 | 0.614 |
| carrier_battle | a | gunship | 860 | 428.8 | 153.7 | 0.42 | 0.285 | 0.84 | 0.0007 | 0.41 | 2.45 | 0.683 |
| carrier_battle | a | strafer | 1032 | 131.5 | 84.5 | 0.04 | 0.205 | 0.70 | 0.0147 | 0.24 | 2.20 | 0.615 |
| carrier_battle | a | all | 3956 | 161.0 | 85.4 | 0.13 | 0.259 | 0.80 | 0.0079 | 0.25 | 2.07 | 0.637 |
| carrier_battle | b | fighter | 2064 | 53.4 | 37.6 | 0.03 | 0.261 | 0.82 | 0.0104 | 0.17 | 1.86 | 0.369 |
| carrier_battle | b | gunship | 860 | 317.1 | 149.5 | 0.31 | 0.244 | 0.87 | 0.0033 | 0.49 | 2.71 | 0.529 |
| carrier_battle | b | strafer | 1032 | 70.6 | 120.9 | 0.04 | 0.229 | 0.69 | 0.0186 | 0.26 | 2.47 | 0.440 |
| carrier_battle | b | all | 3956 | 115.2 | 83.6 | 0.09 | 0.242 | 0.81 | 0.0098 | 0.30 | 2.21 | 0.441 |
| convoy_escort | a | fighter | 1548 | 116.5 | 64.3 | 0.14 | 0.262 | 0.73 | 0.0051 | 0.19 | 1.59 | 0.666 |
| convoy_escort | a | gunship | 516 | 345.0 | 134.3 | 0.59 | 0.194 | 0.71 | 0.0004 | 0.42 | 1.61 | 0.724 |
| convoy_escort | a | strafer | 1032 | 214.1 | 99.9 | 0.28 | 0.226 | 0.69 | 0.0078 | 0.24 | 2.16 | 0.545 |
| convoy_escort | a | all | 3096 | 187.1 | 87.8 | 0.26 | 0.224 | 0.71 | 0.0050 | 0.25 | 1.78 | 0.641 |
| convoy_escort | b | fighter | 1548 | 75.9 | 55.4 | 0.14 | 0.278 | 0.79 | 0.0077 | 0.16 | 1.45 | 0.389 |
| convoy_escort | b | gunship | 516 | 218.9 | 149.6 | 0.45 | 0.206 | 0.81 | 0.0021 | 0.43 | 1.61 | 0.580 |
| convoy_escort | b | strafer | 1032 | 80.8 | 76.9 | 0.68 | 0.126 | 0.56 | 0.0408 | 0.36 | 3.28 | 0.275 |
| convoy_escort | b | all | 3096 | 101.4 | 78.3 | 0.37 | 0.177 | 0.69 | 0.0215 | 0.30 | 2.09 | 0.372 |
