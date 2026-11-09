# A third night of training, and pilots judged by wins above replacement

Shipped to the live page on 2026-11-09, `SIM_VERSION` 6.

<!-- summary: Three new pilots join the live page, the first chosen by wins above replacement: how many more matches a side wins with them flying instead of the script, in matches like the live page's. More go-to drills did not teach go-to. With the new pilots in the field, the learned commanders now beat the script 57% of the time. -->

The live page still flies ten pilots, drawn ship by ship. Three are new this morning, from
a third night of the same training lines as the [second list](../2026-11-07-second-night/).
And the list is chosen a new way.

## A new way to pick pilots

Until now pilots were ranked by a round robin: one pilot flying a whole side against
another, with no commander. The live page is nothing like that. Each ship gets its own
pilot, and each side has a commander.

So the ranking is now **wins above replacement**, borrowed from baseball. We play 4,320
matches like the live page's: deathmatch, carrier battle and convoy escort, each ship's
pilot drawn at random from the field or the sim's script, each side's commander drawn from
the live stable. Then a model sorts out how much each pilot adds to its side's chance of
winning. A pilot's score is the extra wins per 100 matches a side gets with it flying
instead of the script. The script is the replacement level, so it scores 0.

Tap a ship on the live page and its pilot's score is the "wins per 100 matches over the
script".

## The night

Three lines ran from 01:15 to 07:00, about 380 updates each. Two things changed from the
second night:

- **The learned commanders gave the orders.** Every training match with orders drew each
  side's commander from the live stable, the script and the three
  [learned commanders](../2026-11-08-commander-1/), as the live page does.
- **More drills, mostly go-to.** Go-to is every line's weakest order, so drills went up to
  a third of `fighters` and `followers` matches (from a quarter) and a quarter of
  `fighters_pay1`'s (from a tenth), with go-to drawn two or three times as often as attack
  or defend.

## The ten

Best first, with the 95% range. Each range is about ±3.

1. **`f99_696`, +20.8.** A sibling of `f995_701` with a shorter horizon.
2. **`f995_701`, +19.8.** The long-horizon fighter and founder of the `fighters` family.
3. **`f995_400`, +18.3.** The same training run as `f995_701`, 301 updates earlier.
4. **`fighters_pay1_462`, +16.7.**
5. **`fighters_1338`, +16.2.** New. `fighters_959`, one night on.
6. **`followers_1323`, +15.5.** New. `followers_955`, one night on.
7. **`fighters_pay1_849`, +14.9.** New. `fighters_pay1_462`, one night on.
8. **`fighters_506`, +14.4.**
9. **`fighters_959`, +14.4.**
10. **`followers_955`, +11.4.**

Left off: `reward_300` (+10.0), `followers_513` (+7.5), `hide_644` (+7.1) and
`transit_300` (+0.2, the same as the script).

Two things stand out. The top three are the oldest pilots on the list, from one night of training that
paid nothing for following orders. And every pilot is far ahead of the script: even
`followers_955`, tenth, wins its side 11 more matches in 100.

## What the night answered

**The followers made the biggest gain.** `followers_1323` adds 15.5 wins per 100, up from
11.4 for `followers_955` the night before, and is now level with the fighters family. It
still follows orders best of anyone on the list.

**The fighters held steady.** `fighters_1338` adds 1.8 more than `fighters_959` and
`fighters_pay1_849` 1.8 fewer than `fighters_pay1_462`. Both are within the noise.

**More go-to drills did not teach go-to.** How often a pilot reaches the point it was sent
to:

| Line | Second night | Third night |
|---|---|---|
| `followers` | 50% | 47% |
| `fighters` | 30% | 24% |
| `fighters_pay1` | 20% | 21% |

Attack and defend following rose a little for `fighters` (changes target when the order
changes: 50% to 59% on attack, 56% to 67% on defend) and for `followers` on defend (77% to
84%). Go-to needs something other than more of the same drill.

**The learned commanders pull ahead.** In the 1,572 of these matches where a learned
commander faced the script, it won 57.5% (±2.5), up from 53.8% the day before with the
older pilots. It gained most in deathmatch (49% to 54%) and convoy escort (52% to 58%).
Pilots trained under the learned commanders seem to suit them better. In training the
same showed up more strongly: the three lines won 61 to 69% of their matches under a learned
commander and 46 to 61% under the script.

## The season's records

The judging moved to wins above replacement too. A family may keep four of its
lines in training. The `fighters` family had six, so its two weakest, `fighters_506` and
`fighters_959`, are retired from training. Nobody scored below the script, so
nobody else goes. Retired pilots still fly on the page if they score well enough, and
these two do. Training goes on from `fighters_1338` and `fighters_pay1_849`.

Nine stay in training: four `fighters`, four `followers` and the script. `transit_300`, the
followers' founder, scores the same as the script but stays. It is a good follower and a
useful opponent.

## What these numbers don't tell you

Scores are relative to this field: adding stronger pilots moved everyone's score by a few
wins, so compare within one measurement, not across days. Two pilots can only be told
apart when their ranges barely overlap. That is true of the top three against the rest,
and of almost no pair in the middle.

The data is `lab/population/2026-11-sim6/war/third-night/war.json` (every match and the
fit). How the night's training went is in `lab/runs/2026-11-01-pilot-families/plan.md`.

## What's next

The loop is commanders, then pilots, then commanders. The pilots now follow attack and
defend orders a little better, and the commanders already gain from them. The next
commander phase trains against these pilots.
