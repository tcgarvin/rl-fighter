**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.134

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 83 | 99 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.267 | 0.000 | 0.535 | 0.000 | 0.000 | 0.000 | 38 | 50 | eliminated 0.23, convoy_through 0.00, convoy_destroyed 0.77 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 6.6 | 11.7 | 0.00 | 0.064 | 0.79 | 0.0001 | 0.14 | 1.66 | 0.336 |
| carrier_battle | a | gunship | 430 | 67.7 | 66.1 | 0.15 | 0.097 | 0.93 | 0.0002 | 0.44 | 1.92 | 0.680 |
| carrier_battle | a | strafer | 516 | 9.8 | 14.8 | 0.00 | 0.045 | 0.77 | 0.0004 | 0.36 | 1.49 | 0.475 |
| carrier_battle | a | all | 1978 | 20.7 | 24.3 | 0.03 | 0.074 | 0.83 | 0.0002 | 0.27 | 1.67 | 0.471 |
| carrier_battle | b | fighter | 1032 | 129.8 | 64.7 | 0.29 | 0.307 | 0.75 | 0.0006 | 0.21 | 2.30 | 0.551 |
| carrier_battle | b | gunship | 430 | 491.6 | 127.2 | 0.94 | 0.336 | 0.78 | 0.0009 | 0.49 | 1.73 | 0.720 |
| carrier_battle | b | strafer | 516 | 221.0 | 108.8 | 0.33 | 0.224 | 0.74 | 0.0080 | 0.20 | 2.49 | 0.661 |
| carrier_battle | b | all | 1978 | 232.3 | 89.8 | 0.44 | 0.280 | 0.75 | 0.0025 | 0.27 | 2.23 | 0.616 |
| convoy_escort | a | fighter | 731 | 94.5 | 47.5 | 0.15 | 0.352 | 0.92 | 0.0001 | 0.20 | 1.06 | 0.664 |
| convoy_escort | a | gunship | 215 | 383.2 | 98.5 | 0.46 | 0.250 | 0.93 | 0.0000 | 0.44 | 1.04 | 0.812 |
| convoy_escort | a | strafer | 344 | 90.8 | 37.9 | 0.16 | 0.156 | 0.90 | 0.0000 | 0.31 | 1.13 | 0.642 |
| convoy_escort | a | all | 1290 | 141.6 | 53.5 | 0.21 | 0.239 | 0.92 | 0.0001 | 0.28 | 1.08 | 0.697 |
| convoy_escort | b | fighter | 731 | 209.3 | 55.2 | 0.62 | 0.444 | 0.94 | 0.0000 | 0.21 | 1.25 | 0.654 |
| convoy_escort | b | gunship | 215 | 373.9 | 159.8 | 0.99 | 0.274 | 0.91 | 0.0001 | 0.48 | 1.79 | 0.741 |
| convoy_escort | b | strafer | 344 | 174.0 | 42.5 | 0.84 | 0.150 | 0.82 | 0.0003 | 0.20 | 2.52 | 0.597 |
| convoy_escort | b | all | 1290 | 227.3 | 69.2 | 0.74 | 0.258 | 0.90 | 0.0001 | 0.26 | 1.68 | 0.655 |
