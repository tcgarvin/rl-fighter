**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.138

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.016 | 0.031 | 0.000 | 0.000 | 0.000 | 0.000 | 84 | 104 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.260 | 0.000 | 0.519 | 0.000 | 0.000 | 0.000 | 40 | 62 | eliminated 0.21, convoy_through 0.03, convoy_destroyed 0.76 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 10.1 | 9.8 | 0.01 | 0.072 | 0.85 | 0.0008 | 0.14 | 1.65 | 0.346 |
| carrier_battle | a | gunship | 430 | 110.7 | 92.1 | 0.21 | 0.120 | 0.91 | 0.0008 | 0.42 | 2.19 | 0.672 |
| carrier_battle | a | strafer | 516 | 15.5 | 17.2 | 0.01 | 0.054 | 0.76 | 0.0012 | 0.33 | 1.67 | 0.500 |
| carrier_battle | a | all | 1978 | 33.3 | 29.6 | 0.06 | 0.091 | 0.85 | 0.0009 | 0.27 | 1.77 | 0.490 |
| carrier_battle | b | fighter | 1032 | 113.3 | 59.2 | 0.22 | 0.352 | 0.79 | 0.0008 | 0.19 | 1.85 | 0.579 |
| carrier_battle | b | gunship | 430 | 532.2 | 130.9 | 0.88 | 0.372 | 0.80 | 0.0009 | 0.50 | 1.73 | 0.694 |
| carrier_battle | b | strafer | 516 | 217.2 | 113.9 | 0.28 | 0.236 | 0.77 | 0.0099 | 0.20 | 2.35 | 0.680 |
| carrier_battle | b | all | 1978 | 231.5 | 89.0 | 0.38 | 0.305 | 0.79 | 0.0032 | 0.27 | 1.95 | 0.635 |
| convoy_escort | a | fighter | 731 | 81.9 | 39.4 | 0.13 | 0.321 | 0.92 | 0.0000 | 0.19 | 1.04 | 0.549 |
| convoy_escort | a | gunship | 215 | 391.2 | 127.0 | 0.42 | 0.259 | 0.94 | 0.0000 | 0.46 | 1.06 | 0.790 |
| convoy_escort | a | strafer | 344 | 131.8 | 48.7 | 0.22 | 0.166 | 0.93 | 0.0000 | 0.26 | 1.20 | 0.676 |
| convoy_escort | a | all | 1290 | 146.7 | 56.5 | 0.20 | 0.230 | 0.93 | 0.0000 | 0.28 | 1.09 | 0.643 |
| convoy_escort | b | fighter | 731 | 205.4 | 51.3 | 0.58 | 0.439 | 0.93 | 0.0001 | 0.22 | 1.27 | 0.645 |
| convoy_escort | b | gunship | 215 | 403.9 | 187.9 | 0.99 | 0.276 | 0.90 | 0.0001 | 0.48 | 1.82 | 0.735 |
| convoy_escort | b | strafer | 344 | 172.0 | 36.4 | 0.79 | 0.141 | 0.82 | 0.0007 | 0.20 | 2.54 | 0.609 |
| convoy_escort | b | all | 1290 | 229.6 | 70.1 | 0.71 | 0.252 | 0.89 | 0.0002 | 0.27 | 1.70 | 0.654 |
