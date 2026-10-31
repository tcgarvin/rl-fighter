**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.302

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.039 | 0.047 | 0.031 | 0.000 | 0.000 | 0.000 | 87 | 108 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.566 | 0.260 | 0.872 | 0.000 | 0.000 | 0.000 | 49 | 71 | eliminated 0.06, convoy_through 0.13, convoy_destroyed 0.81 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 10.2 | 26.6 | 0.00 | 0.130 | 0.87 | 0.0009 | 0.27 | 1.63 | 0.378 |
| carrier_battle | a | gunship | 860 | 147.2 | 138.9 | 0.13 | 0.202 | 0.94 | 0.0005 | 0.44 | 1.92 | 0.682 |
| carrier_battle | a | strafer | 1032 | 10.9 | 23.0 | 0.00 | 0.074 | 0.82 | 0.0012 | 0.31 | 1.52 | 0.454 |
| carrier_battle | a | all | 3956 | 40.2 | 50.1 | 0.03 | 0.151 | 0.88 | 0.0008 | 0.34 | 1.66 | 0.499 |
| carrier_battle | b | fighter | 2064 | 111.7 | 58.3 | 0.24 | 0.314 | 0.72 | 0.0106 | 0.19 | 2.47 | 0.343 |
| carrier_battle | b | gunship | 860 | 501.6 | 127.4 | 0.86 | 0.313 | 0.84 | 0.0005 | 0.50 | 2.24 | 0.571 |
| carrier_battle | b | strafer | 1032 | 144.1 | 96.8 | 0.41 | 0.215 | 0.60 | 0.0300 | 0.29 | 3.01 | 0.367 |
| carrier_battle | b | all | 3956 | 204.9 | 83.4 | 0.42 | 0.276 | 0.72 | 0.0132 | 0.29 | 2.56 | 0.406 |
| convoy_escort | a | fighter | 1462 | 85.5 | 42.6 | 0.20 | 0.312 | 0.92 | 0.0000 | 0.34 | 1.10 | 0.599 |
| convoy_escort | a | gunship | 430 | 541.8 | 110.9 | 0.62 | 0.300 | 0.94 | 0.0000 | 0.46 | 1.16 | 0.846 |
| convoy_escort | a | strafer | 688 | 121.8 | 38.2 | 0.36 | 0.142 | 0.91 | 0.0000 | 0.25 | 1.38 | 0.654 |
| convoy_escort | a | all | 2580 | 171.2 | 52.8 | 0.32 | 0.235 | 0.92 | 0.0000 | 0.34 | 1.18 | 0.676 |
| convoy_escort | b | fighter | 1462 | 177.9 | 61.9 | 0.48 | 0.387 | 0.88 | 0.0067 | 0.19 | 1.64 | 0.413 |
| convoy_escort | b | gunship | 430 | 448.9 | 232.3 | 0.99 | 0.293 | 0.91 | 0.0004 | 0.47 | 1.84 | 0.610 |
| convoy_escort | b | strafer | 688 | 78.8 | 35.2 | 0.86 | 0.110 | 0.49 | 0.0418 | 0.32 | 2.41 | 0.266 |
| convoy_escort | b | all | 2580 | 196.6 | 83.2 | 0.67 | 0.253 | 0.77 | 0.0157 | 0.28 | 1.88 | 0.410 |
