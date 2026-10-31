**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.743

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.772 | 0.783 | 0.762 | 0.002 | 0.019 | 0.000 | 108 | 135 | time_limit 0.02, carrier_destroyed 0.98 |
| convoy_escort | 516 | 0.713 | 0.461 | 0.965 | 0.000 | 0.000 | 0.000 | 53 | 72 | eliminated 0.01, convoy_through 0.24, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 69.5 | 44.8 | 0.05 | 0.297 | 0.80 | 0.0048 | 0.19 | 1.90 | 0.506 |
| carrier_battle | a | gunship | 860 | 489.0 | 170.1 | 0.49 | 0.306 | 0.83 | 0.0006 | 0.48 | 2.59 | 0.617 |
| carrier_battle | a | strafer | 1032 | 125.0 | 96.4 | 0.06 | 0.221 | 0.73 | 0.0068 | 0.20 | 2.32 | 0.582 |
| carrier_battle | a | all | 3956 | 175.2 | 85.5 | 0.15 | 0.273 | 0.80 | 0.0038 | 0.29 | 2.16 | 0.562 |
| carrier_battle | b | fighter | 2064 | 43.6 | 37.5 | 0.01 | 0.280 | 0.81 | 0.0066 | 0.16 | 1.66 | 0.372 |
| carrier_battle | b | gunship | 860 | 274.7 | 147.7 | 0.22 | 0.250 | 0.85 | 0.0009 | 0.49 | 2.52 | 0.517 |
| carrier_battle | b | strafer | 1032 | 79.0 | 83.8 | 0.03 | 0.201 | 0.69 | 0.0170 | 0.26 | 2.25 | 0.470 |
| carrier_battle | b | all | 3956 | 103.1 | 73.5 | 0.06 | 0.236 | 0.79 | 0.0071 | 0.30 | 2.00 | 0.448 |
| convoy_escort | a | fighter | 1462 | 181.3 | 54.7 | 0.43 | 0.391 | 0.91 | 0.0017 | 0.19 | 1.55 | 0.564 |
| convoy_escort | a | gunship | 430 | 387.8 | 148.1 | 0.79 | 0.247 | 0.90 | 0.0010 | 0.42 | 1.75 | 0.690 |
| convoy_escort | a | strafer | 688 | 134.1 | 42.7 | 0.55 | 0.155 | 0.75 | 0.0035 | 0.22 | 2.48 | 0.451 |
| convoy_escort | a | all | 2580 | 203.1 | 67.1 | 0.52 | 0.249 | 0.87 | 0.0020 | 0.25 | 1.83 | 0.564 |
| convoy_escort | b | fighter | 1462 | 133.6 | 60.9 | 0.29 | 0.364 | 0.86 | 0.0103 | 0.18 | 1.65 | 0.397 |
| convoy_escort | b | gunship | 430 | 449.3 | 189.0 | 0.66 | 0.297 | 0.92 | 0.0013 | 0.44 | 1.57 | 0.624 |
| convoy_escort | b | strafer | 688 | 77.3 | 38.8 | 0.61 | 0.119 | 0.52 | 0.0407 | 0.32 | 2.40 | 0.281 |
| convoy_escort | b | all | 2580 | 171.2 | 76.3 | 0.44 | 0.248 | 0.77 | 0.0173 | 0.27 | 1.83 | 0.411 |
