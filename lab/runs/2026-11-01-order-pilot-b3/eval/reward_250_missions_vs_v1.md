**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.718

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.753 | 0.760 | 0.746 | 0.002 | 0.004 | 0.000 | 107 | 131 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.682 | 0.388 | 0.977 | 0.000 | 0.000 | 0.000 | 46 | 72 | eliminated 0.01, convoy_through 0.19, convoy_destroyed 0.79 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 63.1 | 41.9 | 0.04 | 0.265 | 0.82 | 0.0019 | 0.21 | 1.76 | 0.632 |
| carrier_battle | a | gunship | 860 | 526.0 | 183.9 | 0.54 | 0.290 | 0.83 | 0.0015 | 0.46 | 2.68 | 0.732 |
| carrier_battle | a | strafer | 1032 | 108.5 | 69.5 | 0.03 | 0.187 | 0.75 | 0.0021 | 0.18 | 2.04 | 0.693 |
| carrier_battle | a | all | 3956 | 175.6 | 79.9 | 0.15 | 0.250 | 0.81 | 0.0018 | 0.30 | 2.03 | 0.682 |
| carrier_battle | b | fighter | 2064 | 49.4 | 31.6 | 0.03 | 0.264 | 0.80 | 0.0065 | 0.16 | 1.73 | 0.374 |
| carrier_battle | b | gunship | 860 | 282.9 | 151.1 | 0.28 | 0.274 | 0.86 | 0.0008 | 0.50 | 2.39 | 0.522 |
| carrier_battle | b | strafer | 1032 | 87.9 | 86.5 | 0.05 | 0.210 | 0.71 | 0.0136 | 0.25 | 2.17 | 0.506 |
| carrier_battle | b | all | 3956 | 110.2 | 71.9 | 0.09 | 0.247 | 0.80 | 0.0063 | 0.29 | 1.99 | 0.455 |
| convoy_escort | a | fighter | 1462 | 147.8 | 54.3 | 0.42 | 0.404 | 0.93 | 0.0006 | 0.22 | 1.19 | 0.735 |
| convoy_escort | a | gunship | 430 | 401.5 | 108.4 | 0.80 | 0.239 | 0.91 | 0.0004 | 0.39 | 1.61 | 0.814 |
| convoy_escort | a | strafer | 688 | 191.9 | 47.1 | 0.48 | 0.194 | 0.88 | 0.0007 | 0.16 | 1.48 | 0.757 |
| convoy_escort | a | all | 2580 | 201.8 | 61.4 | 0.50 | 0.257 | 0.91 | 0.0006 | 0.25 | 1.34 | 0.759 |
| convoy_escort | b | fighter | 1462 | 125.6 | 56.6 | 0.29 | 0.362 | 0.87 | 0.0098 | 0.18 | 1.58 | 0.410 |
| convoy_escort | b | gunship | 430 | 507.9 | 205.9 | 0.84 | 0.329 | 0.92 | 0.0006 | 0.45 | 1.60 | 0.636 |
| convoy_escort | b | strafer | 688 | 76.4 | 39.9 | 0.66 | 0.119 | 0.53 | 0.0419 | 0.32 | 2.40 | 0.283 |
| convoy_escort | b | all | 2580 | 176.2 | 77.0 | 0.48 | 0.258 | 0.78 | 0.0175 | 0.28 | 1.80 | 0.420 |
