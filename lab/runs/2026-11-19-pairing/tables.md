| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Row mean | Per-ship draw |
|---|---|---|---|---|---|---|
| `scripted` | 0.562 (+0.087) | 0.462 (−0.043) | 0.392 (−0.034) | 0.469 (−0.010) | 0.471 | 0.427 |
| `unseen` | 0.526 (−0.124) | 0.738 (+0.059) | 0.601 (−0.000) | 0.719 (+0.065) | 0.646 | 0.705 |
| `c1_shaped` | 0.585 (+0.048) | 0.562 (−0.004) | 0.474 (−0.014) | 0.510 (−0.030) | 0.533 | 0.472 |
| `c1_outcome` | 0.540 (−0.012) | 0.569 (−0.012) | 0.552 (+0.049) | 0.531 (−0.025) | 0.548 | 0.566 |
| Column mean | 0.553 | 0.583 | 0.505 | 0.557 | 0.550 | |

Cell ± (1.96 SE): 0.050 to 0.059. Interaction ± (1.96 SE): 0.037 to 0.041. Row mean ±: 0.033; column mean ±: 0.035.

Interaction over the grid: rms 0.050 against 0.019 from noise alone; Wald chi-squared 56.4 on 9 df, p ≈ 0.00; spread beyond noise ≈ 0.046.

Without `unseen` (scripted, c1_shaped, c1_outcome): interaction rms 0.029 against 0.018 from noise; Wald chi-squared 14.0 on 6 df, p ≈ 0.03. Interactions: scripted +0.046, −0.023, −0.034, +0.011; c1_shaped +0.007, +0.016, −0.014, −0.009; c1_outcome −0.053, +0.008, +0.049, −0.003.

| Commander | Per-ship draw | Minus its row mean (one pilot a side) |
|---|---|---|
| `scripted` | 0.427 ± 0.058 | −0.044 ± 0.064 |
| `unseen` | 0.705 ± 0.052 | +0.059 ± 0.056 |
| `c1_shaped` | 0.472 ± 0.058 | −0.061 ± 0.061 |
| `c1_outcome` | 0.566 ± 0.056 | +0.018 ± 0.060 |

| Orders over none (cell minus `unseen`) | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` |
|---|---|---|---|---|
| `scripted` | +0.036 ± 0.076 | −0.276 ± 0.071 | −0.208 ± 0.072 | −0.250 ± 0.069 |
| `c1_shaped` | +0.059 ± 0.073 | −0.175 ± 0.073 | −0.127 ± 0.071 | −0.208 ± 0.072 |
| `c1_outcome` | +0.014 ± 0.072 | −0.168 ± 0.071 | −0.049 ± 0.077 | −0.188 ± 0.071 |

| Mission | `scripted` | `unseen` | `c1_shaped` | `c1_outcome` |
|---|---|---|---|---|
| deathmatch | 0.461 | 0.578 | 0.531 | 0.538 |
| carrier_battle | 0.435 | 0.724 | 0.529 | 0.570 |
| convoy_escort | 0.518 | 0.635 | 0.539 | 0.536 |

WAR's prediction (lab/population/2026-11-sim6/war/goto-school-2/war.json), same matches:

| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Per-ship draw |
|---|---|---|---|---|---|
| `scripted` | 0.587 (+0.002) | 0.539 (−0.000) | 0.510 (−0.001) | 0.439 (−0.001) | 0.499 |
| `c1_shaped` | 0.635 (−0.001) | 0.590 (+0.000) | 0.561 (+0.000) | 0.491 (+0.000) | 0.551 |
| `c1_outcome` | 0.639 (−0.001) | 0.594 (+0.000) | 0.566 (+0.000) | 0.495 (+0.000) | 0.555 |

| Pilot pair (no commander), a v b | a's score | WAR predicts |
|---|---|---|
| `f995_701` v `followers_v8_352` | 0.382 ± 0.051 | 0.643 |
| `followers_school_600` v `followers_v8_352` | 0.451 ± 0.058 | 0.571 |

