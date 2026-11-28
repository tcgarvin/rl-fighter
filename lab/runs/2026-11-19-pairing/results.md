# One commander and one pilot a side

Verdict: **a fixed commander and pilot are not worth more than the sum of their parts,
except in one way we already knew about.**

On the live page every ship's pilot is drawn at random from ten trained pilots, and each
side has a commander that gives its ships orders. We asked whether a side does better
when one commander and one pilot run the whole of it, every ship flown by the same
pilot, in case some commanders and pilots suit each other. Mostly they do not. The one
pairing effect we found is one we already knew: orders hurt the pilots that follow them
and not the pilot that ignores them. A side flown by one pilot does about as well as a
side of mixed pilots, and the best side of all was a pilot given no orders. No rule of
the game changed (`SIM_VERSION` 8, the eighth version of the game's rules).

<!-- summary: We tried giving each side one commander and one pilot, with every ship on the side flown by the same network, to see whether some pairs are worth more together than apart. They are not, beyond what we already knew: orders cost a side up to 0.28 in win rate with three of the four pilots, and nothing with the one that ignores orders. With no orders on either side, a whole side of the best-rated pilot won only 0.38 against a side of the lowest-rated one, the opposite of what its rating predicts, so a rating made in mixed sides under orders does not carry over. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network
(a pilot) that learned to fly by trial and error. A second network or a hand-written
script, the commander, sees the whole side and gives its ships orders. Since
[2026-11-02](../2026-11-02-ten-pilots/results.md) the live page has drawn each ship's
pilot from ten, and since [2026-11-08](../2026-11-08-commander-1/results.md) learned
commanders have flown there beside the script. Two findings set up this night.
[Commander 3](../2026-11-15-commander-3/results.md) found that a side whose pilots get
no orders beats every commander we had, and [the order-cost
night](../2026-11-17-order-cost/results.md) found why: an ordered pilot charges its one
target and loses the duel. On 2026-11-18 the owner asked for [new
directions](../2026-11-19-new-directions/results.md), one of them a consistent commander
and pilot for each side. If some pair were worth more than its parts, the live page and
commander training should be built around pairs. This entry measures whether any is.

## How we measured it

The owner asked to try each side being a consistent commander and pilot pairing,
instead of every ship drawing its pilot at random (the live page and the commander eval,
our batch of matches played only to measure, both draw ship by ship). Both got the
option: `?pairing=side` on the page, `--pilot-draw side` and `--pilot-a` / `--pilot-b`
in `spacefight.commander.eval`, and `pilot_draw` in commander training
(`docs/COMMANDER.md`). These options (`?pairing=side`, `--pilot-draw`, `--pilot-a` /
`--pilot-b`, `pilot_draw`) were removed from the code on 2026-11-19 after this result,
so `run.sh` and `grid.py` need the code at commit `229877d` to rerun.

<!-- figure-idea: the grid as a picture: side a built from a commander (row) and one pilot flying all its ships (column), always facing the same side b of the scripted commander and randomly drawn pilots; helps the reader see what a "cell" is before the tables. -->

**The grid.** Side a is a commander (row) with one pilot (column) flying all its strike
craft, the small piloted ships, or with its pilots drawn ship by ship (last column, "per-ship
draw"). Side b is the same in every cell: the scripted commander with each strike
craft's pilot drawn ship by ship from the live ten (the ten pilots the live page draws
from), the live page's side as it is today. A fixed opponent makes the cells comparable.
Every cell plays the same 96 matches in each of three missions, with side a on each team
half the time: team deathmatch (small ships only, last side standing, with rosters drawn
as on the live page), carrier battle (each side's carrier launches its craft, and a side
wins by destroying the enemy carrier) and convoy escort (one side guards freighters
flying to a jump point, the other attacks them). The rosters and side-b pilots are the
same match by match, so cells pair: two cells can be compared match by match.
288 matches a cell, 6,336 in the grid and pairs. The ± is the margin of error: the true
value very likely lies within that range (1.96 standard errors). We get it from a
bootstrap, which re-draws the set of matches at random many times, the same draw in every
cell, and sees how much each number moves.

- Commanders: `scripted` (the hand-written commander), `unseen` (the scripted commander
  with its orders hidden from its own pilots: no orders), and `c1_shaped` and
  `c1_outcome` from the live stable (the commanders the live page draws from), two learned commanders from [the first commander
  night](../2026-11-08-commander-1/results.md) (`c1_shaped` was paid a little whenever
  the balance of ships swung its way, `c1_outcome` only for the win or loss).
  `c1_shaped_s1` (a second seed of `c1_shaped`, the same training started from another
  random number) was left out for time.
- Pilots: four of the live ten. A pilot's name is its training line followed by the
  training update it was saved at, and `_v8_` marks a pilot widened to read go-to
  deadlines. The two best rated mostly ignore orders. `f995_701`, a strong fighter from
  [the Fighters v2 night](../2026-11-01-fighters-v2/results.md) named for its discount
  of 0.995 (how far ahead it plans) and founder of the fighters family, follows 11 to 22%
  of drills (short practice scenarios with an order to follow). `fighters_pay1_v8_351`,
  of the fighters branch paid less for following orders, follows 26 to 33%. Two come
  from the followers family, bred to fight and follow orders, and do follow them:
  `followers_school_600`, which went through go-to school (drill-heavy training on go-to
  orders), 70 to 89%, and `followers_v8_352` 51 to 76%.

## The answer in numbers

All results here are a side's win rate: the share of matches it won, out of 1, a draw
counting half. A cost of 0.28 means the side's win rate fell by 0.28. Orders cost a side
0.05 to 0.28 in win rate (the scripted commander's orders 0.21 to 0.28) with three of
the four pilots we tried, and nothing with `f995_701`, the pilot that ignores them most.
That is nearly all the pairing effect we measured (the "interaction": how much better or
worse a pair does than its commander and its pilot separately predict). Among the
commanders that give orders, what is left is ±0.05 at most, close to the noise (p ≈ 0.03
over the grid: a pattern that large turns up by chance about 3 times in 100, and no
single pairing is clear of the noise). A side flown by one pilot scores about what a
side whose pilots are drawn ship by ship does. The best side here is a pilot with no
orders at all.

## The grid

Each cell is side a's score against side b: the share of matches it won, a draw counting
half, so 0.5 is even. In brackets is the **interaction**, the cell minus its row mean
minus its column mean plus the grand mean: how much better or worse that pairing does
than its commander's average and its pilot's average predict. It is zero when a pairing
is worth exactly its commander's part plus its pilot's.

| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Row mean | Per-ship draw |
|---|---|---|---|---|---|---|
| `scripted` | 0.562 (+0.087) | 0.462 (−0.043) | 0.392 (−0.034) | 0.469 (−0.010) | 0.471 | 0.427 |
| `unseen` | 0.526 (**−0.124**) | 0.738 (+0.059) | 0.601 (−0.000) | 0.719 (+0.065) | 0.646 | 0.705 |
| `c1_shaped` | 0.585 (+0.048) | 0.562 (−0.004) | 0.474 (−0.014) | 0.510 (−0.030) | 0.533 | 0.472 |
| `c1_outcome` | 0.540 (−0.012) | 0.569 (−0.012) | 0.552 (+0.049) | 0.531 (−0.025) | 0.548 | 0.566 |
| Column mean | 0.553 | 0.583 | 0.505 | 0.557 | 0.550 | |

A cell is ± 0.05 to 0.06, an interaction ± 0.04, a row or column mean ± 0.035.

- **The interaction is real, and it is one thing.** Over the grid its typical size (rms)
  is 0.050, against 0.019 from noise alone. A standard test (Wald chi-squared 56 on 9
  degrees of freedom) puts the chance of that from noise below 1 in 1,000 (p < 0.001).
  Its biggest term is `unseen` with `f995_701`: hiding the orders helps every other pilot
  and not that one.
- **Without the `unseen` row it nearly vanishes.** Among the three commanders that give
  orders the interaction is 0.029 rms against 0.018 from noise (chi-squared 14 on 6
  degrees of freedom, p ≈ 0.03). The largest terms, `c1_outcome` with `f995_701`
  (−0.053) and with `followers_school_600` (+0.049), and `scripted` with `f995_701`
  (+0.046), are each just past their ± 0.037. With twelve cells, one or two would land
  just past their margin by chance alone. No commander has a pilot it is clearly better with.

What a commander's orders are worth, pilot by pilot: its cell minus the `unseen` cell
with the same pilot, paired match by match. A negative number means the orders cost the
side that much in win rate.

| Orders over none | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` |
|---|---|---|---|---|
| `scripted` | +0.036 ± 0.076 | −0.276 ± 0.071 | −0.208 ± 0.072 | −0.250 ± 0.069 |
| `c1_shaped` | +0.059 ± 0.073 | −0.175 ± 0.073 | −0.127 ± 0.071 | −0.208 ± 0.072 |
| `c1_outcome` | +0.014 ± 0.072 | −0.168 ± 0.071 | −0.049 ± 0.077 | −0.188 ± 0.071 |

<div data-figure="diagram" data-name="charge-and-duel" data-caption="The numbers are from the order-cost night's 3 v 3 fleet fights. In this entry's missions three of the four pilots pay the cost. f995_701, which ignores orders, pays nothing."></div>

The cost of orders is the one in [the order-cost entry](../2026-11-17-order-cost/results.md):
an ordered pilot charges and duels its one target. A pilot that follows orders at all
pays it, and `fighters_pay1_v8_351`, which follows only a third of its drills, pays as
much as the followers. `f995_701` pays nothing. The learned commanders cost less than the
script, but none of them gains anything over no orders with any pilot.

By mission: each number is a commander's score averaged over the four pilots.

| Mission | `scripted` | `unseen` | `c1_shaped` | `c1_outcome` |
|---|---|---|---|---|
| Deathmatch | 0.461 | 0.578 | 0.531 | 0.538 |
| Carrier battle | 0.435 | 0.724 | 0.529 | 0.570 |
| Convoy escort | 0.518 | 0.635 | 0.539 | 0.536 |

## One pilot a side against the per-ship draw

The first column is side a's score when its pilots are drawn ship by ship, the second
that score minus the average of the same row's four one-pilot cells.

| Commander | Per-ship draw | Minus the row mean of one pilot a side |
|---|---|---|
| `scripted` | 0.427 ± 0.058 | −0.044 ± 0.064 |
| `unseen` | 0.705 ± 0.052 | +0.059 ± 0.056 |
| `c1_shaped` | 0.472 ± 0.058 | −0.061 ± 0.061 |
| `c1_outcome` | 0.566 ± 0.056 | +0.018 ± 0.060 |

None is clear of its error, and they do not agree in sign. A side of one pilot is worth
about what a mixed side is. The per-ship draw here is from all ten pilots and the row
mean is over four, so the two are not the same pilots. WAR (wins above replacement, our
rating of how many more matches in 100 a side wins with a pilot flying instead of the
script) puts the four's average 0.02 above the ten's, inside these errors.

`scripted` with the per-ship draw is side b's own setup, so it should score 0.50. It
scored 0.427 (deathmatch 0.42, carrier 0.47, convoy 0.40), 2.5 standard errors low. The
pilots it drew were as strong as side b's by WAR (a mean logit difference of 0.00 a
match, logit being the scale WAR's fit works in), so it is either chance or something in
these particular matches favours side b. Every cell plays the same matches against the
same side b, so either way it moves every cell alike and does not touch the interaction
or any paired difference above. It does mean the absolute level of a cell is relative to
this sample of side b.

## What the season's WAR predicts

WAR (`lab/population/2026-11-sim6/war/goto-school-2/war.json`) is a statistical fit (a
logistic model) made on mixed sides under commanders: each pilot gets a number per ship
it flies (its coefficient), each commander a number per mission, and they add up to
predict who wins. Its prediction for the same matches (no prediction for `unseen`, which
it never saw):

| Commander \ pilot | `f995_701` | `fighters_pay1_v8_351` | `followers_school_600` | `followers_v8_352` | Per-ship draw |
|---|---|---|---|---|---|
| `scripted` | 0.587 | 0.539 | 0.510 | 0.439 | 0.499 |
| `c1_shaped` | 0.635 | 0.590 | 0.561 | 0.491 | 0.551 |
| `c1_outcome` | 0.639 | 0.594 | 0.566 | 0.495 | 0.555 |

WAR predicts a side's chances by adding a pilot's part to a commander's part, so it has
no term for a pair that works better together. Its own interactions, worked out as in
the grid above, are all within ±0.002 (adding on WAR's logit scale comes out nearly
additive in win rate at these levels). So any interaction measured above is something
WAR cannot express. Under the script, WAR gets the order of the pilots roughly right
(`f995_701` first, observed 0.562 against 0.39 to 0.47 for the others) and the size of
the commanders wrong: it has both learned commanders 0.05 above the script with every
pilot, observed −0.02 to +0.16.

**With no commander on either side, WAR's order turns over.** One pilot a side, both
sides `unseen`, 288 matches each. The table gives side a's score, WAR's prediction, and
side a's score in each mission:

| Side a v side b | a's score | WAR predicts | Deathmatch | Carrier | Convoy |
|---|---|---|---|---|---|
| `f995_701` v `followers_v8_352` | **0.382 ± 0.051** | 0.643 | 0.271 | 0.677 | 0.198 |
| `followers_school_600` v `followers_v8_352` | 0.451 ± 0.058 | 0.571 | 0.479 | 0.479 | 0.396 |

The best-rated pilot, flying a whole side with no orders on either side, loses to the
lowest rated of the live ten, and badly in deathmatch and convoy. It wins the carrier battle,
as WAR says. Its rating comes from matches in which commanders gave orders: against
ordered pilots, which charge and duel their targets, a pilot that ignores orders does
well, and the grid shows it (+0.04 over no orders when it flies under the script, where
the others lose 0.2 to 0.3). Against free pilots it does not. This pair cannot tell which hurts it: facing free
pilots, or flying a whole side alone. The grid does not settle it either, because a
whole side of `f995_701` with no orders (`unseen`) already scored lowest in its row,
0.526, against side b's mixed pilots under the scripted commander, who were not free.

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
  (This option was removed later the same day, at the owner's call: see "How we
  measured it".)
- **A rating is only good for the setting it was made in.** WAR's per-ship coefficients
  come from mixed sides under orders; with no orders and a whole side of one pilot, its
  top pilot won only 0.38 against the pilot it ranks last of the live ten. Rating pilots by their whole
  side, and with no orders as well as orders, would show it.
- **Not tested:** the six other live pilots, `c1_shaped_s1`, a side of one pilot against a
  side of one pilot under commanders, and training a commander with `pilot_draw=side`
  (the critic, the network that judges a commander's choices during training, sees each
  ship's pilot either way).

## Method and timing

This section is the record of how the numbers were made, and a reader can skip it.

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
