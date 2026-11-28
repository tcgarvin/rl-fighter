# A second night of training puts three new pilots on the live page

Shipped to the live page on 2026-11-07, `SIM_VERSION` 6.

<!-- summary: A second night of training put three new pilots on the live page. The strongest fighter is now one paid less for following orders, which answers the first night's question: extra pay for following buys a little following at the cost of some fighting. More practice drills taught fighters_959 to follow orders better, still not well enough to pass our test for following. None of the three new pilots passes it. -->

The live page still flies ten pilots, drawn at random ship by ship. Three of them are new
this morning, from a second night of the same training as the
[first list](../2026-11-02-ten-pilots/). They replace `transit_300`, `w1_400` and `v1`, the
three weakest pilots that are not the script. (The script is our hand-written, rule-based
pilot. It is rated alongside the trained pilots as a yardstick, but the list is picked
from the others.)

The night asked two things. Does paying a pilot extra for following orders cost it
fighting skill? Yes, some: the new strongest fighter is the one paid less. And does more
practice on orders teach a strong fighter to follow? A little, not enough.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network
that learned to fly by trial and error ([how a pilot works](/pilot/)). Each side's
commander can give its ships orders: attack a named enemy, defend a friendly ship, or go to
a point. Our best fighters ignore orders, and our best followers fight badly. On the night
of 2026-11-01 we began training three lines of pilots to close that gap
([the pilot families plan](../2026-11-01-pilot-families/plan.md)), and
[the first ten](../2026-11-02-ten-pilots/) went live. That night's best new fighter,
`fighters_506`, gained some following. It had trained with some order drills (short
practice scenarios for one order) and with three times the pay for following that the
other lines got, so we could not tell which did it. "Pay" here is reward in training: the
points a pilot earns, which training pushes it to collect. Order pay is the extra reward
for doing what an order says. This night tests the pay, and tries more drills.

We measure following in drills. Go-to is how often a pilot arrives where it was sent.
Attack and defend use a swap test: each drill is flown twice from the same start, with the
enemy to attack (or friend to defend) on opposite sides, and we count how often the pilot
changes target when the order changes. The order gate is a set of pass marks on these.

A pilot's name is its training line followed by the training update (one round of
training: play a batch of matches, then adjust the network once) it was saved at.

## The night

Three training lines ran from 01:17 to 07:30, about 450 updates each.

- **`fighters` continued from `fighters_506`** with more of its matches spent on order
  drills (a quarter, up from a tenth). Last time its following moved on attack and
  defend orders but not on go-to.
- **`followers` continued from `followers_513`** unchanged, to build on its combat.
- **`fighters_pay1` started over from `f995_701`**, the strong fighter that founded the
  `fighters` family and ignores orders. It is the first night's `fighters`
  setup with one change: following an order pays a third as much. That asks whether the
  higher pay is what taught `fighters_506` to follow.

Both continuing lines also gained the first night's two new pilots as enemies to train
against.

## The ten

Best first. Ratings come from a round robin, in which every pilot played every other, one
pilot flying a whole side with no commander, and work like chess ratings: a gap of 100
means roughly 64 wins to 36. They are points in this field only. The field changed, so they
are not comparable with the first list's.

1. **`fighters_pay1_462`, +300.** New. It beats every other pilot overall, from 57% (`fighters_959`) to 100%,
   and has the field's best results in deathmatch and carrier battle.
2. **`fighters_506`, +255.** Top of the first list.
3. **`fighters_959`, +240.** New. `fighters_506`'s line, one night on.
4. **`f995_701`, +214.** The long-horizon fighter, named for its discount of 0.995 (it
   weighs rewards further ahead than a pilot trained at 0.99), and founder of the
   `fighters` family.
5. **`f99_696`, +196.** A sibling of `f995_701` with a shorter horizon.
6. **`f995_400`, +196.** The same training run as `f995_701`, 301 updates earlier.
7. **`followers_955`, +146.** New. `followers_513`'s line, one night on.
8. **`followers_513`, +80.**
9. **`hide_644`, -44.**
10. **`reward_300`, -90.**

Left off: `transit_300` (-122), `w1_400` (-140), `v1` (-208), the script (-416) and
`scratch_417` (-607, the line trained from nothing).

