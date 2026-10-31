**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.109

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 76 | 93 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.219 | 0.000 | 0.438 | 0.000 | 0.000 | 0.000 | 39 | 64 | eliminated 0.24, convoy_through 0.04, convoy_destroyed 0.72 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.2 | 10.4 | 0.00 | 0.114 | 0.88 | 0.0004 | 0.27 | 1.33 | 0.164 |
| carrier_battle | a | gunship | 860 | 49.9 | 57.1 | 0.16 | 0.154 | 0.95 | 0.0009 | 0.49 | 1.64 | 0.407 |
| carrier_battle | a | strafer | 1032 | 6.5 | 13.3 | 0.00 | 0.076 | 0.83 | 0.0007 | 0.32 | 1.31 | 0.268 |
| carrier_battle | a | all | 3956 | 15.7 | 21.3 | 0.04 | 0.122 | 0.89 | 0.0007 | 0.36 | 1.39 | 0.271 |
| carrier_battle | b | fighter | 2064 | 122.0 | 58.2 | 0.34 | 0.270 | 0.76 | 0.0004 | 0.21 | 2.39 | 0.564 |
| carrier_battle | b | gunship | 860 | 444.4 | 116.5 | 0.96 | 0.305 | 0.79 | 0.0004 | 0.47 | 1.79 | 0.747 |
| carrier_battle | b | strafer | 1032 | 210.1 | 103.5 | 0.40 | 0.197 | 0.74 | 0.0032 | 0.19 | 2.65 | 0.665 |
| carrier_battle | b | all | 3956 | 215.1 | 82.7 | 0.49 | 0.247 | 0.76 | 0.0011 | 0.26 | 2.33 | 0.628 |
| convoy_escort | a | fighter | 1462 | 45.5 | 39.2 | 0.02 | 0.347 | 0.91 | 0.0000 | 0.35 | 1.01 | 0.319 |
| convoy_escort | a | gunship | 430 | 459.2 | 145.8 | 0.47 | 0.368 | 0.95 | 0.0006 | 0.48 | 1.01 | 0.636 |
| convoy_escort | a | strafer | 688 | 87.9 | 32.5 | 0.13 | 0.182 | 0.92 | 0.0000 | 0.26 | 1.10 | 0.477 |
| convoy_escort | a | all | 2580 | 125.8 | 55.2 | 0.13 | 0.292 | 0.92 | 0.0002 | 0.37 | 1.03 | 0.456 |
| convoy_escort | b | fighter | 1462 | 197.2 | 49.7 | 0.67 | 0.408 | 0.93 | 0.0000 | 0.22 | 1.35 | 0.643 |
| convoy_escort | b | gunship | 430 | 347.2 | 178.9 | 1.00 | 0.247 | 0.89 | 0.0000 | 0.50 | 1.68 | 0.729 |
| convoy_escort | b | strafer | 688 | 186.4 | 65.3 | 0.83 | 0.157 | 0.85 | 0.0008 | 0.19 | 2.73 | 0.636 |
| convoy_escort | b | all | 2580 | 219.3 | 75.4 | 0.77 | 0.242 | 0.90 | 0.0002 | 0.27 | 1.78 | 0.659 |
