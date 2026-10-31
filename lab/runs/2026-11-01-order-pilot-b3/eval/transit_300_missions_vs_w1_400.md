**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.186

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.008 | 0.008 | 0.008 | 0.000 | 0.000 | 0.000 | 82 | 101 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.364 | 0.000 | 0.729 | 0.000 | 0.000 | 0.000 | 37 | 46 | eliminated 0.14, convoy_destroyed 0.86 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 7.7 | 13.9 | 0.00 | 0.072 | 0.81 | 0.0001 | 0.12 | 1.70 | 0.380 |
| carrier_battle | a | gunship | 430 | 91.1 | 83.1 | 0.16 | 0.117 | 0.93 | 0.0000 | 0.44 | 1.90 | 0.707 |
| carrier_battle | a | strafer | 516 | 10.5 | 15.9 | 0.01 | 0.044 | 0.76 | 0.0004 | 0.35 | 1.55 | 0.507 |
| carrier_battle | a | all | 1978 | 26.6 | 29.4 | 0.04 | 0.084 | 0.84 | 0.0001 | 0.27 | 1.71 | 0.506 |
| carrier_battle | b | fighter | 1032 | 125.6 | 61.8 | 0.31 | 0.315 | 0.75 | 0.0003 | 0.21 | 2.24 | 0.553 |
| carrier_battle | b | gunship | 430 | 501.3 | 118.7 | 0.93 | 0.339 | 0.78 | 0.0007 | 0.49 | 1.73 | 0.719 |
| carrier_battle | b | strafer | 516 | 213.1 | 110.1 | 0.30 | 0.232 | 0.74 | 0.0076 | 0.20 | 2.45 | 0.651 |
| carrier_battle | b | all | 1978 | 230.1 | 86.8 | 0.44 | 0.287 | 0.76 | 0.0021 | 0.27 | 2.18 | 0.616 |
| convoy_escort | a | fighter | 731 | 104.4 | 45.8 | 0.20 | 0.370 | 0.92 | 0.0000 | 0.16 | 1.06 | 0.732 |
| convoy_escort | a | gunship | 215 | 400.3 | 100.6 | 0.50 | 0.274 | 0.93 | 0.0000 | 0.44 | 1.03 | 0.828 |
| convoy_escort | a | strafer | 344 | 111.6 | 37.2 | 0.23 | 0.175 | 0.91 | 0.0000 | 0.29 | 1.06 | 0.704 |
| convoy_escort | a | all | 1290 | 155.6 | 52.6 | 0.26 | 0.259 | 0.92 | 0.0000 | 0.26 | 1.05 | 0.749 |
| convoy_escort | b | fighter | 731 | 204.8 | 55.3 | 0.60 | 0.458 | 0.94 | 0.0001 | 0.21 | 1.23 | 0.664 |
| convoy_escort | b | gunship | 215 | 380.2 | 160.5 | 0.99 | 0.285 | 0.92 | 0.0000 | 0.48 | 1.71 | 0.746 |
| convoy_escort | b | strafer | 344 | 170.1 | 36.8 | 0.84 | 0.149 | 0.80 | 0.0000 | 0.20 | 2.48 | 0.587 |
| convoy_escort | b | all | 1290 | 224.8 | 67.9 | 0.73 | 0.264 | 0.90 | 0.0001 | 0.26 | 1.64 | 0.659 |