## What the night answered

**Order pay trades combat for following.** `fighters_pay1_462`, at a third of the pay,
beats `fighters_506` 60% of the time in deathmatch (last side standing wins), 61% in
carrier battles (destroy the other side's carrier) and 57% in convoy escort (one side
guards cargo ships, the other attacks them), with 44 fewer updates. It also follows orders less: it changes target when the order
changes 25% of the time on attack orders and 21% on defend, against `fighters_506`'s 32% and
36%. Go-to is the same for both, about 20%. This is one training run of each, so the size of
the trade is rough.

**More drills taught `fighters` to follow, but not enough.** `fighters_959` arrives where it
is sent 30% of the time, up from 21%, and changes target on attack and defend orders half the
time, up from a third. It is the best follower among the fighters, and still fails every
part of the order gate (our pass marks on the order drills). Combat dipped: it wins 46% against `fighters_506` in deathmatch, 47%
in carrier battles and 54% in convoy escort.

**`followers` gained combat and lost some following.** `followers_955` beats `followers_513`
69%, 61% and 55% across the three missions. But it arrives where it is sent only 50% of the
time, against the gate's 60% bar and 62% the night before, so it fails the gate on go-to.
Its attack and defend results still pass.

## How they fit against each other

<div data-figure="matchups"></div>

**Still a ladder, with one exception.** Of 349 sets of three pilots with clear results,
none forms a rock-paper-scissors cycle overall. In convoy escort alone, one does:
`f99_696` beats `fighters_959` 61%, `fighters_959` beats `fighters_pay1_462` 56%, and
`fighters_pay1_462` beats `f99_696` 59%. The weakest of those three edges is at the edge of
the noise of 240 matches (with that many, chance alone can move a result about 6 points
from 50%), so it may not hold up.

**The followers are closing in, slowly.** `followers_955` is closer to the top tier than
`followers_513` was, but still wins only 18 to 45% of its matches against the top four, by mode.

## Who follows orders

The table gives the drill results described above: go-to arrival, and the attack and defend
swap tests. `f995_701`, a founder, is exempt from the gate: the plan's rule judges only the
pilots trained from the founders. All on the live list
except `followers_513` fail the
order gate, so about one fighter in ten on the page is flown by a pilot that follows its
commander, down from one in five.

| Pilot | Go-to | Attack | Defend | Gate |
|---|---|---|---|---|
| `followers_513` | 62% | 88% | 86% | Passed |
| `followers_955` | 50% | 81% | 77% | Failed on go-to |
| `fighters_959` | 30% | 50% | 56% | Failed |
| `fighters_506` | 21% | 32% | 36% | Failed |
| `fighters_pay1_462` | 20% | 25% | 21% | Failed |
| `f995_701` | 22% | 14% | 11% | Failed, exempt |

The season's records (every pilot trained under this version of the rules) follow the
gate: the three new pilots are marked archived, as `fighters_506` was. That only records
the failure. They stay in the round robin, and the live page picks on combat rating, so
they fly anyway. (Later the same day the owner dropped the gate as a reason to archive,
and all four were restored to active. From the third night on, places went by wins above
replacement, a measure taken in matches like the live page's.)

## What these numbers don't tell you

The same limits as the [first list](../2026-11-02-ten-pilots/): ratings come from one pilot
flying a whole side with no commander, while the page mixes pilots under a scripted
commander, and sides are drawn without balancing.

The grid's data is `matchups.json`, from `lab/population/2026-11-sim6/round_robin/second-night`
(105 pairs, 75,600 matches including the script and `scratch_417`). How the night's training
went is in [the families plan](../2026-11-01-pilot-families/plan.md).

## What's next

<!-- figure-idea: shared: the trade between fighting and following as a scatter, each pilot placed by combat rating and by drill following, with arrows from parent to child; it would show at a glance that no pilot yet sits in the "fights and follows" corner, and could be redrawn for later nights -->

Still the same goal: a top-tier fighter that also follows orders. Drills help, and order
pay helps a little, but each costs some combat. The plan's next step for `fighters` is
separate skill networks for fighting and following, rather than one net doing both.
