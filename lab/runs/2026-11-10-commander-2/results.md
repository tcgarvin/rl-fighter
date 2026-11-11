# Orders now last five seconds; a price on orders did not make them last longer

Verdict: **PARTIAL**. The hold works and went to the live page on 2026-11-11
(`SIM_VERSION` 7); the price on orders did not.

<!-- summary: Learned commanders were re-ordering ships every second or two. A ship now keeps a changed order for five seconds unless the order is spent, which cut orders ending inside five seconds from 96% to 7%. A night of training with a price on each re-order did not teach commanders to wait any longer than the hold, and no new commander joins the live page. Random orders now beat the scripted commander 0.60 to 0.40. -->

Watching the live page, the owner saw that the learned commanders "change orders far too
often, sometimes giving ships changing orders every second". This entry is the fix, and a
night of training that tried to go further and did not.

## What was wrong

- **The old locks had a gap.** A squad's order was locked for three seconds after it
  changed, and a ship for three seconds after it moved squad, but neither lock saw the
  other. A ship could get a new order through its squad, be moved to another squad a second
  later, and have that squad's order change the second after.
- **Changing an order cost nothing**, and most pilots ignore orders, so training had no
  reason to prefer one order over another. The choices drifted toward even odds.

## The hold

A ship whose order changes, by either route, now keeps that order for five seconds: it
cannot move squad, and its squad's order cannot change. The hold ends early when the order
is spent: the target or the ship it guards is gone, or the ship has arrived at its go-to
point. The details are on the [commander page](/commander/).

`c1_shaped`, the commander already on the live page, against the scripted commander on the
same 144 matches under both rules:

| Rule | Orders a ship-minute | Median order | Orders ending inside 5 s | Time under an order |
|---|---|---|---|---|
| Old three-second locks | 10.1 | 3.0 s | 96% | 45% |
| Five-second hold | 6.8 | 5.0 s | 7% | 52% |

It scored 0.54 under both rules, so the hold cost it nothing we can see. The 7% that still
end early are spent orders.

## The night

The hold caps the churn but does not teach a commander to let an order run: `c1_shaped`
re-orders the moment it is allowed. Three fresh lines trained from 23:03 to 10:45, about
415 updates and 3.4 million decisions each, to see whether a price would:

- **`hold`**: the hold alone.
- **`price2`**: also pays 0.002 for every ship it re-orders (a win is +1).
- **`price5`**: pays 0.005.

All three started leaning toward "keep": four choices in five.

## How they did

576 matches each against the scripted commander (192 per mission, the same pilots for every
commander), so each score is good to about ±0.04:

| Commander | Overall | Deathmatch | Carrier | Convoy | Orders a ship-minute | Mean order | Time under an order |
|---|---|---|---|---|---|---|---|
| `price5` | 0.62 | 0.64 | 0.65 | 0.58 | 5.7 | 5.0 s | 45% |
| Random orders | 0.60 | 0.58 | 0.61 | 0.61 | 4.2 | 9.9 s | 62% |
| `hold` | 0.59 | 0.64 | 0.49 | 0.64 | 5.3 | 5.0 s | 41% |
| `price2` | 0.59 | 0.59 | 0.56 | 0.61 | 6.3 | 5.0 s | 48% |
| `c1_shaped` (phase 1) | 0.53 | 0.54 | 0.52 | 0.54 | 6.8 | 5.0 s | 53% |
| Scripted commander | | | | | 5.0 | 10.4 s | 99% |

Against each other the three new lines are even: 0.55, 0.51 and 0.49.

- **The price did not work.** Every line's orders last exactly the hold: mean 5.0 seconds,
  priced or not. During training the share of free order choices that changed the order
  rose from 16% to about 50% in all three lines. The lean toward "keep" was gone within a
  hundred updates.
- **Why, as far as we can tell:** training also rewards a commander for keeping its choices
  varied (the entropy bonus), and since orders barely change who wins, that push was
  stronger than a price this small. We did not test this; it is the reading that fits the
  logs.
- **No learned line is better than random orders.** All three sit within noise of the
  random commander, as in phase 1.
- **Random orders now beat the script, 0.60 to 0.40.** In phase 1 it was 0.54. The script
  keeps its ships under an order 99% of the time; the random commander 62%, the learned
  ones under half. With the fourth night's pilots, the script's orders seem to cost it
  matches. That matters beyond this entry: the script is the commander every learned one is
  compared with.
- The scripted commander is not held. A third of its own orders end inside five seconds.

## What goes live

The plan set the bar before the run: a new line joins the stable only if its orders last
well over five seconds. None does, so none joins. The stable stays the script and the three
`c1` commanders, and the live page now applies the hold to them.

## Next

- The hold fixes what the owner saw. Making orders last longer than the hold needs more
  than a small price: a much larger one, or no entropy bonus on the order choices.
- The larger problem is unchanged from phase 1. Orders do not matter to who wins, because
  most pilots do not follow them, so a commander has nothing to learn about which order to
  give. That is the pilots' side of the loop, and it is their turn next.
- The script losing to random orders needs a look before the pilots' next night, since
  their matches are commanded by it.
