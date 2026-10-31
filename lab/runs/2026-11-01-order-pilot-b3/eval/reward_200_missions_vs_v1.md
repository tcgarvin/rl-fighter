**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.695

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.707 | 0.690 | 0.725 | 0.000 | 0.006 | 0.000 | 108 | 129 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.682 | 0.411 | 0.953 | 0.000 | 0.000 | 0.000 | 48 | 72 | eliminated 0.02, convoy_through 0.21, convoy_destroyed 0.77 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 60.7 | 37.4 | 0.03 | 0.246 | 0.81 | 0.0021 | 0.22 | 1.85 | 0.616 |
| carrier_battle | a | gunship | 860 | 503.1 | 181.1 | 0.54 | 0.274 | 0.82 | 0.0020 | 0.49 | 2.83 | 0.716 |
| carrier_battle | a | strafer | 1032 | 97.6 | 60.9 | 0.02 | 0.168 | 0.74 | 0.0010 | 0.17 | 1.95 | 0.694 |
| carrier_battle | a | all | 3956 | 166.5 | 74.8 | 0.14 | 0.233 | 0.80 | 0.0018 | 0.31 | 2.09 | 0.669 |
| carrier_battle | b | fighter | 2064 | 51.8 | 32.3 | 0.03 | 0.278 | 0.80 | 0.0066 | 0.15 | 1.70 | 0.380 |
| carrier_battle | b | gunship | 860 | 307.6 | 159.1 | 0.28 | 0.297 | 0.86 | 0.0012 | 0.50 | 2.21 | 0.530 |
| carrier_battle | b | strafer | 1032 | 90.3 | 90.2 | 0.04 | 0.217 | 0.70 | 0.0160 | 0.25 | 2.06 | 0.505 |
| carrier_battle | b | all | 3956 | 117.5 | 75.0 | 0.09 | 0.262 | 0.80 | 0.0071 | 0.29 | 1.90 | 0.460 |
| convoy_escort | a | fighter | 1462 | 146.6 | 48.8 | 0.39 | 0.398 | 0.93 | 0.0005 | 0.23 | 1.23 | 0.683 |
| convoy_escort | a | gunship | 430 | 392.6 | 125.3 | 0.77 | 0.240 | 0.91 | 0.0006 | 0.40 | 1.61 | 0.784 |
| convoy_escort | a | strafer | 688 | 186.9 | 49.5 | 0.47 | 0.193 | 0.87 | 0.0005 | 0.15 | 1.56 | 0.727 |
| convoy_escort | a | all | 2580 | 198.3 | 61.8 | 0.47 | 0.255 | 0.91 | 0.0005 | 0.25 | 1.38 | 0.718 |
| convoy_escort | b | fighter | 1462 | 129.4 | 51.9 | 0.27 | 0.370 | 0.87 | 0.0077 | 0.18 | 1.51 | 0.413 |
| convoy_escort | b | gunship | 430 | 501.6 | 217.8 | 0.86 | 0.322 | 0.92 | 0.0005 | 0.45 | 1.61 | 0.627 |
| convoy_escort | b | strafer | 688 | 78.0 | 37.6 | 0.62 | 0.119 | 0.55 | 0.0366 | 0.32 | 2.41 | 0.291 |
| convoy_escort | b | all | 2580 | 177.7 | 75.7 | 0.46 | 0.257 | 0.79 | 0.0147 | 0.28 | 1.77 | 0.424 |
