**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.255

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.019 | 0.023 | 0.016 | 0.000 | 0.002 | 0.000 | 94 | 112 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.490 | 0.240 | 0.740 | 0.000 | 0.000 | 0.000 | 52 | 71 | eliminated 0.12, convoy_through 0.13, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.2 | 15.6 | 0.00 | 0.075 | 0.83 | 0.0002 | 0.14 | 1.86 | 0.310 |
| carrier_battle | a | gunship | 860 | 84.1 | 107.5 | 0.13 | 0.122 | 0.93 | 0.0003 | 0.44 | 2.07 | 0.665 |
| carrier_battle | a | strafer | 1032 | 11.3 | 23.1 | 0.01 | 0.055 | 0.78 | 0.0012 | 0.38 | 1.76 | 0.451 |
| carrier_battle | a | all | 3956 | 25.0 | 37.5 | 0.03 | 0.091 | 0.85 | 0.0005 | 0.28 | 1.88 | 0.450 |
| carrier_battle | b | fighter | 2064 | 117.5 | 65.3 | 0.24 | 0.339 | 0.72 | 0.0093 | 0.19 | 2.29 | 0.349 |
| carrier_battle | b | gunship | 860 | 538.4 | 133.0 | 0.88 | 0.331 | 0.84 | 0.0012 | 0.50 | 2.12 | 0.562 |
| carrier_battle | b | strafer | 1032 | 145.5 | 96.9 | 0.47 | 0.207 | 0.58 | 0.0428 | 0.30 | 2.98 | 0.352 |
| carrier_battle | b | all | 3956 | 216.3 | 88.3 | 0.44 | 0.284 | 0.71 | 0.0165 | 0.30 | 2.43 | 0.403 |
| convoy_escort | a | fighter | 1462 | 112.7 | 46.5 | 0.23 | 0.333 | 0.92 | 0.0001 | 0.21 | 1.16 | 0.606 |
| convoy_escort | a | gunship | 430 | 373.3 | 91.4 | 0.54 | 0.198 | 0.94 | 0.0000 | 0.44 | 1.15 | 0.798 |
| convoy_escort | a | strafer | 688 | 128.3 | 40.2 | 0.31 | 0.149 | 0.90 | 0.0001 | 0.33 | 1.35 | 0.606 |
| convoy_escort | a | all | 2580 | 160.3 | 52.3 | 0.31 | 0.208 | 0.92 | 0.0001 | 0.30 | 1.21 | 0.654 |
| convoy_escort | b | fighter | 1462 | 216.6 | 63.3 | 0.58 | 0.407 | 0.87 | 0.0078 | 0.20 | 1.65 | 0.420 |
| convoy_escort | b | gunship | 430 | 408.0 | 219.1 | 0.98 | 0.268 | 0.90 | 0.0004 | 0.47 | 2.22 | 0.593 |
| convoy_escort | b | strafer | 688 | 73.5 | 27.9 | 0.91 | 0.101 | 0.44 | 0.0494 | 0.33 | 2.26 | 0.245 |
| convoy_escort | b | all | 2580 | 210.3 | 79.8 | 0.73 | 0.253 | 0.75 | 0.0182 | 0.29 | 1.91 | 0.403 |
