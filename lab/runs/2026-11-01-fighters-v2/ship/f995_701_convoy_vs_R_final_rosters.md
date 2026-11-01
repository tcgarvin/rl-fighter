**policy:ppo_bc_701.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.568

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| convoy_escort | 1032 | 0.568 | 0.219 | 0.917 | 0.000 | 0.000 | 0.000 | 45 | 65 | eliminated 0.12, convoy_through 0.03, convoy_destroyed 0.85 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| convoy_escort | a | fighter | 2580 | 158.5 | 93.3 | 0.19 | 0.531 | 0.92 | 0.0011 | 0.19 | 1.08 | 0.926 |
| convoy_escort | a | gunship | 1032 | 610.5 | 187.6 | 0.83 | 0.300 | 0.88 | 0.0001 | 0.50 | 1.34 | 0.914 |
| convoy_escort | a | strafer | 1548 | 254.6 | 42.8 | 0.36 | 0.212 | 0.90 | 0.0007 | 0.18 | 1.56 | 0.877 |
| convoy_escort | a | all | 5160 | 277.7 | 97.0 | 0.37 | 0.295 | 0.90 | 0.0007 | 0.28 | 1.27 | 0.909 |
| convoy_escort | b | fighter | 2580 | 162.5 | 79.8 | 0.18 | 0.468 | 0.93 | 0.0009 | 0.24 | 1.20 | 0.773 |
| convoy_escort | b | gunship | 1032 | 427.7 | 103.0 | 0.61 | 0.253 | 0.88 | 0.0009 | 0.38 | 1.40 | 0.831 |
| convoy_escort | b | strafer | 1548 | 281.8 | 116.8 | 0.37 | 0.261 | 0.90 | 0.0002 | 0.14 | 1.74 | 0.796 |
| convoy_escort | b | all | 5160 | 251.3 | 95.6 | 0.33 | 0.294 | 0.91 | 0.0007 | 0.25 | 1.40 | 0.795 |
