**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.627

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.624 | 0.643 | 0.605 | 0.000 | 0.019 | 0.000 | 113 | 136 | time_limit 0.02, carrier_destroyed 0.98 |
| convoy_escort | 516 | 0.630 | 0.465 | 0.795 | 0.000 | 0.000 | 0.000 | 63 | 72 | eliminated 0.01, convoy_through 0.33, convoy_destroyed 0.66 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 66.3 | 45.6 | 0.04 | 0.305 | 0.80 | 0.0080 | 0.17 | 1.88 | 0.393 |
| carrier_battle | a | gunship | 860 | 418.6 | 164.7 | 0.42 | 0.281 | 0.84 | 0.0011 | 0.49 | 2.84 | 0.553 |
| carrier_battle | a | strafer | 1032 | 109.9 | 102.8 | 0.06 | 0.216 | 0.70 | 0.0149 | 0.26 | 2.52 | 0.502 |
| carrier_battle | a | all | 3956 | 154.3 | 86.4 | 0.13 | 0.261 | 0.79 | 0.0072 | 0.30 | 2.26 | 0.475 |
| carrier_battle | b | fighter | 2064 | 49.9 | 44.6 | 0.02 | 0.286 | 0.81 | 0.0108 | 0.16 | 1.76 | 0.369 |
| carrier_battle | b | gunship | 860 | 313.9 | 150.2 | 0.26 | 0.254 | 0.86 | 0.0014 | 0.49 | 2.74 | 0.515 |
| carrier_battle | b | strafer | 1032 | 95.7 | 91.0 | 0.05 | 0.205 | 0.67 | 0.0215 | 0.27 | 2.47 | 0.450 |
| carrier_battle | b | all | 3956 | 119.3 | 79.7 | 0.08 | 0.241 | 0.79 | 0.0103 | 0.30 | 2.16 | 0.440 |
| convoy_escort | a | fighter | 1462 | 174.6 | 62.7 | 0.39 | 0.375 | 0.87 | 0.0073 | 0.19 | 1.86 | 0.428 |
| convoy_escort | a | gunship | 430 | 391.0 | 165.0 | 0.71 | 0.245 | 0.90 | 0.0014 | 0.44 | 2.03 | 0.632 |
| convoy_escort | a | strafer | 688 | 116.9 | 44.4 | 0.62 | 0.140 | 0.59 | 0.0226 | 0.30 | 2.69 | 0.340 |
| convoy_escort | a | all | 2580 | 195.3 | 74.9 | 0.51 | 0.240 | 0.80 | 0.0102 | 0.27 | 2.11 | 0.446 |
| convoy_escort | b | fighter | 1462 | 145.1 | 64.1 | 0.31 | 0.353 | 0.85 | 0.0117 | 0.18 | 1.80 | 0.393 |
| convoy_escort | b | gunship | 430 | 405.4 | 182.2 | 0.64 | 0.266 | 0.90 | 0.0023 | 0.44 | 1.90 | 0.607 |
| convoy_escort | b | strafer | 688 | 83.7 | 39.5 | 0.60 | 0.126 | 0.51 | 0.0415 | 0.32 | 2.43 | 0.274 |
| convoy_escort | b | all | 2580 | 172.1 | 77.2 | 0.44 | 0.240 | 0.77 | 0.0180 | 0.27 | 1.98 | 0.404 |
