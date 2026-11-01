**policy:ppo_bc_400.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.492

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.589 | 0.597 | 0.581 | 0.000 | 0.004 | 0.000 | 88 | 114 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.395 | 0.426 | 0.364 | 0.000 | 0.000 | 0.000 | 52 | 74 | eliminated 0.43, convoy_through 0.10, convoy_destroyed 0.47 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 51.8 | 39.9 | 0.06 | 0.343 | 0.85 | 0.0006 | 0.17 | 1.46 | 0.647 |
| carrier_battle | a | gunship | 430 | 495.7 | 172.5 | 0.61 | 0.370 | 0.78 | 0.0027 | 0.42 | 2.14 | 0.685 |
| carrier_battle | a | strafer | 516 | 110.7 | 79.7 | 0.03 | 0.244 | 0.74 | 0.0035 | 0.27 | 1.84 | 0.620 |
| carrier_battle | a | all | 1978 | 163.7 | 79.1 | 0.17 | 0.320 | 0.80 | 0.0021 | 0.29 | 1.71 | 0.655 |
| carrier_battle | b | fighter | 1032 | 45.6 | 33.6 | 0.05 | 0.219 | 0.82 | 0.0009 | 0.25 | 1.85 | 0.647 |
| carrier_battle | b | gunship | 430 | 366.2 | 129.9 | 0.60 | 0.213 | 0.81 | 0.0013 | 0.46 | 2.94 | 0.734 |
| carrier_battle | b | strafer | 516 | 88.1 | 75.4 | 0.04 | 0.160 | 0.72 | 0.0015 | 0.19 | 2.42 | 0.662 |
| carrier_battle | b | all | 1978 | 126.4 | 65.4 | 0.16 | 0.195 | 0.79 | 0.0012 | 0.31 | 2.24 | 0.683 |
| convoy_escort | a | fighter | 774 | 107.1 | 69.0 | 0.06 | 0.403 | 0.85 | 0.0003 | 0.17 | 1.05 | 0.838 |
| convoy_escort | a | gunship | 258 | 419.8 | 178.0 | 0.63 | 0.253 | 0.83 | 0.0001 | 0.46 | 1.50 | 0.845 |
| convoy_escort | a | strafer | 516 | 216.1 | 67.4 | 0.20 | 0.196 | 0.87 | 0.0001 | 0.20 | 1.58 | 0.832 |
| convoy_escort | a | all | 1548 | 195.5 | 86.6 | 0.20 | 0.245 | 0.85 | 0.0002 | 0.25 | 1.30 | 0.838 |
| convoy_escort | b | fighter | 774 | 121.3 | 64.8 | 0.14 | 0.371 | 0.86 | 0.0003 | 0.25 | 1.16 | 0.746 |
| convoy_escort | b | gunship | 258 | 373.0 | 111.5 | 0.54 | 0.237 | 0.85 | 0.0001 | 0.40 | 1.40 | 0.827 |
| convoy_escort | b | strafer | 516 | 272.7 | 106.5 | 0.32 | 0.229 | 0.86 | 0.0001 | 0.15 | 1.69 | 0.789 |
| convoy_escort | b | all | 1548 | 213.7 | 86.5 | 0.27 | 0.254 | 0.86 | 0.0002 | 0.25 | 1.37 | 0.779 |
