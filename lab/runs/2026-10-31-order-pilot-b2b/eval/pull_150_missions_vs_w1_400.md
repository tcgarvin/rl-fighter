**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.162

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 78 | 95 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.324 | 0.000 | 0.647 | 0.000 | 0.000 | 0.000 | 38 | 55 | eliminated 0.16, convoy_through 0.01, convoy_destroyed 0.82 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.5 | 15.0 | 0.00 | 0.112 | 0.87 | 0.0007 | 0.28 | 1.39 | 0.306 |
| carrier_battle | a | gunship | 860 | 71.1 | 68.5 | 0.17 | 0.156 | 0.95 | 0.0006 | 0.47 | 1.65 | 0.591 |
| carrier_battle | a | strafer | 1032 | 7.3 | 15.3 | 0.01 | 0.069 | 0.82 | 0.0002 | 0.33 | 1.37 | 0.383 |
| carrier_battle | a | all | 3956 | 21.3 | 26.7 | 0.04 | 0.121 | 0.89 | 0.0006 | 0.35 | 1.44 | 0.422 |
| carrier_battle | b | fighter | 2064 | 119.5 | 56.9 | 0.32 | 0.261 | 0.75 | 0.0004 | 0.20 | 2.44 | 0.561 |
| carrier_battle | b | gunship | 860 | 463.7 | 121.5 | 0.95 | 0.311 | 0.80 | 0.0005 | 0.48 | 1.86 | 0.750 |
| carrier_battle | b | strafer | 1032 | 200.4 | 102.8 | 0.33 | 0.196 | 0.74 | 0.0033 | 0.20 | 2.67 | 0.666 |
| carrier_battle | b | all | 3956 | 215.4 | 82.9 | 0.46 | 0.248 | 0.76 | 0.0012 | 0.26 | 2.38 | 0.628 |
| convoy_escort | a | fighter | 1462 | 53.9 | 38.6 | 0.05 | 0.343 | 0.92 | 0.0000 | 0.35 | 1.00 | 0.489 |
| convoy_escort | a | gunship | 430 | 548.3 | 140.8 | 0.55 | 0.389 | 0.95 | 0.0001 | 0.46 | 1.02 | 0.799 |
| convoy_escort | a | strafer | 688 | 96.3 | 32.0 | 0.18 | 0.172 | 0.92 | 0.0000 | 0.27 | 1.11 | 0.602 |
| convoy_escort | a | all | 2580 | 147.6 | 53.9 | 0.17 | 0.294 | 0.93 | 0.0000 | 0.36 | 1.03 | 0.609 |
| convoy_escort | b | fighter | 1462 | 186.9 | 48.4 | 0.62 | 0.409 | 0.93 | 0.0001 | 0.21 | 1.31 | 0.645 |
| convoy_escort | b | gunship | 430 | 364.7 | 181.1 | 1.00 | 0.267 | 0.90 | 0.0000 | 0.49 | 1.66 | 0.738 |
| convoy_escort | b | strafer | 688 | 185.2 | 61.1 | 0.82 | 0.160 | 0.84 | 0.0002 | 0.19 | 2.66 | 0.635 |
| convoy_escort | b | all | 2580 | 216.1 | 73.9 | 0.74 | 0.249 | 0.90 | 0.0001 | 0.26 | 1.72 | 0.661 |
