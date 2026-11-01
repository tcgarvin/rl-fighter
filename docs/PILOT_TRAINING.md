# How we train pilots

Status: **agreed plan, 2026-11-01; being built.** Section 1 is what the code did when the
plan was written, read from the code and run configs. Sections 2 to 7 are the plan agreed
with the owner. Section 8 lists what is still open, and section 9 is the build order. Build
items 1 to 3 are written and tested but not yet trained on; sections 2 and 3 say how they
came out.

## The plan in short

- Commanders and pilots train in alternating phases, with the other side frozen.
- About 10 pilots at a time, in families, with the script pilot in the population at first.
- **What an order means is fixed by a drill.** Orders stay human-intelligible, and a pilot
  must keep passing the drills to keep its place.
- Every other match has a commander on both sides or on neither.
- Training matches are the same as live matches.
- Culling is watched in shadow mode before it is trusted.

## 1. Scenarios today

Run `f995` (`lab/runs/2026-11-01-fighters-v2/f995/config.yaml`), preset `orders_v1`
(`spacefight/env/rosters.py`). Each env draws a new match when its last one ends.

| Choice | Draw |
|---|---|
| Mission | deathmatch 0.4, carrier battle 0.3, convoy 0.3 |
| Commander, per team independently | random 0.5, scripted 0.5 |
| Learner's team | random per episode, so both convoy sides get played |
| Enemy pilots | script 0.2, learner itself 0.4, frozen pool 0.4 |
| Frozen pool | half from 3 fixed older pilots, half from this run's checkpoints, even within each |

- **Rosters.** Deathmatch: `fleet_v1`, 1 to 4 ships a side. Carrier: 4 to 5 strike craft
  a side. Convoy: 3 to 4 freighters and 2 to 3 escorts against 4 to 5 attackers.
- **Capital ships** are always flown by the sim's scripts.
- **Logistics are always scripted.** Launches and capital-ship waypoints come from the
  script under both commanders.

Pay per ship (`crates/sim/src/reward.rs`):

| Term | Amount |
|---|---|
| Hull damage dealt / taken | +/- 0.01 per point |
| Shield damage dealt / taken | +/- 0.005 per point |
| Each shot fired | -0.002 |
| Outside the arena | -0.002 |
| Match result | +/- 1 |
| Order pay, times `order_reward_weight` (0 in `f995`, 1 in `transit`) | below |

Order pay: attack pays damage to the target. Defend pays damage to the ward's threats, with
penalties for ward damage and death. Go-to pays potential shaping (fixed at discount 0.99
when this was written; it now follows the training discount, section 3) and 0.2 on arrival.

What changes under this plan: training rosters stop at 12 ships and are smaller than live;
teams draw commanders independently; random orders go; there are no drills.

## 2. Order drills

**The purpose is to keep the meaning of each order clear.** A drill checks that a pilot
understands what it was told, not how well it does it. How to carry out an order is left
to training: taking a pass at enemies on the way to a point is fine, and a commander and
pilots may come to rely on subtleties like that. A pass condition should fail only a pilot
that didn't do what was asked.

| Order | Setup | Pass condition | Not judged |
|---|---|---|---|
| Go-to | A near or far point, sometimes with enemies around | Gets there by the deadline: straight-line time at the hull's speed cap, plus generous slack | The route, or fighting on the way |
| Attack | Enemy groups on opposite sides, one target named | Damage lands on the named target, and the pilot goes for its side | Hits on other enemies, which are never penalised |
| Defend | Two friendly ships under attack on opposite sides, one named | The pilot goes to the named ship and hits its attackers more than the other's | Whether the ward survives |

- **The swap test is the core check for attack and defend.** Same start, name the other
  side, and the pilot's choice should flip. This separates a pilot that understood the
  order from a smart one that would have done the same thing anyway, which a survival
  comparison can't do.
