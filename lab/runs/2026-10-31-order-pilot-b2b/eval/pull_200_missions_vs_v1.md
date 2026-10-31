**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.243

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.008 | 0.012 | 0.004 | 0.000 | 0.002 | 0.000 | 85 | 104 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.479 | 0.182 | 0.775 | 0.000 | 0.000 | 0.000 | 51 | 70 | eliminated 0.11, convoy_through 0.09, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.8 | 21.8 | 0.00 | 0.122 | 0.87 | 0.0010 | 0.28 | 1.58 | 0.335 |
| carrier_battle | a | gunship | 860 | 90.1 | 107.0 | 0.13 | 0.172 | 0.95 | 0.0007 | 0.46 | 1.89 | 0.625 |
| carrier_battle | a | strafer | 1032 | 8.0 | 17.2 | 0.00 | 0.064 | 0.82 | 0.0010 | 0.32 | 1.50 | 0.416 |
| carrier_battle | a | all | 3956 | 25.7 | 39.1 | 0.03 | 0.130 | 0.89 | 0.0009 | 0.35 | 1.63 | 0.456 |
| carrier_battle | b | fighter | 2064 | 116.5 | 62.3 | 0.27 | 0.321 | 0.71 | 0.0103 | 0.19 | 2.43 | 0.344 |
| carrier_battle | b | gunship | 860 | 494.1 | 128.2 | 0.88 | 0.311 | 0.84 | 0.0008 | 0.50 | 2.24 | 0.567 |
| carrier_battle | b | strafer | 1032 | 144.6 | 101.7 | 0.45 | 0.219 | 0.59 | 0.0344 | 0.29 | 3.07 | 0.356 |
| carrier_battle | b | all | 3956 | 205.9 | 86.9 | 0.45 | 0.278 | 0.71 | 0.0143 | 0.29 | 2.56 | 0.401 |
| convoy_escort | a | fighter | 1462 | 69.5 | 41.9 | 0.12 | 0.319 | 0.92 | 0.0000 | 0.35 | 1.07 | 0.529 |
| convoy_escort | a | gunship | 430 | 505.6 | 114.2 | 0.57 | 0.313 | 0.94 | 0.0000 | 0.45 | 1.14 | 0.806 |
| convoy_escort | a | strafer | 688 | 129.5 | 36.1 | 0.33 | 0.157 | 0.92 | 0.0001 | 0.26 | 1.36 | 0.632 |
| convoy_escort | a | all | 2580 | 158.2 | 52.4 | 0.25 | 0.245 | 0.92 | 0.0000 | 0.35 | 1.16 | 0.631 |
| convoy_escort | b | fighter | 1462 | 195.2 | 64.0 | 0.56 | 0.396 | 0.89 | 0.0042 | 0.20 | 1.66 | 0.420 |
| convoy_escort | b | gunship | 430 | 430.6 | 230.2 | 1.00 | 0.280 | 0.91 | 0.0002 | 0.47 | 1.89 | 0.612 |
| convoy_escort | b | strafer | 688 | 80.8 | 38.9 | 0.87 | 0.113 | 0.50 | 0.0341 | 0.31 | 2.51 | 0.271 |
| convoy_escort | b | all | 2580 | 203.9 | 85.0 | 0.72 | 0.253 | 0.79 | 0.0119 | 0.29 | 1.93 | 0.415 |
