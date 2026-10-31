**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.230

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.017 | 0.027 | 0.008 | 0.000 | 0.000 | 0.000 | 95 | 115 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.442 | 0.217 | 0.667 | 0.000 | 0.000 | 0.000 | 53 | 71 | eliminated 0.14, convoy_through 0.13, convoy_destroyed 0.72 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.9 | 14.9 | 0.00 | 0.073 | 0.83 | 0.0007 | 0.15 | 1.92 | 0.300 |
| carrier_battle | a | gunship | 860 | 86.4 | 107.5 | 0.14 | 0.120 | 0.94 | 0.0002 | 0.44 | 2.13 | 0.659 |
| carrier_battle | a | strafer | 1032 | 11.6 | 19.5 | 0.00 | 0.050 | 0.79 | 0.0009 | 0.35 | 1.68 | 0.467 |
| carrier_battle | a | all | 3956 | 25.9 | 36.2 | 0.03 | 0.088 | 0.86 | 0.0006 | 0.28 | 1.90 | 0.447 |
| carrier_battle | b | fighter | 2064 | 112.0 | 62.0 | 0.23 | 0.341 | 0.74 | 0.0071 | 0.19 | 2.22 | 0.354 |
| carrier_battle | b | gunship | 860 | 545.9 | 141.5 | 0.86 | 0.338 | 0.84 | 0.0016 | 0.50 | 2.08 | 0.568 |
| carrier_battle | b | strafer | 1032 | 149.0 | 97.4 | 0.42 | 0.210 | 0.60 | 0.0422 | 0.29 | 2.89 | 0.370 |
| carrier_battle | b | all | 3956 | 216.0 | 88.5 | 0.42 | 0.288 | 0.73 | 0.0153 | 0.30 | 2.36 | 0.414 |
| convoy_escort | a | fighter | 1462 | 108.6 | 47.0 | 0.20 | 0.327 | 0.93 | 0.0000 | 0.23 | 1.15 | 0.578 |
| convoy_escort | a | gunship | 430 | 361.5 | 91.8 | 0.49 | 0.194 | 0.94 | 0.0000 | 0.44 | 1.15 | 0.792 |
| convoy_escort | a | strafer | 688 | 123.5 | 40.2 | 0.27 | 0.142 | 0.92 | 0.0001 | 0.32 | 1.38 | 0.597 |
| convoy_escort | a | all | 2580 | 154.7 | 52.7 | 0.27 | 0.202 | 0.93 | 0.0001 | 0.30 | 1.21 | 0.636 |
| convoy_escort | b | fighter | 1462 | 220.9 | 65.6 | 0.59 | 0.412 | 0.88 | 0.0071 | 0.20 | 1.66 | 0.422 |
| convoy_escort | b | gunship | 430 | 422.0 | 209.3 | 0.98 | 0.261 | 0.91 | 0.0004 | 0.47 | 2.24 | 0.598 |
| convoy_escort | b | strafer | 688 | 74.0 | 29.5 | 0.89 | 0.104 | 0.44 | 0.0429 | 0.33 | 2.36 | 0.242 |
| convoy_escort | b | all | 2580 | 215.3 | 79.9 | 0.74 | 0.254 | 0.76 | 0.0159 | 0.29 | 1.94 | 0.406 |