- **Go-to** also runs with orders hidden on the same seeds, as the baseline.
- **Variety lives here.** Target, distance, hull and squad size vary widely, including
  distances the scripted commander never uses. This replaces random orders as the
  protection against overfitting to one commander.
- **Pay:** the same as in matches, damage and shot cost included, plus order pay, without
  the match result. A hit on another enemy pays what it always does, so nothing teaches
  a pilot not to shoot. Named-target hits simply pay more.
- **Enemies** are script pilots.

### What was built

Scenarios are `spacefight/env/drills.py`, `DrillGenerator.generate(kind, seed)`, pure and
seeded. The sim gained start layouts and drill rules (`MatchConfig.start_layout`, `.drill`;
SIM_SPEC §5.10). No physics changed, the goldens hold and `SIM_VERSION` is still 6.

- **Mission: a deathmatch under drill rules, with `external` commanders on both teams.**
  The pilot obs carries the mission as a one-hot, so a new mission would have told pilots
  they were in a drill. Script followers do follow an `external` commander in a deathmatch;
  only the scripted commander's orders are advisory there. Drill rules have no winner, so
  **no match result is paid, by construction**: the sim ends a drill as a draw. It ends on
  the clock, when team 0 has no strike craft left, or when team 1 is gone and no go-to is
  open, so killing every enemy on the way does not cut a go-to short.
- **Wards are freighters.** A capital hull is never a learner row, and the transport
  script coasts with no waypoint, in any mission, so it needs nothing but a start. They do
  not fire back, which keeps "who hit the attackers" about the pilots.
- **Under attack is real, and the groups stay apart.** Each side's enemy group has an
  `external` attack order on its own side's freighter. A test shows every ward damaged,
  with its group in its threat set, while the pilots do nothing. The freighters last: with
  the script flying the pilots, 83 % of wards outlived the 30 s clock in 64 defend drills,
  and the earliest loss in 64 attack and 64 defend drills was at about 10 s, to two gunships.
- **Attack drills use the same layout**, one enemy named in one group. A quarter have no
  freighters, and their groups fly straight at the pilots (`charging`), so attack is not
  only ever on a busy target. Those groups do not stay apart; the eval reports them
  separately.
- **Sides are out of gun range from the start:** 240 to 320 m away, each side's distance
  drawn on its own, so a pilot that just takes the nearer side fails the swap test.
- **Variety:** hull mix, squad size 1 to 4, go-to distance about 45 to 690 m to the arrival
  circle, radius 15 to 80 m, start speed and heading. The whole layout gets a random
  rotation and, half the time, a mirror, so the named side is not fixed in the world or in
  the pilot's frame. Go-to enemies start beside the route half the time, else across the
  arena from it.
- **Deadline:** from the order, the ship's straight-line time at its speed cap, doubled,
  plus 10 s. Each ship has its own.
- **Orders are queued once, when a match is built** (`Roster.opening_orders`, in
  `RustVecEnv`), and the sim applies them on the first slow tick (tick 60). That is simpler
  than issuing them on slow ticks, and there is no per-env Python on a step. Standing orders
  need no repeat.
