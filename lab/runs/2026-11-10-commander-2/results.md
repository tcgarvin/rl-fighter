# Orders now last five seconds; a price on orders did not make them last longer

Verdict: **PARTIAL**. The hold works and went to the live page on 2026-11-11
(`SIM_VERSION` 7, the seventh version of the game's rules); the price on orders did not.

<!-- summary: The learned commanders, the networks that give a side's ships their orders, were changing a ship's orders every second or two. A ship now keeps a changed order for five seconds unless the order is used up, which cut orders ending inside five seconds from 96% to 7%. A night of training that charged commanders for each change did not teach them to wait any longer than that, so no new commander joins the live page. A commander giving random orders now beats the hand-written commander 0.60 to 0.40. -->

Watching the live page, the owner saw that the learned commanders, the trained networks
that give each side's ships their orders, "change orders far too
often, sometimes giving ships changing orders every second". This entry is the fix, a rule
that a ship keeps a new order for five seconds, and a night of training that tried to go
further and did not. The rule works: orders that end inside five seconds fell from 96% to
7%, at no cost in wins we can see. Charging commanders a small price for each change did
not teach them to let an order run any longer than the rule makes them.

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a **pilot**, a small
neural network that learned to fly by trial and error. Each side also has a **commander**
that sees the whole side and gives its ships orders: attack that enemy, defend that friendly
ship, go to that point. A commander can be the hand-written one (the scripted commander) or
a learned network. It decides once a second, and it orders ships in groups: it puts each
ship in one of up to four squads and gives each squad an order.

<!-- figure-idea: shared: what an order is. A commander above its side, the ships grouped into squads, each squad with its order drawn on the map (an attack arrow to an enemy, a defend ring around a friendly ship, a go-to point), and the pilots free to follow or ignore it. Helps here because squads and squad orders are what the old locks and the new hold act on. -->

Two days before, [the first learned commanders](../2026-11-08-commander-1/results.md)
went onto the live page, about level with the scripted one, and no better than a commander
that gives random orders: most pilots did not follow orders, so orders barely changed who
won. Since then two nights of pilot training, the [third](../2026-11-09-third-night/results.md)
and [fourth](../2026-11-10-fourth-night/results.md), produced the pilots these commanders
now lead. We alternate commander and pilot training, so this was the commanders' turn, and
the obvious flaw to fix first was how often they changed their minds.

## What was wrong

- **The old locks had a gap.** A squad's order was locked for three seconds after it
  changed, and a ship for three seconds after it moved squad, but neither lock saw the
  other. A ship could get a new order through its squad, be moved to another squad a second
  later, and have that squad's order change the second after.
- **Changing an order cost nothing**, and most pilots ignore orders, so training had no
  reason to prefer one order over another. The choices drifted toward even odds.

## The hold

Under a learned commander, a ship whose order changes, by either route, now keeps that
order for five seconds: it
cannot move squad, and its squad's order cannot change. The hold ends early when the order
is spent, that is, used up: the target or the ship it guards is gone, or the ship has
arrived at its go-to point. The details are on the [commander page](/commander/).

<!-- figure-idea: a timeline of one ship's orders over thirty seconds, under the old three-second locks (a new order every second or two, from squad moves and squad orders slipping past each other's locks) and under the five-second hold (each order a solid five-second bar, cut short only when its target dies). Helps a reader see the gap in the old locks and what the hold changes. -->

`c1_shaped`, the learned commander already on the live page, against the scripted
commander on the same 144 matches under both rules. "Orders a ship-minute" is how many new
orders each ship gets per minute. "Median order" is how long a typical order lasts. "Time
under an order" is the share of time a ship has any order at all.

| Rule | Orders a ship-minute | Median order | Orders ending inside 5 s | Time under an order |
|---|---|---|---|---|
| Old three-second locks | 10.1 | 3.0 s | 96% | 45% |
| Five-second hold | 6.8 | 5.0 s | 7% | 52% |

It scored 0.54 under both rules (the share of matches won, where 0.5 is even), so the hold
cost it nothing we can see. The 7% that still end early are spent orders.

## The night

