**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.167

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.004 | 0.000 | 0.008 | 0.000 | 0.000 | 0.000 | 86 | 104 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.329 | 0.000 | 0.659 | 0.000 | 0.000 | 0.000 | 39 | 48 | eliminated 0.17, convoy_through 0.00, convoy_destroyed 0.83 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 8.0 | 12.1 | 0.01 | 0.066 | 0.80 | 0.0001 | 0.13 | 1.68 | 0.372 |
| carrier_battle | a | gunship | 430 | 75.3 | 77.3 | 0.13 | 0.113 | 0.93 | 0.0002 | 0.43 | 1.89 | 0.697 |
| carrier_battle | a | strafer | 516 | 10.0 | 16.5 | 0.01 | 0.048 | 0.77 | 0.0002 | 0.33 | 1.43 | 0.504 |
| carrier_battle | a | all | 1978 | 23.2 | 27.4 | 0.04 | 0.082 | 0.83 | 0.0001 | 0.25 | 1.66 | 0.495 |
| carrier_battle | b | fighter | 1032 | 129.9 | 63.8 | 0.29 | 0.314 | 0.75 | 0.0002 | 0.21 | 2.27 | 0.555 |
| carrier_battle | b | gunship | 430 | 511.7 | 123.5 | 0.94 | 0.337 | 0.78 | 0.0005 | 0.49 | 1.72 | 0.718 |
| carrier_battle | b | strafer | 516 | 200.5 | 110.9 | 0.27 | 0.233 | 0.75 | 0.0069 | 0.20 | 2.33 | 0.662 |
| carrier_battle | b | all | 1978 | 231.3 | 89.0 | 0.43 | 0.288 | 0.76 | 0.0018 | 0.27 | 2.17 | 0.618 |
| convoy_escort | a | fighter | 731 | 100.1 | 46.7 | 0.15 | 0.360 | 0.92 | 0.0000 | 0.18 | 1.08 | 0.721 |
| convoy_escort | a | gunship | 215 | 402.8 | 102.9 | 0.50 | 0.260 | 0.93 | 0.0000 | 0.44 | 1.01 | 0.825 |
| convoy_escort | a | strafer | 344 | 92.3 | 35.9 | 0.17 | 0.154 | 0.90 | 0.0000 | 0.29 | 1.08 | 0.675 |
| convoy_escort | a | all | 1290 | 148.5 | 53.2 | 0.21 | 0.244 | 0.92 | 0.0000 | 0.27 | 1.07 | 0.738 |
| convoy_escort | b | fighter | 731 | 208.5 | 56.3 | 0.63 | 0.444 | 0.94 | 0.0001 | 0.22 | 1.26 | 0.656 |
| convoy_escort | b | gunship | 215 | 376.1 | 158.7 | 0.99 | 0.271 | 0.91 | 0.0000 | 0.48 | 1.60 | 0.746 |
| convoy_escort | b | strafer | 344 | 175.1 | 39.0 | 0.81 | 0.149 | 0.83 | 0.0000 | 0.20 | 2.46 | 0.595 |
| convoy_escort | b | all | 1290 | 227.5 | 68.7 | 0.74 | 0.257 | 0.90 | 0.0000 | 0.26 | 1.64 | 0.657 |
