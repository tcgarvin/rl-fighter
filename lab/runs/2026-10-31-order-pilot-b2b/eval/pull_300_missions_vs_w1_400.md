**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.197

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.008 | 0.012 | 0.004 | 0.000 | 0.000 | 0.000 | 80 | 97 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.386 | 0.000 | 0.771 | 0.000 | 0.000 | 0.000 | 37 | 50 | eliminated 0.11, convoy_through 0.00, convoy_destroyed 0.89 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.9 | 18.0 | 0.00 | 0.108 | 0.86 | 0.0003 | 0.27 | 1.47 | 0.376 |
| carrier_battle | a | gunship | 860 | 112.9 | 90.0 | 0.17 | 0.178 | 0.94 | 0.0003 | 0.44 | 1.68 | 0.680 |
| carrier_battle | a | strafer | 1032 | 9.7 | 18.2 | 0.00 | 0.068 | 0.82 | 0.0007 | 0.31 | 1.39 | 0.455 |
| carrier_battle | a | all | 3956 | 31.7 | 33.7 | 0.04 | 0.130 | 0.88 | 0.0004 | 0.33 | 1.49 | 0.495 |
| carrier_battle | b | fighter | 2064 | 118.7 | 56.2 | 0.29 | 0.266 | 0.75 | 0.0005 | 0.20 | 2.40 | 0.566 |
| carrier_battle | b | gunship | 860 | 479.0 | 124.8 | 0.94 | 0.311 | 0.81 | 0.0004 | 0.48 | 1.90 | 0.749 |
| carrier_battle | b | strafer | 1032 | 196.7 | 96.3 | 0.29 | 0.198 | 0.73 | 0.0030 | 0.20 | 2.59 | 0.665 |
| carrier_battle | b | all | 3956 | 217.4 | 81.6 | 0.43 | 0.251 | 0.76 | 0.0011 | 0.26 | 2.34 | 0.631 |
| convoy_escort | a | fighter | 1462 | 72.1 | 41.0 | 0.13 | 0.344 | 0.92 | 0.0000 | 0.33 | 1.01 | 0.615 |
| convoy_escort | a | gunship | 430 | 562.3 | 126.5 | 0.62 | 0.359 | 0.94 | 0.0000 | 0.45 | 1.04 | 0.860 |
| convoy_escort | a | strafer | 688 | 109.1 | 33.1 | 0.27 | 0.171 | 0.91 | 0.0000 | 0.25 | 1.11 | 0.670 |
| convoy_escort | a | all | 2580 | 163.7 | 53.2 | 0.25 | 0.282 | 0.92 | 0.0000 | 0.34 | 1.04 | 0.695 |
| convoy_escort | b | fighter | 1462 | 179.7 | 45.8 | 0.54 | 0.417 | 0.93 | 0.0000 | 0.21 | 1.24 | 0.652 |
| convoy_escort | b | gunship | 430 | 397.0 | 178.8 | 1.00 | 0.286 | 0.91 | 0.0001 | 0.48 | 1.54 | 0.760 |
| convoy_escort | b | strafer | 688 | 169.5 | 47.3 | 0.77 | 0.156 | 0.83 | 0.0003 | 0.20 | 2.61 | 0.612 |
| convoy_escort | b | all | 2580 | 213.2 | 68.4 | 0.68 | 0.256 | 0.90 | 0.0001 | 0.26 | 1.65 | 0.663 |
