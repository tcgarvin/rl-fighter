# The first learned commanders go live, level with the script

Shipped to the live page on 2026-11-08, `SIM_VERSION` 6.

<!-- summary: A commander gives a side's ships their orders. One night of training took a learned commander from winning 0.46 of its matches against our hand-written scripted commander to 0.53–0.56, about level with it. Three of them join the live page beside the script. With today's pilots, who mostly ignore orders, a commander that gives random orders does as well, so the next step is pilots that follow. -->

Until today every side on the live page was commanded by the sim's script, a hand-written
set of rules. A commander sees the whole battle for its side and gives its ships orders. It
also decides when the carrier launches its fighters and where the big ships go (its
logistics). From today each side draws its commander from a stable of four: the script
and three learned commanders, small neural networks trained overnight. How a learned commander sees and
decides is on the [commander page](/commander/).

The question was whether one night of training could make a commander as good as the
script. It could, about: the learned ones went from a little worse than the script to
about level. But a commander giving random orders does as well, because most of today's
pilots ignore orders.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error ([how a pilot works](/pilot/)).
[Fighters v2](../2026-11-01-fighters-v2/results.md) found that scripted pilots under random
orders beat the scripted commander in 0.75 of carrier battles, so a better commander had
room to win, at least with pilots that follow. Meanwhile the live page had ten pilots,
refreshed by two nights of pilot training ([the second night](../2026-11-07-second-night/results.md)),
most of them strong fighters that ignore orders. The owner's plan is a loop: train
commanders, then pilots under those commanders, then commanders again. This is the first
commander turn, with the pilots frozen (not trained) while it runs.

## The night

Three training lines ran from 02:08 to 11:00, about 325 updates (rounds of training: play a
batch of matches, then adjust the network once), 2.7 million decisions and about 43,000
matches each. A commander makes one decision a second for its side. Each match drew its pilots ship by ship
from the live ten, as the live page does, and its enemy commander from the script (35%),
random orders (10%), itself (30%) and its own past selves (25%, saved copies from earlier
in its training).

- **`c1_shaped`**: the design. A small reward when the balance of ships swings its
  way, and the win or loss at the end.
- **`c1_shaped_s1`**: the same with another seed (the random number that sets up a run),
  to show how much two runs differ.
- **`c1_outcome`**: the win or loss only, to ask whether the small rewards help.

## How they did

576 matches each against the scripted commander (192 per mission, each side half the
time, the same pilots for every commander). Each number is the share of matches won
against the scripted commander, so 0.5 is level. Each score is good to about ±0.04 (±
is the margin of error: the true value is very likely within that range). The missions
are deathmatch (last side standing wins), carrier battle (destroy the other side's
carrier) and convoy escort (one side guards cargo ships, the other attacks them).

| Commander | Overall | Deathmatch | Carrier | Convoy |
|---|---|---|---|---|
| `c1_shaped` | 0.56 | 0.49 | 0.56 | 0.62 |
| `c1_outcome` | 0.55 | 0.54 | 0.56 | 0.54 |
| `c1_shaped_s1` | 0.53 | 0.54 | 0.56 | 0.49 |
| Random orders | 0.54 | 0.51 | 0.57 | 0.55 |
| Untrained, last night | 0.46 | 0.43 | 0.44 | 0.50 |

The last row is the commander before training, measured before the night on 96 matches
per mission (about ±0.05).

Against each other they are even, all within noise: `c1_shaped` scores 0.52 against
`c1_shaped_s1` and 0.50 against `c1_outcome`, and `c1_shaped_s1` 0.50 against
`c1_outcome`. The small
rewards made no difference we can see in one night.

**Training moved the learned commander from a little worse than the script to about
level with it.** It flies its own launches and steers its own carrier, which the
random-orders commander leaves to the script, so the night's gain is mostly in that
logistics. Its orders are no better than random ones, and that is what we expected:
most of the live ten ignore orders, so orders barely change a match. They ask to be
followed; the pilots do not yet listen.

## What they do

<div data-figure="diagram" data-name="orders" data-caption="These commanders give attack, defend and go-to orders, or none. Go-to deadlines and the dock order came in later versions of the rules. The picture leaves out the commander's other choices: when to launch from the carrier and where the carrier steers."></div>

A commander groups its strike craft into up to four squads and gives each squad one order:
attack a named enemy, defend a friendly ship, go to a point, or none. Over the last 40
updates the three behave alike. Each second, about half their squads get a new order or have theirs cleared (a squad that just got one is locked for three
seconds, and an empty squad gets none). Of those, about a third clear the order, just
over a quarter attack, a fifth defend and a sixth go to a point. They launch from a bay
on about one decision in twenty.

## Next

<!-- figure-idea: shared: the training loop as a cycle, commanders train with pilots frozen, then pilots train under the new commanders, then commanders again, with this night marked as the first commander turn; several later entries refer to "the loop" -->

The loop is commanders, then pilots, then commanders. Tonight's pilot phase trains under
these commanders with more go-to drills (short practice scenarios in which a pilot is sent
to a point), so following orders pays more. The pilots will be judged by wins above
replacement (how many more matches out of 100 a side wins with that pilot flying instead
of the script) in matches like the live page's, rather than by the order gate (pass marks
on the drills). Once pilots follow, the next commander phase should find that orders
matter.
