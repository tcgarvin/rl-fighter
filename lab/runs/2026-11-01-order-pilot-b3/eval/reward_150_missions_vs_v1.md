**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.719

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.734 | 0.756 | 0.713 | 0.000 | 0.006 | 0.000 | 107 | 129 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.703 | 0.415 | 0.992 | 0.000 | 0.000 | 0.000 | 49 | 72 | eliminated 0.01, convoy_through 0.20, convoy_destroyed 0.79 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 65.4 | 39.9 | 0.04 | 0.261 | 0.82 | 0.0020 | 0.20 | 1.87 | 0.597 |
| carrier_battle | a | gunship | 860 | 512.2 | 177.0 | 0.59 | 0.270 | 0.82 | 0.0018 | 0.49 | 2.92 | 0.708 |
| carrier_battle | a | strafer | 1032 | 103.5 | 70.2 | 0.03 | 0.163 | 0.73 | 0.0019 | 0.19 | 2.15 | 0.676 |
| carrier_battle | a | all | 3956 | 172.5 | 77.6 | 0.16 | 0.230 | 0.80 | 0.0019 | 0.30 | 2.17 | 0.655 |
| carrier_battle | b | fighter | 2064 | 48.9 | 33.8 | 0.02 | 0.272 | 0.81 | 0.0063 | 0.15 | 1.70 | 0.378 |
| carrier_battle | b | gunship | 860 | 302.0 | 153.3 | 0.28 | 0.282 | 0.86 | 0.0007 | 0.49 | 2.34 | 0.524 |
| carrier_battle | b | strafer | 1032 | 83.7 | 85.4 | 0.02 | 0.214 | 0.71 | 0.0163 | 0.26 | 2.09 | 0.498 |
| carrier_battle | b | all | 3956 | 113.0 | 73.2 | 0.08 | 0.255 | 0.80 | 0.0067 | 0.29 | 1.94 | 0.456 |
| convoy_escort | a | fighter | 1462 | 162.8 | 49.6 | 0.40 | 0.404 | 0.93 | 0.0009 | 0.22 | 1.27 | 0.669 |
| convoy_escort | a | gunship | 430 | 358.8 | 125.9 | 0.78 | 0.224 | 0.91 | 0.0011 | 0.41 | 1.73 | 0.771 |
| convoy_escort | a | strafer | 688 | 181.0 | 49.7 | 0.48 | 0.183 | 0.87 | 0.0004 | 0.17 | 1.76 | 0.701 |
| convoy_escort | a | all | 2580 | 200.3 | 62.3 | 0.49 | 0.248 | 0.91 | 0.0008 | 0.25 | 1.48 | 0.701 |
| convoy_escort | b | fighter | 1462 | 126.4 | 53.1 | 0.28 | 0.354 | 0.86 | 0.0083 | 0.18 | 1.56 | 0.406 |
| convoy_escort | b | gunship | 430 | 474.6 | 210.2 | 0.82 | 0.308 | 0.91 | 0.0008 | 0.45 | 1.73 | 0.625 |
| convoy_escort | b | strafer | 688 | 74.4 | 37.5 | 0.62 | 0.120 | 0.53 | 0.0379 | 0.32 | 2.34 | 0.276 |
| convoy_escort | b | all | 2580 | 170.6 | 75.1 | 0.46 | 0.251 | 0.78 | 0.0154 | 0.28 | 1.80 | 0.416 |
