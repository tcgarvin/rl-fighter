# One commander and one pilot a side

Verdict: **a fixed commander and pilot are not worth more than the sum of their parts,
except in one way we already knew about.** Orders cost a side 0.05 to 0.28 (the script's 0.21 to
0.28) with three of the four pilots and nothing with `f995_701`, the pilot that ignores them most. That is
nearly all the commander x pilot interaction in the grid. Among the commanders that give
orders, what is left is ±0.05 at most, close to the noise (p ≈ 0.03 over the grid, no
single cell clear of it). A side with one pilot scores about what the per-ship draw
does. The best side here is a pilot with no orders at all. No rule of the game changed
(`SIM_VERSION` 8).

The side-pairing options (`?pairing=side`, `--pilot-draw`, `--pilot-a` / `--pilot-b`,
`pilot_draw`) were removed from the code on 2026-11-19 after this result; `run.sh` and
`grid.py` need the code at commit `229877d` to rerun.

<!-- summary: We tried each side being one commander and one pilot, every ship on it flown by the same network, to see whether some pairs are worth more together than apart. They are not, beyond what we knew: orders cost a side up to 0.28 with three of four pilots and nothing with the one that ignores them. With no orders on either side, a whole side of the best-rated pilot lost 0.38 to a side of the lowest-rated follower, the opposite of what its rating predicts, so a rating made in mixed sides under orders does not carry over. -->

The owner asked to try each side being a consistent commander and pilot pairing,
instead of every ship drawing its pilot at random (the live page and the commander eval
both draw ship by ship). Both now have the option: `?pairing=side` on the page,
`--pilot-draw side` and `--pilot-a` / `--pilot-b` in `spacefight.commander.eval`, and
`pilot_draw` in commander training (`docs/COMMANDER.md`). This entry measures whether it
matters.

**The grid.** Side a is a commander (row) with one pilot flying all its strike craft
(column), or with the per-ship draw (last column). Side b is the same in every cell: the
scripted commander with each strike craft's pilot drawn ship by ship from the live ten,
the live page's side as it is today. A fixed opponent makes the cells comparable. Every
cell plays the same 96 matches a mission (deathmatch drafts, carrier battle, convoy
escort; a on each side half the time), with the same rosters and the same side-b pilots
match by match, so cells pair. 288 matches a cell, 6,336 in the grid and pairs. The ±
is 1.96 standard errors from a bootstrap over matches that resamples the same matches
in every cell.

- Commanders: `scripted`, `unseen` (the scripted commander with its orders hidden from
  its own pilots: no orders), `c1_shaped` and `c1_outcome` from the live stable.
  `c1_shaped_s1` (a second seed of `c1_shaped`) was left out for time.
- Pilots: four of the live ten. The two best rated, which mostly ignore orders
  (`f995_701` follows 11 to 22% of drills, `fighters_pay1_v8_351` 26 to 33%), and two
  that follow them (`followers_school_600` 70 to 89%, `followers_v8_352` 51 to 76%).

## The grid

Side a's score; in brackets the **interaction**, the cell minus its row mean minus its
column mean plus the grand mean. It is zero when a pairing is worth exactly its
commander's part plus its pilot's.

| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Row mean | Per-ship draw |
|---|---|---|---|---|---|---|
| `scripted` | 0.562 (+0.087) | 0.462 (−0.043) | 0.392 (−0.034) | 0.469 (−0.010) | 0.471 | 0.427 |
| `unseen` | 0.526 (**−0.124**) | 0.738 (+0.059) | 0.601 (−0.000) | 0.719 (+0.065) | 0.646 | 0.705 |
| `c1_shaped` | 0.585 (+0.048) | 0.562 (−0.004) | 0.474 (−0.014) | 0.510 (−0.030) | 0.533 | 0.472 |
| `c1_outcome` | 0.540 (−0.012) | 0.569 (−0.012) | 0.552 (+0.049) | 0.531 (−0.025) | 0.548 | 0.566 |
| Column mean | 0.553 | 0.583 | 0.505 | 0.557 | 0.550 | |

A cell is ± 0.05 to 0.06, an interaction ± 0.04, a row or column mean ± 0.035.

