**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.174

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.000 | 0.004 | 0.000 | 0.000 | 0.000 | 80 | 96 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.347 | 0.000 | 0.694 | 0.000 | 0.000 | 0.000 | 37 | 53 | eliminated 0.15, convoy_through 0.01, convoy_destroyed 0.85 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.9 | 15.5 | 0.00 | 0.114 | 0.86 | 0.0004 | 0.25 | 1.40 | 0.265 |
| carrier_battle | a | gunship | 860 | 71.1 | 71.8 | 0.15 | 0.172 | 0.95 | 0.0007 | 0.45 | 1.62 | 0.523 |
| carrier_battle | a | strafer | 1032 | 9.0 | 16.9 | 0.00 | 0.076 | 0.82 | 0.0002 | 0.31 | 1.31 | 0.386 |
| carrier_battle | a | all | 3956 | 21.9 | 28.1 | 0.03 | 0.129 | 0.88 | 0.0005 | 0.33 | 1.43 | 0.377 |
| carrier_battle | b | fighter | 2064 | 125.1 | 55.8 | 0.32 | 0.259 | 0.75 | 0.0005 | 0.20 | 2.56 | 0.559 |
| carrier_battle | b | gunship | 860 | 464.1 | 121.3 | 0.95 | 0.304 | 0.82 | 0.0003 | 0.47 | 1.83 | 0.755 |
| carrier_battle | b | strafer | 1032 | 194.6 | 102.7 | 0.34 | 0.193 | 0.74 | 0.0033 | 0.20 | 2.66 | 0.666 |
| carrier_battle | b | all | 3956 | 216.9 | 82.3 | 0.46 | 0.244 | 0.76 | 0.0011 | 0.26 | 2.43 | 0.627 |
| convoy_escort | a | fighter | 1462 | 73.2 | 41.2 | 0.10 | 0.347 | 0.92 | 0.0000 | 0.30 | 1.01 | 0.520 |
| convoy_escort | a | gunship | 430 | 531.2 | 132.7 | 0.59 | 0.376 | 0.94 | 0.0000 | 0.42 | 1.01 | 0.772 |
| convoy_escort | a | strafer | 688 | 90.6 | 33.4 | 0.19 | 0.169 | 0.91 | 0.0000 | 0.24 | 1.09 | 0.609 |
| convoy_escort | a | all | 2580 | 154.2 | 54.4 | 0.21 | 0.291 | 0.93 | 0.0000 | 0.32 | 1.03 | 0.610 |
| convoy_escort | b | fighter | 1462 | 190.3 | 48.0 | 0.60 | 0.419 | 0.93 | 0.0000 | 0.21 | 1.25 | 0.653 |
| convoy_escort | b | gunship | 430 | 380.0 | 177.5 | 1.00 | 0.271 | 0.90 | 0.0000 | 0.49 | 1.62 | 0.748 |
| convoy_escort | b | strafer | 688 | 183.9 | 56.0 | 0.82 | 0.162 | 0.85 | 0.0002 | 0.19 | 2.59 | 0.628 |
| convoy_escort | b | all | 2580 | 220.2 | 71.7 | 0.73 | 0.255 | 0.90 | 0.0001 | 0.26 | 1.67 | 0.666 |
