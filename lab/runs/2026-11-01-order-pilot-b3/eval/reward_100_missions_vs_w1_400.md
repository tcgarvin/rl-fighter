**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.471

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.442 | 0.512 | 0.372 | 0.000 | 0.000 | 0.000 | 101 | 125 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.500 | 0.023 | 0.977 | 0.000 | 0.000 | 0.000 | 40 | 53 | eliminated 0.02, convoy_through 0.01, convoy_destroyed 0.98 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 52.3 | 31.1 | 0.03 | 0.261 | 0.82 | 0.0010 | 0.17 | 1.58 | 0.595 |
| carrier_battle | a | gunship | 430 | 430.4 | 190.5 | 0.45 | 0.284 | 0.84 | 0.0010 | 0.48 | 2.60 | 0.712 |
| carrier_battle | a | strafer | 516 | 94.5 | 55.9 | 0.02 | 0.174 | 0.74 | 0.0011 | 0.19 | 1.95 | 0.669 |
| carrier_battle | a | all | 1978 | 145.5 | 72.2 | 0.12 | 0.242 | 0.81 | 0.0010 | 0.29 | 1.90 | 0.656 |
| carrier_battle | b | fighter | 1032 | 63.3 | 35.8 | 0.04 | 0.271 | 0.80 | 0.0010 | 0.16 | 1.79 | 0.576 |
| carrier_battle | b | gunship | 430 | 458.4 | 183.6 | 0.45 | 0.308 | 0.84 | 0.0003 | 0.49 | 2.25 | 0.709 |
| carrier_battle | b | strafer | 516 | 108.8 | 72.2 | 0.03 | 0.203 | 0.74 | 0.0028 | 0.20 | 2.01 | 0.675 |
| carrier_battle | b | all | 1978 | 161.1 | 77.4 | 0.13 | 0.264 | 0.80 | 0.0012 | 0.29 | 1.95 | 0.644 |
| convoy_escort | a | fighter | 731 | 144.6 | 40.0 | 0.33 | 0.403 | 0.93 | 0.0000 | 0.19 | 1.16 | 0.664 |
| convoy_escort | a | gunship | 215 | 396.4 | 145.0 | 0.76 | 0.279 | 0.93 | 0.0002 | 0.43 | 1.32 | 0.776 |
| convoy_escort | a | strafer | 344 | 181.4 | 49.4 | 0.45 | 0.191 | 0.89 | 0.0002 | 0.16 | 1.72 | 0.712 |
| convoy_escort | a | all | 1290 | 196.4 | 60.0 | 0.43 | 0.267 | 0.92 | 0.0001 | 0.24 | 1.34 | 0.702 |
| convoy_escort | b | fighter | 731 | 151.9 | 45.1 | 0.35 | 0.417 | 0.93 | 0.0003 | 0.19 | 1.24 | 0.653 |
| convoy_escort | b | gunship | 215 | 418.6 | 157.2 | 0.88 | 0.283 | 0.92 | 0.0000 | 0.45 | 1.49 | 0.766 |
| convoy_escort | b | strafer | 344 | 159.6 | 39.8 | 0.54 | 0.167 | 0.83 | 0.0002 | 0.20 | 2.21 | 0.615 |
| convoy_escort | b | all | 1290 | 198.4 | 62.4 | 0.49 | 0.263 | 0.90 | 0.0002 | 0.25 | 1.54 | 0.670 |
