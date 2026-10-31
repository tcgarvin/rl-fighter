**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.668

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.703 | 0.713 | 0.694 | 0.000 | 0.006 | 0.000 | 110 | 132 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.632 | 0.419 | 0.845 | 0.000 | 0.000 | 0.000 | 61 | 72 | eliminated 0.01, convoy_through 0.28, convoy_destroyed 0.71 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 69.1 | 45.7 | 0.03 | 0.308 | 0.80 | 0.0051 | 0.15 | 1.87 | 0.433 |
| carrier_battle | a | gunship | 860 | 447.0 | 161.6 | 0.48 | 0.277 | 0.84 | 0.0015 | 0.46 | 2.88 | 0.582 |
| carrier_battle | a | strafer | 1032 | 113.2 | 100.3 | 0.06 | 0.215 | 0.72 | 0.0105 | 0.24 | 2.44 | 0.531 |
| carrier_battle | a | all | 3956 | 162.7 | 85.1 | 0.14 | 0.259 | 0.80 | 0.0051 | 0.28 | 2.24 | 0.509 |
| carrier_battle | b | fighter | 2064 | 48.9 | 41.1 | 0.01 | 0.283 | 0.80 | 0.0083 | 0.16 | 1.76 | 0.370 |
| carrier_battle | b | gunship | 860 | 311.3 | 152.2 | 0.28 | 0.259 | 0.85 | 0.0010 | 0.49 | 2.65 | 0.513 |
| carrier_battle | b | strafer | 1032 | 79.1 | 91.0 | 0.04 | 0.205 | 0.68 | 0.0225 | 0.27 | 2.32 | 0.455 |
| carrier_battle | b | all | 3956 | 113.8 | 78.3 | 0.08 | 0.243 | 0.79 | 0.0091 | 0.30 | 2.10 | 0.441 |
| convoy_escort | a | fighter | 1462 | 177.5 | 57.0 | 0.39 | 0.374 | 0.89 | 0.0040 | 0.16 | 1.77 | 0.463 |
| convoy_escort | a | gunship | 430 | 364.6 | 160.8 | 0.73 | 0.234 | 0.89 | 0.0015 | 0.42 | 1.95 | 0.636 |
| convoy_escort | a | strafer | 688 | 126.7 | 47.1 | 0.57 | 0.148 | 0.65 | 0.0121 | 0.27 | 2.58 | 0.392 |
| convoy_escort | a | all | 2580 | 195.1 | 71.6 | 0.49 | 0.238 | 0.83 | 0.0055 | 0.25 | 2.01 | 0.481 |
| convoy_escort | b | fighter | 1462 | 145.0 | 61.4 | 0.31 | 0.348 | 0.86 | 0.0114 | 0.18 | 1.80 | 0.400 |
| convoy_escort | b | gunship | 430 | 455.5 | 204.7 | 0.72 | 0.281 | 0.90 | 0.0011 | 0.44 | 1.93 | 0.605 |
| convoy_escort | b | strafer | 688 | 78.7 | 37.8 | 0.61 | 0.117 | 0.51 | 0.0408 | 0.32 | 2.51 | 0.274 |
| convoy_escort | b | all | 2580 | 179.1 | 79.0 | 0.46 | 0.241 | 0.77 | 0.0175 | 0.27 | 2.01 | 0.408 |
