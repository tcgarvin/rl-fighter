# A third night of training, and pilots judged by wins above replacement

Shipped to the live page on 2026-11-09, `SIM_VERSION` 6 (the sixth version of the game's rules).

<!-- summary: Three new pilots join the live page, the first chosen by wins above replacement: how many more matches out of 100 a side wins with a pilot flying its ships instead of our hand-written pilot, in matches like the live page's. More practice on "go to this point" orders did not teach pilots to follow them. With the new pilots in the field, the learned commanders now beat the scripted commander 57% of the time. -->

The live page, the site's front page, plays matches forever with ten pilots, drawn at
random ship by ship. Three are new this morning, from a third night of training. They are
also the first chosen a new way: by **wins above replacement** (WAR), how many more matches
out of 100 a side wins with a pilot flying its ships instead of the script, our
hand-written pilot. The best pilots add about 20 wins in 100.

The night also asked whether more practice would teach pilots to follow "go to this point"
orders. It did not. And with the new pilots in the field, the learned commanders (trained
networks that give a side's ships their orders) now beat the hand-written commander 57% of
the time.

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a **pilot**, a small
neural network that learned to fly by trial and error. Each side also has a **commander**,
a second network or a hand-written script that sees the whole side and gives its ships
orders: attack that ship, defend that one, go to that point.

<!-- figure-idea: shared: what an order is. A commander above a side of ships, with an attack arrow to an enemy, a defend ring around a friendly ship and a go-to point, and the pilots below free to follow or ignore them. Helps here because the night is about pilots learning to follow orders. -->

A week before, [ten pilots went onto the live page](../2026-11-02-ten-pilots/results.md).
Since then each night of training has carried on three lines, each a pilot trained further
night after night: `fighters` (strong fighters, paid well for following orders),
`followers` (pilots that follow orders, learning to fight) and, from the
[second night](../2026-11-07-second-night/results.md), `fighters_pay1` (the `fighters`
setup paid a third as much for following). The day before this night,
[the first learned commanders](../2026-11-08-commander-1/results.md) joined the page,
about level with the scripted one. Orders matter only if pilots follow them, so this night
trained pilots under those commanders, with more practice on orders. And it changed how we
decide which pilots fly, because the old ranking measured matches nothing like the page's.

## A new way to pick pilots

Until now pilots were ranked by a round robin: every pilot played every other, one pilot
flying a whole side against another, with no commander, and the results gave each a rating
like a chess rating. The live page is nothing like that. Each ship gets its own pilot,
drawn at random, so a side is a mix of pilots, and each side has a commander.

So the ranking is now **wins above replacement**, borrowed from baseball. There a player's
WAR is how many more games his team wins with him than with a "replacement" player, the
kind any team can find cheaply. Here the replacement is the script: any side can always have
its ships flown by it, so it scores 0 by definition.

<!-- figure-idea: shared: how WAR works. A grid of matches, each ship coloured by the pilot drawn for it (the script among them), the matches' results feeding a fit, and out the other end each pilot's wins per 100 over the script. Helps a reader see why random mixing lets the fit tell one pilot's share from its teammates'. -->

How it is measured:

- **Matches like the live page's.** We play 4,320 matches, 1,440 each of the page's three
  missions: team deathmatch (last side standing wins), carrier battle (each side has a
  carrier, the big ship that launches the small ones, and destroying the enemy's wins) and
  convoy escort (one side guards cargo ships, the other attacks them). Each ship's pilot is
  drawn at random from the candidates and the script. Each side's commander is drawn from
  the live stable, the four commanders the page uses: the scripted one and three learned
  ones.
- **A fit sorts out who added what.** Because the draws are random, each pilot flies on
  many different sides, beside and against every other. A statistical model (a
  logistic regression, like the plus-minus ratings used in basketball) estimates how much
  each pilot's ships add to their side's chance of winning, allowing for the mission, the
  side and the commanders.
- **The score.** For every match a pilot flew in, the model's chance that its side wins,
  minus the same chance with its ships flown by the script instead. Averaged over those
  matches and multiplied by 100, that is the pilot's WAR: extra wins per 100 matches. A
  draw counts as half a win.

Tap a ship on the live page and its pilot's score is the "wins per 100 matches over the
script".

## The night

Three lines ran from 01:15 to 07:00, about 380 updates each. An update is one round of
training: play a batch of matches, then adjust the network once. Two things changed from
the second night:

- **The learned commanders gave the orders.** Every training match with orders drew each
  side's commander from the live stable, the script and the three
  [learned commanders](../2026-11-08-commander-1/results.md), as the live page does.
- **More drills, mostly go-to.** Drills are short practice scenarios built around one
  order. Go-to is every line's weakest order, so drills went up to a third of `fighters`
  and `followers` matches (from a quarter) and a quarter of `fighters_pay1`'s (from a
  tenth), with go-to drawn two or three times as often as attack or defend.

## The ten

A pilot's name is its training line followed by the update it was saved at:
`fighters_1338` is the `fighters` line after 1,338 updates. The `f995` and `f99` pilots
come from an earlier run, [fighters v2](../2026-11-01-fighters-v2/results.md), named for the
horizon they trained with, how far ahead a pilot weighs future reward (0.995 looks further
ahead than 0.99).

Best first. Each number is the pilot's wins added per 100 matches over the script. Each is
good to about ±3: ± is the margin of error, and the true value is very likely within 3 of
the number shown (a 95% range).

1. **`f99_696`, +20.8.** A sibling of `f995_701` with a shorter horizon.
2. **`f995_701`, +19.8.** The long-horizon fighter and founder of the `fighters` family,
   the pilot every `fighters` and `fighters_pay1` pilot descends from.
3. **`f995_400`, +18.3.** The same training run as `f995_701`, 301 updates earlier.
4. **`fighters_pay1_462`, +16.7.**
5. **`fighters_1338`, +16.2.** New: `fighters_959` after one more night of training.
6. **`followers_1323`, +15.5.** New: `followers_955` after one more night of training.
7. **`fighters_pay1_849`, +14.9.** New: `fighters_pay1_462` after one more night of training.
8. **`fighters_506`, +14.4.**
9. **`fighters_959`, +14.4.**
10. **`followers_955`, +11.4.**

Left off: `reward_300` (+10.0), `followers_513` (+7.5), `hide_644` (+7.1) and
`transit_300` (+0.2, the same as the script). These are older pilots from earlier runs.
`transit_300` is the follower the `followers` line started from.

Two things stand out. The top three are the oldest pilots on the list, from one night of training that
paid nothing for following orders. And every pilot is far ahead of the script: even
`followers_955`, tenth, wins its side 11 more matches in 100.

## What the night answered

**The followers made the biggest gain.** `followers_1323` adds 15.5 wins per 100, up from
11.4 for `followers_955` the night before, and is now level with the fighters family. It
still follows orders best of anyone on the list.

**The fighters held steady.** `fighters_1338` adds 1.8 more than `fighters_959` and
`fighters_pay1_849` 1.8 fewer than `fighters_pay1_462`. Both are within the noise: the
gaps are smaller than the margin of error.

**More go-to drills did not teach go-to.** How often each line's newest pilot reaches the
point it was sent to in the drills, after the second night and after the third:

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

The season is the record of every pilot trained under this version of the rules. The
judging of who stays active moved to wins above replacement too. Active members are the
ones training may carry on from. A pilot that is archived (retired from training) stays on
record. A family, a pilot and its descendants, may keep four of its pilots active. The
`fighters` family had six, so its two weakest, `fighters_506` and `fighters_959`, are
archived. Nobody scored below the script, so nobody else goes. Archived pilots still fly on
the page if they score well enough, and these two do. Training goes on from `fighters_1338` and
`fighters_pay1_849`.

Nine stay active: four `fighters`, four `followers` and the script, which is never trained
but stays on the list as the yardstick. `transit_300`, the followers' founder, scores the same as the script but stays. It is a good follower and a
useful opponent.

## What these numbers don't tell you

Scores are relative to this field: adding stronger pilots moved everyone's score by a few
wins, so compare within one measurement, not across days. Two pilots can only be told
apart when their ranges barely overlap, which with ranges of about ±3 takes a gap of about
6. That is true of the top pilot, `f99_696` (+17.4 to +23.9), against the bottom three of
the ten, and of almost no pair of neighbours. The top three's ranges overlap those of the
next several.

The data is `lab/population/2026-11-sim6/war/third-night/war.json` (every match and the
fit). How the night's training went is in `lab/runs/2026-11-01-pilot-families/plan.md`.

## What's next

The loop is commanders, then pilots, then commanders: we alternate a night of training for
one with a night for the other, each against the latest of the other. The pilots now follow
attack and defend orders a little better, and the commanders already gain from them. The
next commander phase trains against these pilots.
