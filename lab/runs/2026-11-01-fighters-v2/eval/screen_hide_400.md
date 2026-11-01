**policy:ppo_bc_400.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.250

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.287 | 0.326 | 0.248 | 0.000 | 0.004 | 0.000 | 98 | 127 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.213 | 0.287 | 0.140 | 0.000 | 0.000 | 0.000 | 54 | 75 | eliminated 0.39, convoy_through 0.19, convoy_destroyed 0.43 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 44.8 | 56.6 | 0.02 | 0.314 | 0.80 | 0.0202 | 0.06 | 1.89 | 0.468 |
| carrier_battle | a | gunship | 430 | 277.1 | 124.7 | 0.28 | 0.252 | 0.84 | 0.0012 | 0.37 | 2.33 | 0.589 |
| carrier_battle | a | strafer | 516 | 82.5 | 58.2 | 0.02 | 0.172 | 0.69 | 0.0187 | 0.27 | 2.20 | 0.486 |
| carrier_battle | a | all | 1978 | 105.1 | 71.8 | 0.08 | 0.232 | 0.78 | 0.0139 | 0.21 | 2.07 | 0.510 |
| carrier_battle | b | fighter | 1032 | 75.1 | 55.0 | 0.03 | 0.283 | 0.86 | 0.0058 | 0.23 | 1.88 | 0.686 |
| carrier_battle | b | gunship | 430 | 504.3 | 169.4 | 0.64 | 0.250 | 0.84 | 0.0028 | 0.46 | 2.81 | 0.753 |
| carrier_battle | b | strafer | 516 | 100.5 | 90.3 | 0.04 | 0.192 | 0.75 | 0.0016 | 0.19 | 2.13 | 0.681 |
| carrier_battle | b | all | 1978 | 175.0 | 89.1 | 0.17 | 0.237 | 0.83 | 0.0039 | 0.31 | 2.14 | 0.710 |
| convoy_escort | a | fighter | 774 | 72.5 | 49.8 | 0.09 | 0.262 | 0.86 | 0.0004 | 0.11 | 1.41 | 0.599 |
| convoy_escort | a | gunship | 258 | 291.6 | 155.2 | 0.24 | 0.279 | 0.89 | 0.0000 | 0.38 | 1.14 | 0.725 |
| convoy_escort | a | strafer | 516 | 133.0 | 87.9 | 0.16 | 0.223 | 0.85 | 0.0013 | 0.22 | 1.92 | 0.511 |
| convoy_escort | a | all | 1548 | 129.2 | 80.1 | 0.14 | 0.248 | 0.86 | 0.0006 | 0.20 | 1.54 | 0.594 |
| convoy_escort | b | fighter | 774 | 145.8 | 77.6 | 0.22 | 0.374 | 0.84 | 0.0006 | 0.24 | 1.16 | 0.763 |
| convoy_escort | b | gunship | 258 | 443.6 | 146.2 | 0.79 | 0.221 | 0.75 | 0.0003 | 0.41 | 1.76 | 0.815 |
| convoy_escort | b | strafer | 516 | 293.0 | 86.2 | 0.46 | 0.197 | 0.83 | 0.0003 | 0.16 | 1.59 | 0.789 |
| convoy_escort | b | all | 1548 | 244.5 | 91.9 | 0.40 | 0.232 | 0.82 | 0.0004 | 0.25 | 1.40 | 0.784 |
