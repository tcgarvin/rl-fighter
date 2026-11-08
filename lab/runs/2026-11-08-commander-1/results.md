# The first learned commanders go live, level with the script

Shipped to the live page on 2026-11-08, `SIM_VERSION` 6.

<!-- summary: One night of training took a learned commander from 0.46 against the scripted commander to 0.53–0.56, about level with it. Three of them join the live page beside the script. With today's pilots, who mostly ignore orders, a commander that gives random orders does as well, so the next step is pilots that follow. -->

Until today every side on the live page was commanded by the sim's script. From today
each side draws its commander from a stable of four: the script and three learned
commanders, trained overnight. How a learned commander sees and decides is on the
[commander page](/commander/).

## The night

Three training lines ran from 02:08 to 11:00, about 325 updates and 2.7 million
decisions each (one a second per side, so about 43,000 matches each). Each match drew
its pilots ship by ship from the live ten, as the live page does, and its enemy
commander from the script (35%), random orders (10%), itself (30%) and its own past
selves (25%).

- **`c1_shaped`**: the design. A small reward when the balance of ships swings its
  way, and the win or loss at the end.
- **`c1_shaped_s1`**: the same with another seed, to show how much two runs differ.
- **`c1_outcome`**: the win or loss only, to ask whether the small rewards help.

## How they did

576 matches each against the scripted commander (192 per mission, each side half the
time, the same pilots for every commander), so each score is good to about ±0.04:

| Commander | Overall | Deathmatch | Carrier | Convoy |
|---|---|---|---|---|
| `c1_shaped` | 0.56 | 0.49 | 0.56 | 0.62 |
| `c1_outcome` | 0.55 | 0.54 | 0.56 | 0.54 |
| `c1_shaped_s1` | 0.53 | 0.54 | 0.56 | 0.49 |
| Random orders | 0.54 | 0.51 | 0.57 | 0.55 |
| Untrained, last night | 0.46 | 0.43 | 0.44 | 0.50 |

Against each other they are even: 0.52, 0.50 and 0.50, all within noise. The small
rewards made no difference we can see in one night.

**Training moved the learned commander from a little worse than the script to about
level with it.** It flies its own launches and steers its own carrier, which the
random-orders commander leaves to the script, so the night's gain is mostly in that
logistics. Its orders are no better than random ones, and that is what we expected:
most of the live ten ignore orders, so orders barely change a match. They ask to be
followed; the pilots do not yet listen.

## What they do

Over the last 40 updates the three behave alike. Each second, about half their squads
get a new order or have theirs cleared (a squad that just got one is locked for three
seconds, and an empty squad gets none). Of those, about a third clear the order, just
over a quarter attack, a fifth defend and a sixth go to a point. They launch from a bay
on about one decision in twenty.

## Next

The loop is commanders, then pilots, then commanders. Tonight's pilot phase trains
under these commanders with more go-to drills, so following orders pays more. The
pilots will be judged by wins above replacement in matches like the live page's,
rather than by the order gate. Once pilots follow, the next commander phase should
find that orders matter.