The hold caps the churn but does not teach a commander to let an order run: `c1_shaped`
re-orders the moment it is allowed. So we trained three new commanders, the night's three
arms, from scratch, identical except for one setting. They ran from 23:03 to 10:45, about
415 updates and 3.4 million decisions each. An update is one round of training: play a
batch of matches, then adjust the network once. The question was whether a price would
teach patience:

- **`hold`**: the hold alone.
- **`price2`**: also pays 0.002 for every ship it re-orders. A commander is trained on
  points, its reward: a win is +1 and a loss −1, so a side of six ships re-ordered every
  five seconds for 100 seconds would pay 0.24 at this price.
- **`price5`**: pays 0.005.

All three started leaning toward "keep", the choice that leaves an order as it is: four
choices in five.

## How they did

576 matches each against the scripted commander (192 per mission, the same pilots for every
commander). The missions are team deathmatch (last side standing wins), carrier battle (each
side has a carrier, the big ship that launches the small ones, and destroying the enemy's
wins) and convoy escort (one side guards cargo ships, the other attacks them). Each score is
the share of matches won, 0.5 being even, and is good to about ±0.04: ± is the margin of
error, the range the true value very likely lies in. The last three columns describe the
commander's own orders. The scripted commander's row has no scores because it is the
opponent.

| Commander | Overall | Deathmatch | Carrier | Convoy | Orders a ship-minute | Mean order | Time under an order |
|---|---|---|---|---|---|---|---|
| `price5` | 0.62 | 0.64 | 0.65 | 0.58 | 5.7 | 5.0 s | 45% |
| Random orders | 0.60 | 0.58 | 0.61 | 0.61 | 4.2 | 9.9 s | 62% |
| `hold` | 0.59 | 0.64 | 0.49 | 0.64 | 5.3 | 5.0 s | 41% |
| `price2` | 0.59 | 0.59 | 0.56 | 0.61 | 6.3 | 5.0 s | 48% |
| `c1_shaped` (phase 1) | 0.53 | 0.54 | 0.52 | 0.54 | 6.8 | 5.0 s | 53% |
| Scripted commander | | | | | 5.0 | 10.4 s | 99% |

"Phase 1" is the [first commander night](../2026-11-08-commander-1/results.md). "Random
orders" is a commander that gives orders at random, our baseline. Against each other the
three new lines are even: `hold` won 0.55 against `price2` and 0.51 against `price5`, and
`price2` won 0.49 against `price5`.

- **The price did not work.** Every line's orders last exactly the hold: mean 5.0 seconds,
  priced or not. During training the share of free order choices, the ones the hold left
  open, that changed the order rose from 16% to about 50% in all three lines. The lean
  toward "keep" was gone within a hundred updates.
- **Why, as far as we can tell:** training also rewards a commander for keeping its choices
  varied (the entropy bonus, which keeps a network exploring while it learns), and since
  orders barely change who wins, that push was stronger than a price this small. We did not
  test this; it is the reading that fits the logs.
- **No learned line is better than random orders.** All three sit within noise of the
  random commander, as in phase 1.
- **Random orders now beat the script, 0.60 to 0.40.** In phase 1 it was 0.54. The script
  keeps its ships under an order 99% of the time; the random commander 62%, the learned
  ones under half. With the [fourth night's](../2026-11-10-fourth-night/results.md) pilots,
  the script's orders seem to cost it matches. That matters beyond this entry: the script is
  the commander every learned one is compared with.
- The scripted commander is not held: the hold applies to learned commanders, not to the
  scripted or random ones. Holding the script too would change the game's own rules, and
  the script is what every learned commander is compared with, so that is a separate
  decision for the owner. A third of its own orders end inside five seconds.

## What goes live

The live page draws each side's commander from a stable, a short list. The plan set the bar
before the run: a new line joins the stable only if its orders last well over five seconds.
None does, so none joins. The stable stays the script and the three `c1` commanders from
phase 1, and the live page now applies the hold to them.

## Next

- The hold fixes what the owner saw. Making orders last longer than the hold needs more
  than a small price: a much larger one, or no entropy bonus on the order choices.
- The larger problem is unchanged from phase 1. Orders do not matter to who wins, because
  most pilots do not follow them, so a commander has nothing to learn about which order to
  give. That is the pilots' side of the loop, and it is their turn next.
- The script losing to random orders needs a look before the pilots' next night, since
  their matches are commanded by it.
