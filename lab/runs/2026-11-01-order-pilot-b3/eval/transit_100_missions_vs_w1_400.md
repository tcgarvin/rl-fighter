**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.120

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 84 | 98 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.240 | 0.000 | 0.481 | 0.000 | 0.000 | 0.000 | 38 | 55 | eliminated 0.24, convoy_through 0.02, convoy_destroyed 0.74 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 6.8 | 9.1 | 0.00 | 0.060 | 0.82 | 0.0002 | 0.16 | 1.67 | 0.302 |
| carrier_battle | a | gunship | 430 | 57.7 | 60.3 | 0.16 | 0.090 | 0.91 | 0.0003 | 0.44 | 1.95 | 0.651 |
| carrier_battle | a | strafer | 516 | 9.9 | 15.3 | 0.01 | 0.047 | 0.78 | 0.0009 | 0.35 | 1.53 | 0.472 |
| carrier_battle | a | all | 1978 | 18.7 | 21.8 | 0.04 | 0.070 | 0.84 | 0.0004 | 0.29 | 1.69 | 0.448 |
| carrier_battle | b | fighter | 1032 | 131.3 | 62.4 | 0.30 | 0.322 | 0.75 | 0.0007 | 0.21 | 2.17 | 0.557 |
| carrier_battle | b | gunship | 430 | 498.3 | 118.2 | 0.95 | 0.335 | 0.77 | 0.0007 | 0.49 | 1.71 | 0.709 |
| carrier_battle | b | strafer | 516 | 216.9 | 108.7 | 0.31 | 0.234 | 0.75 | 0.0073 | 0.20 | 2.35 | 0.663 |
| carrier_battle | b | all | 1978 | 233.4 | 86.6 | 0.44 | 0.288 | 0.76 | 0.0023 | 0.27 | 2.12 | 0.618 |
| convoy_escort | a | fighter | 731 | 89.2 | 44.3 | 0.12 | 0.353 | 0.92 | 0.0000 | 0.23 | 1.06 | 0.588 |
| convoy_escort | a | gunship | 215 | 357.0 | 106.0 | 0.42 | 0.238 | 0.94 | 0.0002 | 0.45 | 1.04 | 0.798 |
| convoy_escort | a | strafer | 344 | 107.1 | 39.7 | 0.16 | 0.165 | 0.92 | 0.0003 | 0.30 | 1.16 | 0.623 |
| convoy_escort | a | all | 1290 | 138.6 | 53.4 | 0.18 | 0.234 | 0.92 | 0.0001 | 0.30 | 1.08 | 0.651 |
| convoy_escort | b | fighter | 731 | 204.6 | 52.7 | 0.60 | 0.442 | 0.94 | 0.0000 | 0.22 | 1.26 | 0.645 |
| convoy_escort | b | gunship | 215 | 384.9 | 170.6 | 0.99 | 0.272 | 0.92 | 0.0003 | 0.48 | 1.74 | 0.747 |
| convoy_escort | b | strafer | 344 | 186.3 | 39.5 | 0.83 | 0.153 | 0.82 | 0.0002 | 0.20 | 2.60 | 0.597 |
| convoy_escort | b | all | 1290 | 229.8 | 68.8 | 0.73 | 0.257 | 0.90 | 0.0002 | 0.27 | 1.70 | 0.652 |
