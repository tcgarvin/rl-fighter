**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.486

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.477 | 0.473 | 0.481 | 0.000 | 0.000 | 0.000 | 98 | 122 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.496 | 0.023 | 0.969 | 0.000 | 0.000 | 0.000 | 37 | 51 | eliminated 0.01, convoy_through 0.02, convoy_destroyed 0.97 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 49.7 | 28.5 | 0.03 | 0.246 | 0.81 | 0.0009 | 0.18 | 1.56 | 0.602 |
| carrier_battle | a | gunship | 430 | 443.6 | 183.5 | 0.49 | 0.282 | 0.83 | 0.0017 | 0.49 | 2.63 | 0.717 |
| carrier_battle | a | strafer | 516 | 81.8 | 49.4 | 0.02 | 0.153 | 0.74 | 0.0008 | 0.19 | 1.95 | 0.685 |
| carrier_battle | a | all | 1978 | 143.7 | 67.6 | 0.13 | 0.231 | 0.80 | 0.0012 | 0.30 | 1.89 | 0.664 |
| carrier_battle | b | fighter | 1032 | 63.4 | 33.7 | 0.06 | 0.270 | 0.80 | 0.0014 | 0.17 | 1.77 | 0.572 |
| carrier_battle | b | gunship | 430 | 439.6 | 180.0 | 0.49 | 0.306 | 0.83 | 0.0002 | 0.48 | 2.30 | 0.699 |
| carrier_battle | b | strafer | 516 | 107.7 | 71.1 | 0.04 | 0.200 | 0.74 | 0.0034 | 0.20 | 2.00 | 0.668 |
| carrier_battle | b | all | 1978 | 156.7 | 75.2 | 0.15 | 0.261 | 0.80 | 0.0014 | 0.29 | 1.95 | 0.637 |
| convoy_escort | a | fighter | 731 | 138.8 | 43.0 | 0.34 | 0.429 | 0.93 | 0.0000 | 0.21 | 1.12 | 0.683 |
| convoy_escort | a | gunship | 215 | 401.8 | 136.2 | 0.76 | 0.281 | 0.93 | 0.0001 | 0.41 | 1.35 | 0.801 |
| convoy_escort | a | strafer | 344 | 174.6 | 45.4 | 0.47 | 0.192 | 0.88 | 0.0000 | 0.16 | 1.68 | 0.713 |
| convoy_escort | a | all | 1290 | 192.2 | 59.2 | 0.44 | 0.273 | 0.92 | 0.0000 | 0.25 | 1.31 | 0.719 |
| convoy_escort | b | fighter | 731 | 157.5 | 40.2 | 0.39 | 0.410 | 0.92 | 0.0001 | 0.19 | 1.27 | 0.650 |
| convoy_escort | b | gunship | 215 | 411.3 | 166.5 | 0.89 | 0.292 | 0.92 | 0.0001 | 0.45 | 1.42 | 0.767 |
| convoy_escort | b | strafer | 344 | 149.8 | 45.0 | 0.53 | 0.167 | 0.84 | 0.0004 | 0.20 | 2.10 | 0.624 |
| convoy_escort | b | all | 1290 | 197.7 | 62.5 | 0.51 | 0.265 | 0.90 | 0.0002 | 0.26 | 1.52 | 0.670 |