- **The interaction is real, and it is one thing.** Over the grid it is 0.050 rms against
  0.019 from noise (Wald chi-squared 56 on 9 df, p < 0.001). Its biggest term is `unseen`
  with `f995_701`: hiding the orders helps every other pilot and not that one.
- **Without the `unseen` row it nearly vanishes.** Among the three commanders that give
  orders the interaction is 0.029 rms against 0.018 from noise (chi-squared 14 on 6 df,
  p ≈ 0.03). The largest terms, `c1_outcome` with `f995_701` (−0.053) and with
  `followers_school_600` (+0.049), and `scripted` with `f995_701` (+0.046), are each just
  past their ± 0.037. Twelve cells give that once or twice by chance. No commander has a
  pilot it is clearly better with.

What a commander's orders are worth, pilot by pilot (its cell minus the `unseen` cell,
paired):

| Orders over none | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` |
|---|---|---|---|---|
| `scripted` | +0.036 ± 0.076 | −0.276 ± 0.071 | −0.208 ± 0.072 | −0.250 ± 0.069 |
| `c1_shaped` | +0.059 ± 0.073 | −0.175 ± 0.073 | −0.127 ± 0.071 | −0.208 ± 0.072 |
| `c1_outcome` | +0.014 ± 0.072 | −0.168 ± 0.071 | −0.049 ± 0.077 | −0.188 ± 0.071 |

The cost of orders is the one in [the order-cost entry](../2026-11-17-order-cost/results.md):
an ordered pilot charges and duels its one target. A pilot that follows orders at all
pays it, and `fighters_pay1_v8_351`, which follows only a third of its drills, pays as
much as the followers. `f995_701` pays nothing. The learned commanders cost less than the
script, but none of them gains anything over no orders with any pilot.

By mission (row means over the four pilots):

| Mission | `scripted` | `unseen` | `c1_shaped` | `c1_outcome` |
|---|---|---|---|---|
| Deathmatch | 0.461 | 0.578 | 0.531 | 0.538 |
| Carrier battle | 0.435 | 0.724 | 0.529 | 0.570 |
| Convoy escort | 0.518 | 0.635 | 0.539 | 0.536 |

## One pilot a side against the per-ship draw

| Commander | Per-ship draw | Minus the row mean of one pilot a side |
|---|---|---|
| `scripted` | 0.427 ± 0.058 | −0.044 ± 0.064 |
| `unseen` | 0.705 ± 0.052 | +0.059 ± 0.056 |
| `c1_shaped` | 0.472 ± 0.058 | −0.061 ± 0.061 |
| `c1_outcome` | 0.566 ± 0.056 | +0.018 ± 0.060 |

None is clear of its error, and they do not agree in sign. A side of one pilot is worth
about what a mixed side is. The per-ship draw here is from all ten pilots and the row
mean is over four, so the two are not the same pilots; WAR puts the four's average 0.02
above the ten's, inside these errors.

`scripted` with the per-ship draw is side b's own setup, so it should score 0.50. It
scored 0.427 (deathmatch 0.42, carrier 0.47, convoy 0.40), 2.5 standard errors low. The
pilots it drew were as strong as side b's by WAR (a mean logit difference of 0.00 a
match), so it is either chance or something in these particular matches favours side b.
Every cell plays the same matches against the same side b, so either way it moves every
cell alike and does not touch the interaction or any paired difference above. It does
mean the absolute level of a cell is relative to this sample of side b.

## What the season's WAR predicts

WAR (`lab/population/2026-11-sim6/war/goto-school-2/war.json`) is a logistic model
fitted on mixed sides under commanders: a pilot's per-ship coefficient plus each
commander's term per mission. Its prediction for the same matches (no prediction for
`unseen`, which it never saw):

| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Per-ship draw |
|---|---|---|---|---|---|
| `scripted` | 0.587 | 0.539 | 0.510 | 0.439 | 0.499 |
| `c1_shaped` | 0.635 | 0.590 | 0.561 | 0.491 | 0.551 |
| `c1_outcome` | 0.639 | 0.594 | 0.566 | 0.495 | 0.555 |

Its own interactions are all within ±0.002: an additive model in logits is nearly
additive in score at these levels, so any interaction measured above is something WAR
cannot express. Under the script, WAR gets the order of the pilots roughly right
(`f995_701` first, observed 0.562 against 0.39 to 0.47 for the others) and the size of
the commanders wrong: it has both learned commanders 0.05 above the script with every
pilot, observed −0.02 to +0.16.

**With no commander on either side, WAR's order turns over.** One pilot a side, both
sides `unseen`, 288 matches each:

| Side a v side b | a's score | WAR predicts | Deathmatch | Carrier | Convoy |
|---|---|---|---|---|---|
| `f995_701` v `followers_v8_352` | **0.382 ± 0.051** | 0.643 | 0.271 | 0.677 | 0.198 |
| `followers_school_600` v `followers_v8_352` | 0.451 ± 0.058 | 0.571 | 0.479 | 0.479 | 0.396 |

The best-rated pilot, flying a whole side with no orders on either side, loses to the
lowest rated of the live ten, and badly in deathmatch and convoy. It wins the carrier battle,
as WAR says. Its rating comes from matches in which commanders gave orders: against
ordered pilots, which charge and duel their targets, a pilot that ignores orders does
well, and the grid shows it (+0.04 over no orders when it flies under the script, where
the others lose 0.2 to 0.3). Against free pilots it does not. This pair cannot tell
whether it is the free opponent or the side of one pilot that hurts it, since the cell
with `f995_701` on side a under `unseen` against the mixed scripted side b scored 0.526,
already the lowest in its row.

## What we learned

- **A consistent pairing is not worth more than its parts.** Between the commanders and
  pilots we have, the only pairing effect is that orders hurt pilots that follow them and
  not the one that ignores them. A commander does not have a pilot it works with.
- **No commander earns its orders with any pilot.** Against the same side b, every
  ordered row loses to `unseen` with three pilots of four, and only draws with
  `f995_701`. Orders have to become cheap for the pilots before a pairing can be about
  anything else (the order-cost entry's "Next").
- **One pilot a side flies about as well as a mixed side.** Nothing is lost on the page by
  `?pairing=side`; whether to make it the default is a question of what viewers like to
  watch, not of strength. `DEFAULT_PAIRING` in `web/src/live/match.ts` switches it.
- **A rating is only good for the setting it was made in.** WAR's per-ship coefficients
  come from mixed sides under orders; with no orders and a whole side of one pilot, its
  top pilot lost 0.38 to the pilot it ranks last of the live ten. Rating pilots by their whole
  side, and with no orders as well as orders, would show it.
- **Not tested:** the six other live pilots, `c1_shaped_s1`, a side of one pilot against a
  side of one pilot under commanders, and training a commander with `pilot_draw=side`
  (the critic sees each ship's pilot either way).

## Method and timing

`run.sh` runs the cells with `grid.py` (one cell, one mission: `play_matches` from the
commander eval, a pinned pilot for side a, the per-ship draw for side b, every match kept
in the cell JSON) and `analyze.py` writes `analysis.json` and `tables.md` (2,000
bootstrap resamples; the interaction test is a Wald statistic with the bootstrap
covariance, on (rows − 1) x (columns − 1) df). The `f995_701` column ran at 144 matches
a mission before the rest was cut to 96 for time; the analysis uses its first 96, which
are the same rosters, sides and side-b pilots as everyone else's.

The laptop was shared with two other evals all evening (load 20 to 30 on 16 cores). The
grid and pairs took 96 minutes of cell time and two hours of wall clock, at 4 threads
after 8 threads thrashed (a carrier cell at 8 threads did not finish in 15 minutes; at 4
it took 2 to 4). A carrier battle cell is about half the cost; uncontended, at 8 threads,
a cell of 96 matches a mission takes about 3 minutes.

## Files

- `run.sh`: the grid (`cells/<mission>/grid__<commander>__<pilot|mixed>.json`) and the
  pilot pairs (`cells/<mission>/pair__<a>__<b>.json`); re-running skips finished cells.
  `run.out` is its log.
- `grid.py`: one cell (JSON `rlf.pairing.cell/1`: per match a's score, team, roster, the
  ships each pilot flew per side, end reason).
- `analyze.py`: the tables (`tables.md`) and `analysis.json` (`rlf.pairing.analysis/1`).
