**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.214

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 85 | 103 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.428 | 0.202 | 0.655 | 0.000 | 0.000 | 0.000 | 53 | 71 | eliminated 0.15, convoy_through 0.13, convoy_destroyed 0.73 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.6 | 17.4 | 0.00 | 0.123 | 0.87 | 0.0005 | 0.27 | 1.51 | 0.203 |
| carrier_battle | a | gunship | 860 | 54.2 | 89.8 | 0.13 | 0.162 | 0.95 | 0.0009 | 0.46 | 1.83 | 0.440 |
| carrier_battle | a | strafer | 1032 | 7.2 | 14.7 | 0.00 | 0.067 | 0.84 | 0.0005 | 0.32 | 1.44 | 0.295 |
| carrier_battle | a | all | 3956 | 17.1 | 32.4 | 0.03 | 0.125 | 0.89 | 0.0007 | 0.35 | 1.56 | 0.306 |
| carrier_battle | b | fighter | 2064 | 123.2 | 62.4 | 0.32 | 0.327 | 0.73 | 0.0080 | 0.20 | 2.45 | 0.352 |
| carrier_battle | b | gunship | 860 | 470.4 | 120.9 | 0.92 | 0.320 | 0.83 | 0.0006 | 0.50 | 2.04 | 0.567 |
| carrier_battle | b | strafer | 1032 | 159.3 | 105.6 | 0.50 | 0.227 | 0.62 | 0.0285 | 0.29 | 3.08 | 0.375 |
| carrier_battle | b | all | 3956 | 208.1 | 86.4 | 0.49 | 0.285 | 0.72 | 0.0117 | 0.29 | 2.53 | 0.408 |
| convoy_escort | a | fighter | 1462 | 65.8 | 41.9 | 0.10 | 0.316 | 0.92 | 0.0000 | 0.34 | 1.08 | 0.394 |
| convoy_escort | a | gunship | 430 | 440.9 | 109.5 | 0.50 | 0.300 | 0.94 | 0.0002 | 0.45 | 1.13 | 0.664 |
| convoy_escort | a | strafer | 688 | 132.7 | 36.4 | 0.30 | 0.159 | 0.92 | 0.0000 | 0.26 | 1.40 | 0.533 |
| convoy_escort | a | all | 2580 | 146.2 | 51.7 | 0.22 | 0.238 | 0.92 | 0.0001 | 0.35 | 1.17 | 0.505 |
| convoy_escort | b | fighter | 1462 | 200.6 | 66.1 | 0.60 | 0.386 | 0.88 | 0.0064 | 0.20 | 1.75 | 0.411 |
| convoy_escort | b | gunship | 430 | 410.4 | 229.6 | 1.00 | 0.265 | 0.90 | 0.0003 | 0.48 | 2.07 | 0.596 |
| convoy_escort | b | strafer | 688 | 85.6 | 45.8 | 0.89 | 0.118 | 0.52 | 0.0340 | 0.31 | 2.76 | 0.272 |
| convoy_escort | b | all | 2580 | 204.9 | 87.9 | 0.74 | 0.247 | 0.78 | 0.0129 | 0.28 | 2.07 | 0.408 |
