**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.195

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.000 | 0.004 | 0.000 | 0.000 | 0.000 | 79 | 98 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.388 | 0.000 | 0.775 | 0.000 | 0.000 | 0.000 | 37 | 50 | eliminated 0.11, convoy_through 0.00, convoy_destroyed 0.89 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.6 | 16.7 | 0.00 | 0.111 | 0.86 | 0.0002 | 0.26 | 1.44 | 0.315 |
| carrier_battle | a | gunship | 860 | 89.1 | 72.9 | 0.17 | 0.168 | 0.94 | 0.0004 | 0.43 | 1.65 | 0.570 |
| carrier_battle | a | strafer | 1032 | 9.6 | 16.8 | 0.00 | 0.071 | 0.83 | 0.0006 | 0.30 | 1.32 | 0.434 |
| carrier_battle | a | all | 3956 | 26.3 | 29.0 | 0.04 | 0.126 | 0.88 | 0.0003 | 0.33 | 1.45 | 0.425 |
| carrier_battle | b | fighter | 2064 | 126.9 | 54.6 | 0.30 | 0.262 | 0.74 | 0.0004 | 0.21 | 2.53 | 0.560 |
| carrier_battle | b | gunship | 860 | 463.0 | 123.5 | 0.94 | 0.309 | 0.80 | 0.0005 | 0.48 | 1.90 | 0.752 |
| carrier_battle | b | strafer | 1032 | 195.9 | 104.2 | 0.32 | 0.201 | 0.73 | 0.0029 | 0.19 | 2.53 | 0.666 |
| carrier_battle | b | all | 3956 | 218.0 | 82.5 | 0.44 | 0.251 | 0.75 | 0.0010 | 0.26 | 2.39 | 0.627 |
| convoy_escort | a | fighter | 1462 | 75.7 | 41.8 | 0.12 | 0.342 | 0.92 | 0.0000 | 0.32 | 1.01 | 0.579 |
| convoy_escort | a | gunship | 430 | 532.2 | 124.5 | 0.63 | 0.355 | 0.94 | 0.0000 | 0.41 | 1.03 | 0.802 |
| convoy_escort | a | strafer | 688 | 104.0 | 34.2 | 0.24 | 0.165 | 0.91 | 0.0000 | 0.24 | 1.11 | 0.654 |
| convoy_escort | a | all | 2580 | 159.3 | 53.6 | 0.24 | 0.277 | 0.92 | 0.0000 | 0.32 | 1.04 | 0.657 |
| convoy_escort | b | fighter | 1462 | 187.7 | 47.8 | 0.58 | 0.421 | 0.93 | 0.0000 | 0.21 | 1.28 | 0.651 |
| convoy_escort | b | gunship | 430 | 381.0 | 172.4 | 1.00 | 0.273 | 0.92 | 0.0000 | 0.48 | 1.58 | 0.755 |
| convoy_escort | b | strafer | 688 | 172.6 | 50.5 | 0.80 | 0.155 | 0.83 | 0.0002 | 0.20 | 2.53 | 0.618 |
| convoy_escort | b | all | 2580 | 215.9 | 69.3 | 0.71 | 0.253 | 0.90 | 0.0001 | 0.26 | 1.66 | 0.663 |
