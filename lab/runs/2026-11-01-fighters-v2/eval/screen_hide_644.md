**policy:ppo_bc_644.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.109

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.105 | 0.116 | 0.093 | 0.000 | 0.000 | 0.000 | 100 | 123 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.112 | 0.140 | 0.085 | 0.000 | 0.000 | 0.000 | 53 | 75 | eliminated 0.41, convoy_through 0.11, convoy_destroyed 0.47 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 34.5 | 52.7 | 0.02 | 0.326 | 0.78 | 0.0378 | 0.04 | 1.93 | 0.365 |
| carrier_battle | a | gunship | 430 | 186.0 | 98.0 | 0.18 | 0.226 | 0.83 | 0.0018 | 0.33 | 2.26 | 0.496 |
| carrier_battle | a | strafer | 516 | 59.6 | 70.7 | 0.03 | 0.174 | 0.63 | 0.0482 | 0.30 | 2.02 | 0.409 |
| carrier_battle | a | all | 1978 | 74.0 | 67.2 | 0.06 | 0.223 | 0.76 | 0.0297 | 0.19 | 2.02 | 0.415 |
| carrier_battle | b | fighter | 1032 | 89.3 | 61.0 | 0.06 | 0.260 | 0.84 | 0.0083 | 0.26 | 2.23 | 0.676 |
| carrier_battle | b | gunship | 430 | 534.2 | 155.3 | 0.83 | 0.217 | 0.80 | 0.0033 | 0.47 | 3.48 | 0.746 |
| carrier_battle | b | strafer | 516 | 120.0 | 111.8 | 0.09 | 0.191 | 0.70 | 0.0038 | 0.19 | 2.30 | 0.664 |
| carrier_battle | b | all | 1978 | 194.0 | 94.8 | 0.23 | 0.217 | 0.80 | 0.0056 | 0.32 | 2.52 | 0.699 |
| convoy_escort | a | fighter | 774 | 73.8 | 56.9 | 0.07 | 0.318 | 0.84 | 0.0056 | 0.09 | 1.52 | 0.472 |
| convoy_escort | a | gunship | 258 | 221.0 | 112.7 | 0.19 | 0.276 | 0.89 | 0.0000 | 0.37 | 1.07 | 0.617 |
| convoy_escort | a | strafer | 516 | 149.9 | 98.4 | 0.15 | 0.255 | 0.84 | 0.0026 | 0.26 | 2.13 | 0.471 |
| convoy_escort | a | all | 1548 | 123.7 | 80.0 | 0.12 | 0.274 | 0.85 | 0.0036 | 0.20 | 1.65 | 0.496 |
| convoy_escort | b | fighter | 774 | 153.0 | 80.3 | 0.26 | 0.354 | 0.80 | 0.0005 | 0.28 | 1.16 | 0.757 |
| convoy_escort | b | gunship | 258 | 435.5 | 130.4 | 0.88 | 0.204 | 0.76 | 0.0013 | 0.39 | 1.61 | 0.831 |
| convoy_escort | b | strafer | 516 | 323.4 | 90.2 | 0.59 | 0.191 | 0.81 | 0.0001 | 0.15 | 1.67 | 0.793 |
| convoy_escort | b | all | 1548 | 256.9 | 92.0 | 0.47 | 0.221 | 0.80 | 0.0005 | 0.26 | 1.40 | 0.786 |
