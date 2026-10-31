**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.731

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.779 | 0.775 | 0.783 | 0.000 | 0.010 | 0.000 | 106 | 130 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.682 | 0.380 | 0.984 | 0.000 | 0.000 | 0.000 | 53 | 71 | eliminated 0.01, convoy_through 0.19, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 68.6 | 42.8 | 0.05 | 0.274 | 0.80 | 0.0030 | 0.17 | 1.90 | 0.537 |
| carrier_battle | a | gunship | 860 | 508.2 | 174.7 | 0.53 | 0.282 | 0.83 | 0.0010 | 0.48 | 2.86 | 0.673 |
| carrier_battle | a | strafer | 1032 | 118.1 | 94.3 | 0.04 | 0.203 | 0.72 | 0.0049 | 0.22 | 2.31 | 0.618 |
| carrier_battle | a | all | 3956 | 177.1 | 84.9 | 0.15 | 0.252 | 0.80 | 0.0027 | 0.29 | 2.21 | 0.604 |
| carrier_battle | b | fighter | 2064 | 45.6 | 36.3 | 0.02 | 0.285 | 0.80 | 0.0066 | 0.15 | 1.65 | 0.372 |
| carrier_battle | b | gunship | 860 | 273.9 | 145.7 | 0.23 | 0.254 | 0.86 | 0.0008 | 0.49 | 2.56 | 0.513 |
| carrier_battle | b | strafer | 1032 | 82.5 | 92.0 | 0.04 | 0.207 | 0.68 | 0.0170 | 0.27 | 2.26 | 0.462 |
| carrier_battle | b | all | 3956 | 104.9 | 74.6 | 0.07 | 0.241 | 0.79 | 0.0072 | 0.30 | 2.01 | 0.445 |
| convoy_escort | a | fighter | 1462 | 175.5 | 51.1 | 0.45 | 0.372 | 0.92 | 0.0020 | 0.20 | 1.51 | 0.595 |
| convoy_escort | a | gunship | 430 | 364.5 | 144.5 | 0.75 | 0.232 | 0.89 | 0.0010 | 0.44 | 1.85 | 0.718 |
| convoy_escort | a | strafer | 688 | 154.2 | 44.7 | 0.57 | 0.153 | 0.78 | 0.0031 | 0.22 | 2.49 | 0.539 |
| convoy_escort | a | all | 2580 | 201.3 | 64.9 | 0.53 | 0.234 | 0.88 | 0.0020 | 0.26 | 1.83 | 0.608 |
| convoy_escort | b | fighter | 1462 | 129.0 | 56.6 | 0.29 | 0.350 | 0.86 | 0.0114 | 0.17 | 1.66 | 0.398 |
| convoy_escort | b | gunship | 430 | 469.2 | 206.6 | 0.68 | 0.304 | 0.92 | 0.0009 | 0.44 | 1.65 | 0.623 |
| convoy_escort | b | strafer | 688 | 87.3 | 38.3 | 0.59 | 0.127 | 0.53 | 0.0339 | 0.31 | 2.39 | 0.298 |
| convoy_escort | b | all | 2580 | 174.6 | 76.7 | 0.44 | 0.250 | 0.78 | 0.0156 | 0.27 | 1.85 | 0.417 |