- **Nobody flies blind.** Drill rules hold every ship under a control lock until the order
  lands, so they coast for the first 2 s. Without it the script drifted toward its nearest
  enemy before it had an order, and momentum alone scored as choosing the wrong side (the
  script's flip rate on a small sample went from 0.69 to 0.94 on attack).

**Where it differs from the plan above:**

- Go-to pay and the deadline agree, but the eval does not count a ship killed before its
  deadline as a failure, since fighting on the way is allowed. Such ships are *censored*, and
  the report gives their count, so a squad that keeps dying on the way still shows.
- The side chosen comes from where the pilots go, not from damage: the first time a pilot is
  80 m along the line between the sides from where it was when the order landed. The squad's
  choice is the side most committed pilots took. It does not depend on where enemies fly.
- A swap test "flip" means the squad chose the named side both times, not only that the
  choice changed. `same_side` reports the pilot who picks one side whatever it is told.
- **Pay:** order pay in a defend drill still includes the ward-loss penalties, as in a match.
  They are paid but not judged: the eval never looks at whether a ward survived.

### Drills in training

`drill_share` and `drill_weights` in `pilots_v1` (`roster_overrides`, default 0, and at 0 no
extra number is drawn, so the draws are unchanged). A family's `commander_p` splits what is
left after drills, so the Fighters row of section 4 is `drill_share: 0.1, commander_p: 0.333`.

- A drill env's enemies are the script and the learner is team 0, the ordered team. It is
  held out of the opponent quota (`OpponentAssigner.force_scripted`), so the band shares
  still describe matches.
- A run with drills must pay for orders: the config refuses `order_reward_weight` 0, and
  refuses `hide_damage_when_ordered`, which would teach a pilot not to shoot.
- Logs: `drill_rows_share`, `drill_episodes` and `drill_success` per kind. Success in the log
  is a running signal: go-to, ships arrived; attack, any damage on the target; defend, the
  named ward's attackers took more. Side and swap need the eval. Drills are not in the
  episode tallies, so a draw in a drill does not touch `vs_scripted_*`.

### Drill eval

`spacefight/eval/drills.py`, JSON `rlf.eval.drills/1` and a plain report beside it. Fixed
seeds, separate from training. The script gets no hidden pass, since it flies orders it
cannot see. Standard errors treat ships of one squad as independent for go-to, so they are a
little small there. Attack and defend are per drill.

### Obeying only in drills: what a pilot can see

A drill is not disguised beyond its mission one-hot. A pilot could tell a drill from a match
by its start (no jump-in), its control lock, or a defend of a freighter under a deathmatch
one-hot. This stays the owner's call below.

### Drill gate

Run on fixed seeds, separately from training. A new pilot must pass to enter the population
and must keep passing to stay. Failing archives it with the reason. The founders
`f995_701` and `transit_300` are exempt, but their children are not.

Bars start lenient ("roughly the appropriate way") and tighten as pilots improve. They come
from the outcome, and the script pilot's result is a reference rather than a target.
Numbers get set after measuring the script and the founders on the real drills.

**Built:** `apply_gate` in `spacefight/eval/drills.py` reads `spacefight/eval/drill_bars.yaml`,
all unset today. A failed bar fails the pilot. Otherwise any unset bar means `report_only`,
stated plainly, never a pass. `exempt` names pilots it does not judge; the member list that
decides that comes in a later package.

### Obeying only in drills

The owner's call: we don't defend against this now, and we deal with it if it shows up.
The existing order eval (`spacefight/eval/orders.py`) keeps running on real matches as a
plain report, which is how we would see it. It is not part of the gate.

## 3. Match scenarios

Live rosters only. Both sides have the same condition in every match:

| Condition | What pilots see | Who does logistics |
|---|---|---|
| Commander, both sides | The commander's orders | Commander |
| No commander, both sides | No orders (`hide_orders`) | Script |

- **Commander means scripted for now.** Learned commanders join the mix once they exist.
- **Carrier and convoy special case.** With no commander, the script still launches and
  moves capital ships, because the mission cannot run otherwise. Agreed with the owner.
- **Random orders are out of matches.** They add noise for little value now that drills
  cover the variety. If ever used, both sides get them.
- **Enemies** come from the population, weighted toward those that beat the learner, with
  a floor so none drop out.

**Why both sides:** it keeps ratings fair, because neither side carries a handicap the
other lacks. It does not remove the temptation to ignore orders: a pilot who ignores orders
can still beat an obedient enemy, and team reward will pay it. That is why order pay stays
on in these matches and the drill gate exists.

**Pay in matches:** team reward, plus order pay whenever an order is shown. No script pull
and no KL anchor.

**Order pay's shaping discount must follow the training discount first.** Go-to pay is
`γΦ′ − Φ` with γ hard-coded to 0.99 (`ORDER_SHAPING_GAMMA`). At a training discount of
0.995 that pays a pilot to stay away. In a simple model of straight flight at 60 m/s, 225
m from the point, the discounted pay is +0.73 to fly there and +1.00 to stay put; with the
discounts matched it is +0.61 and +0.50. No past run hit this: `f995` had order pay off,
and runs with order pay trained at 0.99.

**Built:** `MatchConfig.order_shaping_gamma` (default 0.99), set for a whole env by
`RustVecEnv(order_shaping_gamma=...)`, and the trainer passes its `gamma`. A resumed
config keeps its own discount; at 0.99 the pay is exactly what it was. `f995`'s config
(0.995, order pay off) would log a different `reward_order` if resumed but train the same.

### Preset `pilots_v1`

`spacefight/env/rosters.py`; `orders_v1` still works, so old configs resume. Per match:

| Choice | Draw |
|---|---|
| Mission | `mission_weights`, default deathmatch 0.4, carrier 0.3, convoy 0.3 |
| Carrier, convoy | `rlf_sim.mission_rosters` at run time: the first 0.5, the others evenly, as the page |
| Deathmatch | The page's draft: 2 to 4 of the cheapest hull's worth of credits, the same budget a side, each side spending it independently |
| Condition | `commander_p`, default 0.5: both teams' orders shown, else hidden from both |

A family sets its own share with `roster_overrides`, e.g. `commander_p: 0.3`.
`tests/test_pilots_rosters.py` runs the page's own `missionRoster` in Node and compares its
draws with the sampler's.

Where training still differs from the page:

- **Mission mix.** The page rotates through the three evenly; training defaults to 0.4,
  0.3, 0.3.
- **Hidden orders.** The page always shows orders; half of training hides them, by design.
- **Uncertified hulls.** The page swaps a mission roster's strike craft that the champion
  is not certified to fly. Training does not, which matters only if a champion is ever
  certified for fewer than the three strike hulls.
- **Budget.** The sampler uses the bundle's default budget. A bundle built with
  `RLF_ROSTER_BUDGET` set lower would draft smaller sides than training does.

How the plan's words came out in code:

- **Order pay only when shown.** The sim pays `order_rewards` whatever the obs shows, so
  the trainer drops it on hidden rows (`RustVecEnv.order_hidden_rows`). The logged
  `reward_order` is what was paid. Hidden rows also get no transit pull.
- **"No commander" still has a commander underneath.** Hidden orders change what pilots
  see, not what scripts do. In a carrier battle or a convoy, *script-flown strike craft*
  keep flying the scripted commander's orders, so an enemy script pilot in a no-commander
  match still follows orders that a learned pilot cannot see. Deathmatch orders are
  advisory, so scripts ignore them there anyway.
- **Slots.** Every match pads to 20, the biggest live roster, so a rollout's obs buffer at
  256 envs is about 2.0 GB against 1.2 GB at 12 slots.
- **Speed.** Sim alone, on a shared machine (64 envs, 4 threads, random actions): 876
  steps/s against 1,691 for the 12-slot carrier and 1,938 for the 12-slot convoy. That is
  a first number; measure again on a free machine before planning a night around it.

## 4. Families

Every neural pilot descends from the script: v1 began as a clone of it (BC, DAgger, then
PPO). So today's tree has one root, and only a from-scratch family is truly unrelated.

Shares of training, as a starting point:

| Family | Founder | Why | Drills | Commander | No commander | Order pay |
|---|---|---|---|---|---|---|
| Script | Script pilot | Yardstick, and it follows. Cannot have children | Does not train | | | |
| Fighters | `f995_701` | Best fighter, follows nothing | 0.10 | 0.30 | 0.60 | 1 and 3 |
| Followers | `transit_300` | Best neural follower, weak fighter. Its script pull stops here | 0.25 | 0.50 | 0.25 | 1 and 3 |
| Scratch | None | Only unrelated line. Long shot, kept for diversity | 0.10 | 0.30 | 0.60 | 1 |

Founder numbers on the existing order eval (attack share, threat share, go-to arrival;
deathmatch vs script): `transit_300` 0.51, 0.58, 0.66; 0.74. `f995_701` 0.31, 0.29, 0.48;
0.90. Script, for following: 0.47, 0.65, 0.90.

**Reaching about 10:** 3 learners a night at about 700 updates each at today's speed.
Live-sized matches will slow that by an amount not yet measured. Script, `f995_701`, plus 9
trained members is 11 after 3 nights. Night 1 trains one member of each family. If Scratch
can't beat the script in deathmatch by morning, its slot goes to another family.

**First question the population answers:** can a small share of drills give `f995_701`'s
children following while they keep their combat? If not, raise the share, and if that
fails, fall back to separate skill networks.

## 5. What earns a place

1. **Drill gate:** pass or out (section 2).
2. **Combat rating:** matches with no commander on either side, on live rosters.

Reported but not rated: following in real matches, and win rate with a commander on both
sides. The script pilot stays until it is the worst on combat, as long as another pilot
has matched its drill results.

## 6. Culling and the family tree

**Shadow mode first.** For the first few phases nothing is culled. Every phase records who
would have been, and the owner reviews it before the rule goes live.

Rule to test in shadow mode:

- Bottom 2 on combat are candidates.
- Diversity bonus: rating rises with tree distance to the nearest member of the top 10,
  up to a cap. The bonus affects survival only, never enemy sampling or deployment.
- A cap of 4 of 10 from one founder is the fallback if the bonus is not enough.

This is close to explicit fitness sharing in NEAT (Stanley & Miikkulainen 2002), where
relatives share fitness so that one species cannot take over.

Tree distance and behaviour can disagree: cousins may fly alike and strangers may
converge. Shadow mode also logs behaviour distance (fire rate, engagement range, engine
duty) to check whether the tree is a good proxy.

**Archive:** nothing is deleted. Retired members stay on disk with their records and may
return as occasional opponents. A record holds founder, parent, fork update, settings
changed, drill results and combat rating over time.

## 7. Changing the game while a population lives

Changes cost more with 10 pilots. Group the expensive ones and make them between
populations (DESIGN calls these seasons).

| Change | Cost |
|---|---|
| Observations, physics, or what an order means | Every pilot is stale. Retrain all, or widen inputs and fine-tune all |
| Hull stats | Pilots still run, but all need fine-tuning and re-rating |
| Rosters, mission rules | Pilots still run, re-rate all |
| Website, art, commander overlay | None |

Do first, before the first population: live rosters in training and the drills. Both
change what the first 10 pilots learn.

`f995_701` stays live until a member passes the drill gate and beats it in combat, or the
owner waives that. Population ratings do not deploy anything.

## 8. Still open

1. One network that both fights and follows, or separate skill networks. Working default:
   one network, with the fallback in section 4.
2. Drill bars, set once the script and founders have been measured.
3. How much combat a follower may give up to get in. Today the gate has no combat floor.
4. Where the owner reviews the tree and shadow culls. Default: a phone-friendly page.
5. Runs are started by hand at first. Nightly automation comes later.

## 9. Build order

Code can be written while the owner uses the machine. Training and big evals wait until
the owner says the machine is free.

| # | Work | Needs the machine? |
|---|---|---|
| 1 | Order pay's shaping discount follows the training discount | No |
| 2 | Live rosters and both-sides commander conditions in training (`pilots_v1`) | Benchmark only |
| 3 | Sim start positions, drill scenarios, drills in training, drill gate (built) | No |
| 4 | Population records, family tree, round robin, combat rating, shadow culling | No |
| 5 | Weighted enemy sampling from the population | No |
| 6 | Measure the script and founders on the drills, then set the bars | Yes |
| 7 | Run the round robin across existing pilots | Yes |
| 8 | First night: one member of each of Fighters, Followers and Scratch | Yes |

Commander training starts once a pilot passes the drill gate.
