mode **script** (script), n = 128 per roster

### carrier_battle (time limit 150 s)

| roster | team 0 win | team 1 win | time limit | median s | p90 s | end reasons | launches | launch median s | launch p90 s | launches per 30 s | carrier travel m | strike left | hangar left | carrier hp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| wing of 8 | 0.41 | 0.59 | 0.23 | 138 | 150 | time_limit 0.23, carrier_destroyed 0.77 | 12.0 | 16 | 44 | 8.4 3.3 0.3 0.0 0.0 | 353 | 0.3 / 0.8 | 0.0 / 0.0 | 0.33 / 0.47 |
| wing of 6 | 0.55 | 0.45 | 0.16 | 136 | 150 | time_limit 0.16, carrier_destroyed 0.84 | 8.0 | 16 | 32 | 6.8 1.2 0.0 0.0 0.0 | 358 | 0.2 / 0.1 | 0.0 / 0.0 | 0.32 / 0.19 |
| wing of 9 | 0.39 | 0.61 | 0.15 | 135 | 150 | time_limit 0.15, carrier_destroyed 0.85 | 14.0 | 14 | 34 | 12.0 1.8 0.2 0.0 0.0 | 343 | 0.5 / 0.7 | 0.0 / 0.0 | 0.34 / 0.47 |
| all | 0.45 | 0.55 | 0.18 | 136 | 150 | time_limit 0.18, carrier_destroyed 0.82 | 11.3 | 16 | 40 | 9.1 2.1 0.2 0.0 0.0 | 352 | 0.3 / 0.6 | 0.0 / 0.0 | 0.33 / 0.38 |

### convoy_escort (time limit 120 s)

| roster | defenders win | attackers win | time limit | median s | p90 s | end reasons | escaped | destroyed | progress | wins w/ escape | strike left |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 freighters | 0.00 | 1.00 | 0.00 | 50 | 64 | convoy_destroyed 1.00 | 0.08 | 2.01 | 0.72 | 0.00 | 0.1 / 3.9 |
| 3 freighters | 0.98 | 0.02 | 0.00 | 68 | 68 | eliminated 0.19, convoy_through 0.79, convoy_destroyed 0.02 | 1.65 | 0.15 | 0.96 | 0.86 | 1.5 / 1.1 |
| 5 freighters | 0.73 | 0.27 | 0.00 | 75 | 77 | convoy_through 0.73, convoy_destroyed 0.27 | 2.36 | 1.55 | 0.96 | 1.00 | 0.7 / 2.1 |
| all | 0.57 | 0.43 | 0.00 | 68 | 75 | eliminated 0.06, convoy_through 0.51, convoy_destroyed 0.43 | 1.36 | 1.23 | 0.88 | 0.92 | 0.8 / 2.4 |

(207 s)
