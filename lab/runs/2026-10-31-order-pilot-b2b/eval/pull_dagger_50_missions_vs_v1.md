**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.171

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.004 | 0.000 | 0.000 | 0.000 | 0.000 | 85 | 102 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.339 | 0.147 | 0.531 | 0.000 | 0.000 | 0.000 | 54 | 71 | eliminated 0.17, convoy_through 0.14, convoy_destroyed 0.69 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.0 | 11.1 | 0.00 | 0.110 | 0.90 | 0.0006 | 0.27 | 1.46 | 0.177 |
| carrier_battle | a | gunship | 860 | 50.0 | 73.3 | 0.16 | 0.145 | 0.96 | 0.0007 | 0.46 | 1.95 | 0.393 |
| carrier_battle | a | strafer | 1032 | 7.3 | 14.0 | 0.00 | 0.072 | 0.84 | 0.0004 | 0.31 | 1.50 | 0.263 |
| carrier_battle | a | all | 3956 | 16.9 | 25.4 | 0.04 | 0.117 | 0.91 | 0.0006 | 0.35 | 1.58 | 0.274 |
| carrier_battle | b | fighter | 2064 | 120.4 | 60.5 | 0.30 | 0.341 | 0.77 | 0.0054 | 0.19 | 2.26 | 0.376 |
| carrier_battle | b | gunship | 860 | 479.9 | 123.9 | 0.90 | 0.331 | 0.84 | 0.0006 | 0.50 | 2.07 | 0.568 |
| carrier_battle | b | strafer | 1032 | 161.9 | 121.1 | 0.46 | 0.236 | 0.65 | 0.0224 | 0.28 | 2.98 | 0.408 |
| carrier_battle | b | all | 3956 | 209.4 | 90.1 | 0.47 | 0.294 | 0.75 | 0.0088 | 0.29 | 2.41 | 0.431 |
| convoy_escort | a | fighter | 1462 | 62.0 | 42.6 | 0.06 | 0.342 | 0.92 | 0.0000 | 0.34 | 1.07 | 0.306 |
| convoy_escort | a | gunship | 430 | 401.8 | 107.1 | 0.46 | 0.296 | 0.95 | 0.0000 | 0.47 | 1.05 | 0.591 |
| convoy_escort | a | strafer | 688 | 132.0 | 39.7 | 0.26 | 0.187 | 0.92 | 0.0000 | 0.27 | 1.32 | 0.441 |
| convoy_escort | a | all | 2580 | 137.3 | 52.6 | 0.18 | 0.257 | 0.93 | 0.0000 | 0.36 | 1.14 | 0.423 |
| convoy_escort | b | fighter | 1462 | 215.6 | 68.3 | 0.65 | 0.398 | 0.89 | 0.0049 | 0.20 | 1.78 | 0.418 |
| convoy_escort | b | gunship | 430 | 399.2 | 218.0 | 1.00 | 0.253 | 0.89 | 0.0002 | 0.48 | 2.15 | 0.591 |
| convoy_escort | b | strafer | 688 | 90.0 | 45.8 | 0.88 | 0.123 | 0.52 | 0.0272 | 0.31 | 2.65 | 0.275 |
| convoy_escort | b | all | 2580 | 212.7 | 87.3 | 0.77 | 0.250 | 0.79 | 0.0101 | 0.29 | 2.08 | 0.412 |
