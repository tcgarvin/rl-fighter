**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.157

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 81 | 97 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.314 | 0.004 | 0.624 | 0.000 | 0.000 | 0.000 | 38 | 56 | eliminated 0.17, convoy_through 0.02, convoy_destroyed 0.81 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 11.5 | 10.1 | 0.01 | 0.102 | 0.89 | 0.0003 | 0.25 | 1.38 | 0.350 |
| carrier_battle | a | gunship | 860 | 81.5 | 96.8 | 0.15 | 0.179 | 0.95 | 0.0002 | 0.45 | 1.73 | 0.612 |
| carrier_battle | a | strafer | 1032 | 8.7 | 12.8 | 0.01 | 0.058 | 0.83 | 0.0003 | 0.28 | 1.45 | 0.439 |
| carrier_battle | a | all | 3956 | 26.0 | 29.7 | 0.04 | 0.126 | 0.90 | 0.0003 | 0.33 | 1.47 | 0.461 |
| carrier_battle | b | fighter | 2064 | 115.3 | 55.1 | 0.30 | 0.291 | 0.79 | 0.0003 | 0.19 | 2.15 | 0.586 |
| carrier_battle | b | gunship | 860 | 475.6 | 135.4 | 0.91 | 0.335 | 0.82 | 0.0002 | 0.48 | 1.70 | 0.740 |
| carrier_battle | b | strafer | 1032 | 197.6 | 101.7 | 0.29 | 0.203 | 0.74 | 0.0030 | 0.19 | 2.52 | 0.678 |
| carrier_battle | b | all | 3956 | 215.1 | 84.7 | 0.43 | 0.265 | 0.79 | 0.0010 | 0.26 | 2.15 | 0.645 |
| convoy_escort | a | fighter | 1462 | 60.0 | 43.1 | 0.07 | 0.358 | 0.92 | 0.0000 | 0.33 | 1.02 | 0.492 |
| convoy_escort | a | gunship | 430 | 507.0 | 128.5 | 0.57 | 0.361 | 0.94 | 0.0000 | 0.44 | 1.04 | 0.778 |
| convoy_escort | a | strafer | 688 | 113.6 | 33.5 | 0.23 | 0.185 | 0.91 | 0.0000 | 0.25 | 1.12 | 0.611 |
| convoy_escort | a | all | 2580 | 148.8 | 54.8 | 0.20 | 0.288 | 0.92 | 0.0000 | 0.34 | 1.05 | 0.603 |
| convoy_escort | b | fighter | 1462 | 188.0 | 47.1 | 0.60 | 0.413 | 0.92 | 0.0000 | 0.21 | 1.30 | 0.645 |
| convoy_escort | b | gunship | 430 | 357.3 | 182.9 | 1.00 | 0.261 | 0.91 | 0.0001 | 0.48 | 1.59 | 0.747 |
| convoy_escort | b | strafer | 688 | 181.7 | 54.8 | 0.77 | 0.163 | 0.83 | 0.0004 | 0.19 | 2.58 | 0.628 |
| convoy_escort | b | all | 2580 | 214.5 | 71.8 | 0.71 | 0.251 | 0.90 | 0.0001 | 0.26 | 1.69 | 0.661 |
