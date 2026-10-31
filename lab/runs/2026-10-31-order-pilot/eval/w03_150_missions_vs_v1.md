**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.684

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.707 | 0.713 | 0.702 | 0.000 | 0.012 | 0.000 | 109 | 135 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.661 | 0.492 | 0.829 | 0.000 | 0.000 | 0.000 | 60 | 72 | eliminated 0.01, convoy_through 0.33, convoy_destroyed 0.67 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 66.3 | 49.1 | 0.04 | 0.309 | 0.81 | 0.0079 | 0.17 | 1.83 | 0.419 |
| carrier_battle | a | gunship | 860 | 459.9 | 167.0 | 0.44 | 0.307 | 0.84 | 0.0013 | 0.48 | 2.70 | 0.551 |
| carrier_battle | a | strafer | 1032 | 126.4 | 96.3 | 0.05 | 0.228 | 0.71 | 0.0116 | 0.23 | 2.41 | 0.516 |
| carrier_battle | a | all | 3956 | 167.5 | 87.1 | 0.13 | 0.278 | 0.80 | 0.0065 | 0.29 | 2.17 | 0.488 |
| carrier_battle | b | fighter | 2064 | 49.1 | 41.4 | 0.02 | 0.272 | 0.80 | 0.0104 | 0.17 | 1.81 | 0.369 |
| carrier_battle | b | gunship | 860 | 288.0 | 143.5 | 0.24 | 0.243 | 0.85 | 0.0015 | 0.49 | 2.68 | 0.510 |
| carrier_battle | b | strafer | 1032 | 83.2 | 95.3 | 0.05 | 0.201 | 0.69 | 0.0200 | 0.26 | 2.49 | 0.458 |
| carrier_battle | b | all | 3956 | 110.0 | 77.7 | 0.08 | 0.232 | 0.79 | 0.0097 | 0.30 | 2.18 | 0.439 |
| convoy_escort | a | fighter | 1462 | 182.3 | 64.7 | 0.41 | 0.382 | 0.89 | 0.0053 | 0.17 | 1.68 | 0.468 |
| convoy_escort | a | gunship | 430 | 408.2 | 160.0 | 0.73 | 0.254 | 0.90 | 0.0015 | 0.41 | 1.91 | 0.641 |
| convoy_escort | a | strafer | 688 | 104.3 | 33.0 | 0.62 | 0.131 | 0.59 | 0.0184 | 0.27 | 2.59 | 0.324 |
| convoy_escort | a | all | 2580 | 199.2 | 72.1 | 0.52 | 0.246 | 0.81 | 0.0080 | 0.24 | 1.96 | 0.465 |
| convoy_escort | b | fighter | 1462 | 143.4 | 67.9 | 0.35 | 0.348 | 0.84 | 0.0132 | 0.18 | 1.84 | 0.394 |
| convoy_escort | b | gunship | 430 | 406.2 | 160.9 | 0.61 | 0.269 | 0.91 | 0.0011 | 0.44 | 1.69 | 0.612 |
| convoy_escort | b | strafer | 688 | 79.9 | 41.5 | 0.61 | 0.124 | 0.49 | 0.0385 | 0.32 | 2.40 | 0.269 |
| convoy_escort | b | all | 2580 | 170.3 | 76.4 | 0.46 | 0.240 | 0.76 | 0.0180 | 0.27 | 1.96 | 0.401 |
