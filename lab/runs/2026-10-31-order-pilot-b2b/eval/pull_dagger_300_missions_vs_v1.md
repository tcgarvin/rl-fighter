**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.271

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.016 | 0.012 | 0.019 | 0.000 | 0.000 | 0.000 | 86 | 107 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.527 | 0.248 | 0.806 | 0.000 | 0.000 | 0.000 | 49 | 71 | eliminated 0.09, convoy_through 0.13, convoy_destroyed 0.78 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.6 | 24.5 | 0.00 | 0.126 | 0.87 | 0.0004 | 0.27 | 1.61 | 0.311 |
| carrier_battle | a | gunship | 860 | 114.9 | 119.4 | 0.13 | 0.194 | 0.94 | 0.0005 | 0.43 | 1.93 | 0.575 |
| carrier_battle | a | strafer | 1032 | 11.5 | 21.3 | 0.01 | 0.073 | 0.83 | 0.0016 | 0.30 | 1.51 | 0.430 |
| carrier_battle | a | all | 3956 | 32.5 | 44.3 | 0.03 | 0.142 | 0.89 | 0.0007 | 0.33 | 1.65 | 0.427 |
| carrier_battle | b | fighter | 2064 | 114.5 | 60.6 | 0.25 | 0.315 | 0.72 | 0.0094 | 0.19 | 2.48 | 0.351 |
| carrier_battle | b | gunship | 860 | 503.6 | 119.7 | 0.88 | 0.315 | 0.84 | 0.0006 | 0.50 | 2.17 | 0.571 |
| carrier_battle | b | strafer | 1032 | 146.4 | 99.2 | 0.41 | 0.218 | 0.61 | 0.0309 | 0.29 | 3.05 | 0.376 |
| carrier_battle | b | all | 3956 | 207.4 | 83.5 | 0.43 | 0.278 | 0.72 | 0.0128 | 0.29 | 2.56 | 0.412 |
| convoy_escort | a | fighter | 1462 | 92.0 | 42.8 | 0.21 | 0.318 | 0.93 | 0.0000 | 0.33 | 1.10 | 0.569 |
| convoy_escort | a | gunship | 430 | 463.4 | 108.1 | 0.61 | 0.281 | 0.93 | 0.0001 | 0.42 | 1.19 | 0.780 |
| convoy_escort | a | strafer | 688 | 126.5 | 39.1 | 0.36 | 0.139 | 0.90 | 0.0000 | 0.24 | 1.44 | 0.645 |
| convoy_escort | a | all | 2580 | 163.1 | 52.7 | 0.32 | 0.225 | 0.92 | 0.0000 | 0.33 | 1.21 | 0.642 |
| convoy_escort | b | fighter | 1462 | 187.7 | 61.2 | 0.52 | 0.389 | 0.88 | 0.0066 | 0.19 | 1.63 | 0.416 |
| convoy_escort | b | gunship | 430 | 440.5 | 230.1 | 0.99 | 0.288 | 0.91 | 0.0002 | 0.47 | 1.82 | 0.613 |
| convoy_escort | b | strafer | 688 | 82.8 | 37.5 | 0.86 | 0.112 | 0.51 | 0.0366 | 0.31 | 2.54 | 0.277 |
| convoy_escort | b | all | 2580 | 201.9 | 83.0 | 0.69 | 0.252 | 0.78 | 0.0140 | 0.28 | 1.91 | 0.415 |
