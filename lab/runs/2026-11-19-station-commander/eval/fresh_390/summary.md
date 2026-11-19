# fresh_390

| Reading | Role | n | Score | vs none | Best rule | Rule vs none | vs the rule | End: station / repelled / clock |
|---|---|---|---|---|---|---|---|---|
| carrier | defender | 1024 | 0.503 | -0.062 ± 0.040 | `hold_late` | +0.185 ± 0.039 | -0.246 ± 0.039 | 0.50 / 0.38 / 0.12 |
| carrier | attacker | 1024 | 0.431 | -0.005 ± 0.040 | `carrier_push` | +0.130 ± 0.038 | -0.135 ± 0.041 | 0.43 / 0.54 / 0.03 |
| convoy | defender | 512 | 0.510 | -0.064 ± 0.057 | `hold_late` | +0.203 ± 0.053 | -0.268 ± 0.055 | 0.49 / 0.37 / 0.14 |
| convoy | attacker | 512 | 0.461 | +0.035 ± 0.058 | `carrier_push` | +0.145 ± 0.054 | -0.109 ± 0.054 | 0.46 / 0.52 / 0.02 |

## Telemetry (commander side)

| Reading | Role | First launch s (median, IQR) | Station hull then | Hangar empty s | Re-orders / min | Under an order | Carrier to station m at 10/20/30/45/60/90 s | Station hull at 10/20/30/45/60/90 s |
|---|---|---|---|---|---|---|---|---|
| carrier | defender | 2 (2–2) | 1.00 | 4 | 6.2 | 0.12 | 461 / 441 / 431 / 426 / 420 / 352 | 1.00 / 0.98 / 0.87 / 0.70 / 0.59 / 0.52 |
| carrier | attacker | 2 (2–2) | 1.00 | 6 | 15.6 | 0.21 | 457 / 440 / 423 / 390 / 340 / 225 | 1.00 / 1.00 / 0.94 / 0.84 / 0.75 / 0.61 |
| convoy | defender | 2 (2–2) | 1.00 | 4 | 5.6 | 0.11 | 461 / 441 / 429 / 424 / 419 / 352 | 1.00 / 0.98 / 0.88 / 0.71 / 0.60 / 0.55 |
| convoy | attacker | 2 (2–2) | 1.00 | 6 | 16.1 | 0.20 | 456 / 437 / 420 / 383 / 329 / 213 | 1.00 / 0.99 / 0.94 / 0.83 / 0.74 / 0.59 |

Hand rules for comparison (carrier reading): the script (`none`) launches the station's reserve at about 2 s and has emptied it by 4 s; `hold_late` waits for hull < 0.60 (first launch about 30 s, 16-match smoke: median 32 s at hull 0.54). `carrier_push`'s carrier is 396 m out at 20 s, 237 m at 45 s, 163 m at 90 s; the patrol's 420 to 460 m.

**Verdict: FAIL** (defender: below the rule, does not beat no orders, attacker: below the rule, does not beat no orders)
