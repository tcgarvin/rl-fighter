# Third commander phase: are orders worth more than no orders?

Prepared 2026-11-15 with the owner's go-ahead for a commander round. The design is
`docs/COMMANDER.md`; the page is `/commander/`.

## Why now

Two nights of go-to school gave us pilots that follow orders: `followers_school_1052`
changes sides with an attack or defend order more than nine times in ten. The last
commander phase ended on "orders do not matter to who wins, because most pilots do not
follow them". So the plan was to train commanders over pilots that do follow, with the
live ten as the control.

Before training we measured what the commanders we have are worth over each pilot list.
That changed the plan.

## What we measured before training

Every strike craft on both sides is drawn ship by ship from one list: the live ten, or
the four best followers (`pilots_followers.json`: `followers_school_1052`,
`followers_school_600`, `followers_solo_1072`, `followers_pay3_810`). 1,152 matches a
row, 384 a mission, the same seeds for every row. Each score is good to about ±0.03.

A new side, **unseen**: the scripted commander with its orders hidden from its own
pilots. It launches as the script does and its pilots fly as if nobody commanded them. It
is the side with no orders.

Score against the scripted commander:

| Side | Over the followers | Over the live ten |
|---|---|---|
| No orders (unseen) | 0.75 | 0.69 |
| `price5` (last phase's best) | 0.62 | 0.58 |
| `hold` (last phase) | 0.62 | 0.58 |
| `c1_shaped` (on the live page) | 0.59 | 0.56 |
| Random orders | 0.59 | 0.58 |

Score against the side with no orders:

| Side | Over the followers | Over the live ten |
|---|---|---|
| Scripted commander | 0.25 | 0.31 |
| Random orders | 0.33 | 0.38 |
| `price5` | 0.34 | 0.41 |

- **Every commander we have makes its side worse than no commander.** The script most of
  all. In the carrier battle over the followers, pilots with no orders beat pilots under
  the scripted commander 0.87 to 0.13.
- **The better the pilots follow, the more the orders cost.** That is the plan's premise
  the other way up: orders do matter over followers, and all the ones we give are bad.
- **The learned commanders learned to order less, not to order well.** They keep a ship
  under an order 42 to 52% of the time, random orders 62%, the script 99%, and the less
  a side orders the better it does. `price5` against random orders directly is 0.52.
- This also explains last phase's oddity, random orders beating the script 0.60 to 0.40.

The data: `eval_before/` (`before.sh` runs it again).

## Where the cost is

A second look the same afternoon, the scripted commander's side against the same pilots
with no orders (`order_cost.py`, outputs in `order_cost/`).

**It is not about obedience as the drills measure it.** A third pilot list,
`pilots_ignorers.json`: three pilots of the `fighters_pay1` line, which change sides with
an attack or defend order two or three times in ten. No orders beats the script by the
same margin over them as over the followers: 0.75 overall, 0.87 in the carrier battle.

**It grows with the size of the fleet.** Even deathmatches, the ordered side's score. In
deathmatch every order the script gives is an attack order.

| Ships a side | Followers | Ignorers | Matches |
|---|---|---|---|
| 1 v 1 | 0.46 | 0.48 | 1,536 |
| 2 v 2 | 0.35 | 0.30 | 1,536 |
| 3 v 3 (live drafts) | 0.23 | 0.24 | 512 |
| 4 v 4 (live drafts) | 0.11 | 0.17 | 64 |

- With one ship a side the order can only name the one enemy there is, and being ordered
  costs little: three or four points in a hundred.
- With two or more a side the order chooses the target, and the ordered side loses badly.
  So most of the cost is the target the script picks, and every pilot we tried goes for
  it enough to matter, the "ignorers" included.
- **The ordered side loses its ships early.** In the first 30 seconds of a deathmatch it
  loses 1.07 ships a match and the side with no orders 0.76. In the convoy escort 2.7
  against 1.1; in the carrier battle 1.5 against 0.7, and 3.9 against 2.5 in the next 30.

Not yet known: what the ordered pilot does in those seconds that the free one does not.
The script sends half a fleet at the enemy nearest it and the other half at the most
damaged enemy. Our guess is that a pilot sent after one enemy stops dealing with the
others.

## What changed (2026-11-15)

- **The eval has an `unseen` side** and takes a pilot list (`--pilots`).
- **The trainer has an unseen enemy**: a fifth entry in `opponent_shares`. A config with
  four shares means none of it, so nothing trained before changes.
- `TrainConfig.live_pilots` already named the pilots; it now has a second list to name.
- No rule of the game changed. `SIM_VERSION` stays 8 and `COMMANDER_IO_VERSION` 1.

## The question tonight

Can a commander find orders that are worth more than no orders? A learned commander can
choose "no order" for every squad, so against the unseen side it can always reach about
0.50 by staying quiet. Anything above that is orders that help.

## Arms

Three fresh commanders, last phase's sizes (128 matches at once, 8,192 decisions an
update), the 5-second hold, no price on orders, the same seed.

