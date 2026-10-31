**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.652

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.653 | 0.620 | 0.686 | 0.000 | 0.008 | 0.000 | 111 | 134 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.651 | 0.469 | 0.833 | 0.000 | 0.000 | 0.000 | 61 | 72 | eliminated 0.01, convoy_through 0.30, convoy_destroyed 0.68 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 64.3 | 46.1 | 0.04 | 0.302 | 0.81 | 0.0074 | 0.17 | 1.89 | 0.402 |
| carrier_battle | a | gunship | 860 | 442.3 | 166.5 | 0.44 | 0.294 | 0.85 | 0.0014 | 0.50 | 2.81 | 0.538 |
| carrier_battle | a | strafer | 1032 | 113.5 | 92.1 | 0.06 | 0.221 | 0.73 | 0.0119 | 0.23 | 2.41 | 0.505 |
| carrier_battle | a | all | 3956 | 159.3 | 84.3 | 0.13 | 0.269 | 0.80 | 0.0063 | 0.30 | 2.23 | 0.474 |
| carrier_battle | b | fighter | 2064 | 53.1 | 41.8 | 0.02 | 0.289 | 0.80 | 0.0107 | 0.16 | 1.77 | 0.372 |
| carrier_battle | b | gunship | 860 | 303.7 | 152.7 | 0.25 | 0.255 | 0.85 | 0.0013 | 0.49 | 2.67 | 0.508 |
| carrier_battle | b | strafer | 1032 | 91.8 | 92.1 | 0.04 | 0.206 | 0.69 | 0.0233 | 0.27 | 2.42 | 0.461 |
| carrier_battle | b | all | 3956 | 117.7 | 79.0 | 0.08 | 0.242 | 0.79 | 0.0106 | 0.30 | 2.13 | 0.441 |
| convoy_escort | a | fighter | 1462 | 172.4 | 60.5 | 0.38 | 0.370 | 0.90 | 0.0048 | 0.17 | 1.73 | 0.454 |
| convoy_escort | a | gunship | 430 | 397.1 | 160.0 | 0.73 | 0.247 | 0.90 | 0.0015 | 0.44 | 1.98 | 0.625 |
| convoy_escort | a | strafer | 688 | 128.4 | 40.0 | 0.59 | 0.149 | 0.65 | 0.0109 | 0.25 | 2.63 | 0.361 |
| convoy_escort | a | all | 2580 | 198.1 | 71.6 | 0.49 | 0.243 | 0.83 | 0.0057 | 0.25 | 2.01 | 0.466 |
| convoy_escort | b | fighter | 1462 | 141.6 | 63.5 | 0.31 | 0.348 | 0.85 | 0.0129 | 0.17 | 1.77 | 0.395 |
| convoy_escort | b | gunship | 430 | 439.1 | 190.4 | 0.66 | 0.281 | 0.91 | 0.0020 | 0.44 | 1.80 | 0.614 |
| convoy_escort | b | strafer | 688 | 87.7 | 42.1 | 0.59 | 0.124 | 0.52 | 0.0479 | 0.32 | 2.54 | 0.289 |
| convoy_escort | b | all | 2580 | 176.8 | 78.9 | 0.44 | 0.240 | 0.77 | 0.0206 | 0.27 | 1.98 | 0.409 |
