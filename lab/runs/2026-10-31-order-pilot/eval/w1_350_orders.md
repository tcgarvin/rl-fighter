**policy:ppo_bc_350.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 182 (0.64 of 486) | 0.398 | 222.3 | 0.201 | 0.100 | 41 (0.77 of 2537) | 956/952/1002 |
| scripted | 158 (0.78 of 814) | 0.490 | 250.7 | 0.240 | 0.015 | 25 (0.88 of 2235) | 1784/617/279 |
| carrier_battle/random | 200 (0.64 of 285) | 0.486 | 276.5 | 0.159 | 0.097 | 41 (0.76 of 1610) | 625/578/603 |
| convoy_escort/random | 159 (0.64 of 201) | 0.233 | 126.2 | 0.264 | 0.105 | 40 (0.79 of 927) | 331/374/399 |
| carrier_battle/scripted | 376 (0.75 of 440) | 0.632 | 302.8 | 0.207 | 0.000 | 32 (0.88 of 1106) | 995/409/0 |
| convoy_escort/scripted | 61 (0.83 of 374) | 0.236 | 137.9 | 0.355 | 0.015 | 18 (0.87 of 1129) | 789/208/279 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.23 | 0.20 | 0.23 |
| random | gunship | 0.48 | 0.50 | 0.47 | 0.48 |
| random | strafer | 0.25 | 0.20 | 0.24 | 0.21 |
| scripted | fighter | 0.18 | 0.26 | 0.24 | 0.22 |
| scripted | gunship | 0.41 | 0.49 | 0.47 | 0.47 |
| scripted | strafer | 0.16 | 0.21 | 0.23 | 0.19 |