Every arm meets the same enemies: the unseen side in half its matches, itself in a
quarter and its own earlier snapshots in a quarter. No matches against the script or
random orders: beating them teaches only "order less".

| Arm | Pilots | Entropy bonus |
|---|---|---|
| `followers` | the four followers | 0.002 |
| `followers_ent01` | the four followers | 0.01, as in both earlier phases |
| `live` | the live ten | 0.002 |

- `followers` is the main line.
- `live` against it: does it matter that the pilots follow? If good orders exist, the
  followers should show them first. If the only lesson is "be quiet", the two should end
  the same.
- `followers_ent01` against it: last phase, the entropy bonus pushed order choices toward
  even odds all night (the order head's entropy rose from 3.2 to 4.4, and the share of
  choices that changed an order from 0.26 to 0.53) while the win rate barely moved. If
  that bonus is what kept commanders ordering, this arm stays noisy and the other two
  go quiet.

## What the morning reads

`morning.sh`, the same seeds and sizes as the table above.

1. **Each arm against the unseen side over its own pilots.** Before: `price5` 0.34 over
   the followers, 0.41 over the live ten. About 0.50 is a commander that learned to stay
   out of the way. Clearly above 0.50 is the result we want.
2. **How much each arm orders** (time under an order; `price5` 45%) and what it orders, by
   kind, from the training log. A score near 0.50 with almost no orders is a quiet
   commander. Near 0.50 with orders would be more interesting.
3. Each arm against random orders and the script, for the line back to earlier phases.
4. Each arm against the unseen side over the other pilot list, and `followers` against
   each of the other two.
5. `win_unseen` through the night in `log.jsonl`.

## What goes live

Set before the run. A line joins the stable if, over the live ten, it is not behind the
unseen side by more than noise (0.47 or better). The unseen side beats the script 0.69 to
0.31 there, so such a line is well ahead of everything in the stable now. If it gives
almost no orders (under 10% of ship time), the entry says so plainly and it is the
owner's call whether a commander that commands nothing belongs on the page.

## Running it

- `launch_when_idle.sh` waits for midnight and for the owner to be away, runs `run.sh`
  until 07:00 and then `morning.sh` at the lowest priority (15 evals, about two and a
  half hours; the three that matter most come first).
- Rehearsed 2026-11-15 with `SMOKE=1`: three updates an arm, then the morning at 48
  matches a mission.
- About 35 updates an hour last phase, so about 250 updates an arm by 07:00. Last phase
  ran 415.

## Not tonight

- Deadlines on go-to orders. No commander gives one yet; first a commander has to give
  any order worth following.
- What an ordered pilot does wrong in the first 30 seconds (above). It matters beyond
  commanders: the script commands sides in pilot training, and the live stable (the
  script and three commanders that all lose to no orders) commands the matches that rate
  pilots.
