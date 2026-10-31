**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.672

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.676 | 0.651 | 0.702 | 0.000 | 0.006 | 0.000 | 110 | 133 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.667 | 0.492 | 0.841 | 0.000 | 0.000 | 0.000 | 60 | 72 | eliminated 0.01, convoy_through 0.32, convoy_destroyed 0.67 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 72.1 | 46.3 | 0.05 | 0.302 | 0.80 | 0.0059 | 0.15 | 1.92 | 0.465 |
| carrier_battle | a | gunship | 860 | 424.2 | 165.1 | 0.46 | 0.258 | 0.84 | 0.0020 | 0.47 | 2.83 | 0.596 |
| carrier_battle | a | strafer | 1032 | 114.0 | 107.0 | 0.04 | 0.222 | 0.71 | 0.0126 | 0.25 | 2.41 | 0.545 |
| carrier_battle | a | all | 3956 | 159.6 | 87.9 | 0.14 | 0.252 | 0.80 | 0.0060 | 0.29 | 2.25 | 0.530 |
| carrier_battle | b | fighter | 2064 | 52.0 | 42.4 | 0.02 | 0.298 | 0.80 | 0.0096 | 0.16 | 1.74 | 0.376 |
| carrier_battle | b | gunship | 860 | 323.3 | 152.0 | 0.27 | 0.262 | 0.86 | 0.0018 | 0.49 | 2.70 | 0.509 |
| carrier_battle | b | strafer | 1032 | 87.8 | 95.4 | 0.05 | 0.207 | 0.69 | 0.0234 | 0.27 | 2.45 | 0.458 |
| carrier_battle | b | all | 3956 | 120.3 | 80.0 | 0.08 | 0.247 | 0.79 | 0.0103 | 0.30 | 2.13 | 0.444 |
| convoy_escort | a | fighter | 1462 | 176.5 | 55.6 | 0.39 | 0.366 | 0.90 | 0.0034 | 0.17 | 1.69 | 0.501 |
| convoy_escort | a | gunship | 430 | 363.5 | 157.7 | 0.72 | 0.226 | 0.90 | 0.0018 | 0.44 | 2.06 | 0.661 |
| convoy_escort | a | strafer | 688 | 136.3 | 50.8 | 0.58 | 0.149 | 0.69 | 0.0087 | 0.27 | 2.77 | 0.419 |
| convoy_escort | a | all | 2580 | 196.9 | 71.3 | 0.50 | 0.232 | 0.84 | 0.0045 | 0.26 | 2.04 | 0.514 |
| convoy_escort | b | fighter | 1462 | 140.9 | 62.6 | 0.31 | 0.345 | 0.85 | 0.0104 | 0.18 | 1.78 | 0.395 |
| convoy_escort | b | gunship | 430 | 435.2 | 203.5 | 0.70 | 0.275 | 0.90 | 0.0018 | 0.44 | 1.94 | 0.605 |
| convoy_escort | b | strafer | 688 | 84.2 | 40.5 | 0.60 | 0.124 | 0.52 | 0.0427 | 0.32 | 2.54 | 0.283 |
| convoy_escort | b | all | 2580 | 174.8 | 80.2 | 0.45 | 0.239 | 0.77 | 0.0176 | 0.27 | 2.01 | 0.408 |
