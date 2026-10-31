**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.224

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.006 | 0.008 | 0.004 | 0.000 | 0.000 | 0.000 | 85 | 102 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.442 | 0.143 | 0.740 | 0.000 | 0.000 | 0.000 | 49 | 70 | eliminated 0.12, convoy_through 0.08, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.6 | 19.6 | 0.00 | 0.119 | 0.88 | 0.0009 | 0.28 | 1.55 | 0.302 |
| carrier_battle | a | gunship | 860 | 76.5 | 105.8 | 0.13 | 0.171 | 0.95 | 0.0009 | 0.48 | 1.95 | 0.589 |
| carrier_battle | a | strafer | 1032 | 6.8 | 16.0 | 0.00 | 0.064 | 0.83 | 0.0005 | 0.33 | 1.49 | 0.378 |
| carrier_battle | a | all | 3956 | 22.4 | 37.4 | 0.03 | 0.129 | 0.89 | 0.0008 | 0.36 | 1.62 | 0.420 |
| carrier_battle | b | fighter | 2064 | 116.8 | 60.8 | 0.29 | 0.325 | 0.72 | 0.0093 | 0.19 | 2.45 | 0.347 |
| carrier_battle | b | gunship | 860 | 492.1 | 129.6 | 0.89 | 0.331 | 0.84 | 0.0008 | 0.50 | 2.09 | 0.571 |
| carrier_battle | b | strafer | 1032 | 147.8 | 105.0 | 0.43 | 0.223 | 0.62 | 0.0273 | 0.29 | 3.02 | 0.382 |
| carrier_battle | b | all | 3956 | 206.4 | 87.3 | 0.46 | 0.287 | 0.72 | 0.0120 | 0.29 | 2.52 | 0.409 |
| convoy_escort | a | fighter | 1462 | 65.7 | 41.0 | 0.12 | 0.321 | 0.92 | 0.0000 | 0.35 | 1.07 | 0.483 |
| convoy_escort | a | gunship | 430 | 495.0 | 117.4 | 0.56 | 0.322 | 0.94 | 0.0001 | 0.46 | 1.15 | 0.777 |
| convoy_escort | a | strafer | 688 | 120.2 | 32.1 | 0.31 | 0.154 | 0.92 | 0.0000 | 0.28 | 1.32 | 0.589 |
| convoy_escort | a | all | 2580 | 151.8 | 51.3 | 0.24 | 0.248 | 0.93 | 0.0000 | 0.36 | 1.15 | 0.591 |
| convoy_escort | b | fighter | 1462 | 197.2 | 64.8 | 0.55 | 0.396 | 0.90 | 0.0049 | 0.20 | 1.67 | 0.423 |
| convoy_escort | b | gunship | 430 | 415.0 | 227.0 | 0.99 | 0.276 | 0.90 | 0.0006 | 0.47 | 1.93 | 0.608 |
| convoy_escort | b | strafer | 688 | 88.3 | 37.4 | 0.89 | 0.116 | 0.52 | 0.0273 | 0.31 | 2.67 | 0.279 |
| convoy_escort | b | all | 2580 | 204.5 | 84.6 | 0.71 | 0.252 | 0.79 | 0.0105 | 0.28 | 1.98 | 0.418 |
