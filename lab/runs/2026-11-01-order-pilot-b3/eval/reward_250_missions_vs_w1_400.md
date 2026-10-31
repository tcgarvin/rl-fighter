**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.500

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.508 | 0.434 | 0.581 | 0.000 | 0.008 | 0.000 | 101 | 126 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 258 | 0.492 | 0.023 | 0.961 | 0.000 | 0.000 | 0.000 | 36 | 49 | eliminated 0.03, convoy_through 0.00, convoy_destroyed 0.97 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 55.6 | 33.9 | 0.03 | 0.277 | 0.81 | 0.0006 | 0.19 | 1.58 | 0.645 |
| carrier_battle | a | gunship | 430 | 468.6 | 188.8 | 0.43 | 0.307 | 0.85 | 0.0008 | 0.46 | 2.50 | 0.738 |
| carrier_battle | a | strafer | 516 | 88.2 | 48.0 | 0.01 | 0.177 | 0.75 | 0.0004 | 0.18 | 1.88 | 0.688 |
| carrier_battle | a | all | 1978 | 153.9 | 71.2 | 0.11 | 0.259 | 0.82 | 0.0007 | 0.29 | 1.86 | 0.690 |
| carrier_battle | b | fighter | 1032 | 60.8 | 32.3 | 0.04 | 0.261 | 0.79 | 0.0013 | 0.17 | 1.77 | 0.568 |
| carrier_battle | b | gunship | 430 | 411.9 | 175.5 | 0.42 | 0.295 | 0.84 | 0.0002 | 0.48 | 2.28 | 0.709 |
| carrier_battle | b | strafer | 516 | 109.9 | 74.0 | 0.02 | 0.200 | 0.73 | 0.0018 | 0.20 | 2.02 | 0.673 |
| carrier_battle | b | all | 1978 | 149.9 | 74.3 | 0.12 | 0.254 | 0.79 | 0.0010 | 0.28 | 1.95 | 0.639 |
| convoy_escort | a | fighter | 731 | 126.2 | 46.8 | 0.32 | 0.412 | 0.93 | 0.0000 | 0.21 | 1.08 | 0.734 |
| convoy_escort | a | gunship | 215 | 449.8 | 127.0 | 0.77 | 0.298 | 0.93 | 0.0000 | 0.38 | 1.27 | 0.842 |
| convoy_escort | a | strafer | 344 | 175.2 | 47.7 | 0.44 | 0.202 | 0.91 | 0.0000 | 0.15 | 1.36 | 0.777 |
| convoy_escort | a | all | 1290 | 193.2 | 60.4 | 0.43 | 0.280 | 0.92 | 0.0000 | 0.24 | 1.19 | 0.771 |
| convoy_escort | b | fighter | 731 | 150.0 | 41.8 | 0.37 | 0.406 | 0.92 | 0.0001 | 0.20 | 1.28 | 0.646 |
| convoy_escort | b | gunship | 215 | 432.5 | 156.5 | 0.87 | 0.305 | 0.93 | 0.0000 | 0.45 | 1.32 | 0.775 |
| convoy_escort | b | strafer | 344 | 164.4 | 49.3 | 0.58 | 0.171 | 0.84 | 0.0000 | 0.20 | 2.09 | 0.632 |
| convoy_escort | b | all | 1290 | 200.9 | 62.9 | 0.51 | 0.267 | 0.90 | 0.0001 | 0.26 | 1.50 | 0.671 |
