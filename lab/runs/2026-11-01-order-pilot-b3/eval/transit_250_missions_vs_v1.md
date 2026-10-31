**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.286

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.019 | 0.023 | 0.016 | 0.000 | 0.000 | 0.000 | 94 | 114 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.552 | 0.310 | 0.795 | 0.000 | 0.000 | 0.000 | 48 | 71 | eliminated 0.10, convoy_through 0.16, convoy_destroyed 0.74 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.5 | 20.2 | 0.01 | 0.078 | 0.82 | 0.0002 | 0.12 | 1.96 | 0.383 |
| carrier_battle | a | gunship | 860 | 109.7 | 130.3 | 0.14 | 0.143 | 0.94 | 0.0004 | 0.43 | 2.04 | 0.697 |
| carrier_battle | a | strafer | 1032 | 12.5 | 20.3 | 0.01 | 0.049 | 0.78 | 0.0005 | 0.33 | 1.66 | 0.509 |
| carrier_battle | a | all | 3956 | 31.5 | 44.1 | 0.04 | 0.099 | 0.85 | 0.0003 | 0.25 | 1.90 | 0.501 |
| carrier_battle | b | fighter | 2064 | 109.9 | 63.9 | 0.22 | 0.338 | 0.73 | 0.0078 | 0.19 | 2.27 | 0.352 |
| carrier_battle | b | gunship | 860 | 553.4 | 136.8 | 0.86 | 0.347 | 0.84 | 0.0014 | 0.50 | 2.04 | 0.569 |
| carrier_battle | b | strafer | 1032 | 143.9 | 93.4 | 0.42 | 0.208 | 0.59 | 0.0419 | 0.29 | 2.92 | 0.362 |
| carrier_battle | b | all | 3956 | 215.2 | 87.5 | 0.41 | 0.291 | 0.72 | 0.0155 | 0.30 | 2.39 | 0.410 |
| convoy_escort | a | fighter | 1462 | 115.6 | 47.8 | 0.30 | 0.315 | 0.92 | 0.0001 | 0.18 | 1.18 | 0.707 |
| convoy_escort | a | gunship | 430 | 343.1 | 83.7 | 0.55 | 0.191 | 0.93 | 0.0000 | 0.44 | 1.19 | 0.820 |
| convoy_escort | a | strafer | 688 | 130.2 | 38.9 | 0.34 | 0.143 | 0.90 | 0.0001 | 0.29 | 1.36 | 0.662 |
| convoy_escort | a | all | 2580 | 157.4 | 51.4 | 0.35 | 0.200 | 0.92 | 0.0001 | 0.27 | 1.23 | 0.722 |
| convoy_escort | b | fighter | 1462 | 203.3 | 64.0 | 0.56 | 0.401 | 0.87 | 0.0088 | 0.19 | 1.67 | 0.419 |
| convoy_escort | b | gunship | 430 | 419.1 | 217.7 | 0.98 | 0.278 | 0.91 | 0.0004 | 0.47 | 2.16 | 0.600 |
| convoy_escort | b | strafer | 688 | 74.3 | 30.2 | 0.89 | 0.105 | 0.45 | 0.0461 | 0.32 | 2.19 | 0.252 |
| convoy_escort | b | all | 2580 | 204.9 | 80.6 | 0.72 | 0.254 | 0.76 | 0.0178 | 0.28 | 1.89 | 0.406 |
