# Ten pilots now fly the live page, and this is how they stack up

Shipped to the live page on 2026-11-02, `SIM_VERSION` 6.

<!-- summary: Each fighter on the live page is now flown by one of ten nets, drawn at random ship by ship. They form a clear ladder with no rock-paper-scissors: four strong fighters, one pilot that both fights and follows orders, and five weaker pilots. Convoy escort is the one place the order changes at the top. -->

Until today one net flew every fighter on the page. Now each strike craft gets one of ten
nets at random, so a single squad can hold several different minds. Carriers, freighters
and both commanders are still flown by scripts.

You can look at them yourself: **tap a ship on the live page**. The camera comes in on it
and a panel says which net is flying. "Details", or a second tap, opens the odds that net
gives each thruster, turret and trigger, a few times a second, alongside what it actually drew.

## The ten

Best first. Ratings are points in this field only: a gap of 100 means roughly 64 wins to 36.

1. **`fighters_506`, +314.** Strongest in the field. Forked from `f995_701` with order pay
   and drills. It gained combat but follows orders only a little.
2. **`f995_701`, +277.** The long-horizon fighter, the champion before this list. Fights
   hard and ignores orders.
3. **`f995_400`, +264.** The same training run as `f995_701`, 301 updates earlier.
4. **`f99_696`, +246.** A sibling of `f995_701` with a shorter horizon.
5. **`followers_513`, +144.** The only pilot that both fights well and follows orders.
   Forked from `transit_300`.
6. **`hide_644`, +8.** Trained so that a shot under an order earned only order pay. It did
   not learn to follow.
7. **`reward_300`, -38.** Paid for following orders, with no script pull. It barely learned
   to follow.
8. **`transit_300`, -71.** Pulled toward the script on the way to an order. The best neural
   follower, and a weak fighter.
9. **`w1_400`, -88.** An early order pilot with the older, smaller order inputs.
10. **`v1`, -156.** The first fleet pilot: a clone of the script, sharpened by PPO. It
    predates orders and cannot read them.

The list is the ten highest rated in the season who are not the script (-357). That leaves
out only `scratch_417` (-543), trained from nothing for one night. `fighters_506` flies even
though it failed the order gate and is archived in the season's records: the gate rules on
following orders, and the page picks on combat rating.

## How they fit against each other

<div data-figure="matchups"></div>

**It is a ladder.** Across every set of three pilots with clear results, not one forms a
rock-paper-scissors cycle (0 of 173). A higher rating almost always means a winning record,
and these pilots don't yet have distinct styles that counter each other.

**There are three tiers.**

- **The top four** split their matches closely. `fighters_506` beats the other three 58 to
  60% of the time, and those three are within 48 to 52% of each other.
- **`followers_513` stands alone in the middle.** It wins only 27 to 34% against the top
  four, and 67 to 85% against everyone below.
- **The bottom five** beat each other by smaller margins, from 52% to 71%.

**Convoy escort is where the top changes.** `fighters_506` beats everyone in deathmatch and
carrier battles, but not here. `f995_400` beats it 57% of the time, just outside the noise of
240 matches, and beats `f995_701` 60%. `f99_696`, the weakest of the four overall, has a
winning record against the other three, though its 53% and 54% against two of them are within
that noise.

**Of the behaviours the round robin records, trigger use splits the tiers most cleanly.** The top five
fire on 60 to 68% of their decisions, the bottom five on 39 to 43%. Time spent engaged is
close across all ten, 74 to 80%. `followers_513` went from its parent's 42% to 66% in one
night of training, which came with +215 rating points. That is a correlation, and we have not
tested whether firing more is the cause.

**Everyone beats the script overall,** from 82% (`v1`) to 99% (`f995_701`, `f995_400`), but
it holds up better in a convoy, where `v1` wins only 53%. Even there the script has an edge
the nets lack in these matches: it flies its commander's orders while they see none.

## Who follows orders

Only two of the ten pass the order gate, so about one fighter in five on the page is flown
by a pilot that follows its commander. Go-to is how often it arrives where it was sent. Attack and defend are
how often it changes targets when the order changes.

| Pilot | Go-to | Attack | Defend | Gate |
|---|---|---|---|---|
| `transit_300` | 70% | 87% | 100% | Passed |
| `followers_513` | 62% | 88% | 86% | Passed |
| `fighters_506` | 21% | 32% | 36% | Failed |
| `f995_701` | 22% | 14% | 11% | Failed, exempt |
| `hide_644` | 13% | 18% | 18% | Failed |
| `reward_300` | 12% | 12% | 10% | Failed |

`f995_400`, `f99_696` and `w1_400` have not been drilled. `v1` has no inputs for orders.

So the best fighters don't follow and the best followers don't fight, with `followers_513`
the first real step between the two. No pilot in the top tier passes the gate yet.

## What these numbers don't tell you

- **Nobody has been rated in the matches the page now shows.** Every number here comes from
  one pilot flying a whole side with no commander. The page mixes pilots on each side under
  a scripted commander. How the pilots do as mixed teams is unmeasured.
- **Sides are not balanced.** The draw is uniform and per ship, so one side can draw mostly
  `fighters_506` and the other mostly `v1`. Expect some lopsided matches.
- **The memory soak test is close to its bar.** Over 10 minutes the heap grew 10.6% against
  a 10% limit on the first run with ten pilots, and 9.1% on a later run with the ship
  inspector open. One pilot alone grew 7.7% on a run with the same curve, flattening late, so
  we judged it not to be a leak from the extra nets. It should be watched.

The grid's data is `matchups.json`, from `lab/population/2026-11-sim6/round_robin/first-night`
(47,520 matches including the script and `scratch_417`). How the night's training went is in
`lab/runs/2026-11-01-pilot-families/plan.md`.

## What's next

The goal is a top-tier fighter that also follows orders. The next training night is planned
but not yet run: `fighters` continues with more drills, `followers` continues unchanged, and a
second `fighters` line at lower order pay replaces `scratch`. When a new list goes live, it
gets its own entry here.
