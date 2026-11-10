# How we train pilots

Status: **agreed plan, 2026-11-01; being built.** Section 1 is what the code did when the
plan was written, read from the code and run configs. Sections 2 to 7 are the plan agreed
with the owner. Section 8 lists what is still open, and section 9 is the build order. Build
items 1 to 3 are written and tested but not yet trained on; sections 2 and 3 say how they
came out.

## The plan in short

- Commanders and pilots train in alternating phases, with the other side frozen.
- About 10 pilots at a time, in families, with the script pilot in the population at first.
- **What an order means is fixed by a drill.** Orders stay human-intelligible. Drills are
  measured and reported; since 2026-11-08 failing them archives nobody.
- Every other match has a commander on both sides or on neither.
- Training matches are the same as live matches.
- A pilot keeps its place by wins above replacement (WAR) in live-like matches.
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
| Each shot fired | -0.002, and -0.002 more in training (below) |
| Outside the arena | -0.002 |
| Match result | +/- 1 |
| Order pay, times `order_reward_weight` (0 in `f995`, 1 in `transit`) | below |

Order pay: attack pays damage to the target. Defend pays damage to the ward's threats, with
penalties for ward damage and death. Go-to pays potential shaping (fixed at discount 0.99
when this was written; it now follows the training discount, section 3) and 0.2 on arrival.

The price of a shot: since night 4 (2026-11-09) every training line pays `extra_fire_cost`
0.002 per shot on top of the sim's 0.002, twice the sim's price, charged by the trainer so
the sim and the browser are unchanged. At 2x, pilots held the trigger less and hit a little
more often at no cost in WAR; a 4x line (`fighters_fire4`) scored 3.8 wins per 100 below
its 2x twin and was retired. **2x is the standing setting** (owner's decision, 2026-11-10;
`lab/runs/2026-11-10-fourth-night`).

Dead ships: since the same night the critic also trains on the learner's rows for ships
that have died or are control-locked (`value_only_rows`, `spacefight/rl/spike_ppo.py`).
Death does not end a ship's episode, so advantages near a death bootstrap from the value
of a dead ship, which the critic had never been trained on (it read from -0.78 to +0.91
across checkpoints; it now reads about 0).

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

Run on fixed seeds, separately from training. **Since 2026-11-08 the gate archives
nobody** (owner's call): `record-drills` still records each pilot's results and verdict,
and they are reported, but a place is earned by WAR (section 5). Before that, a pilot had
to pass to enter and keep passing to stay, the founders `f995_701` and `transit_300`
exempt.

Bars start lenient ("roughly the appropriate way") and tighten as pilots improve. They come
from the outcome, and the script pilot's result is a reference rather than a target.

**First bars, set 2026-11-01** from 256 drills per kind on existing pilots. Each sits well
above the pilots that do not follow and below `transit_300`, the one trained pilot that does:

| Bar | Set at | Script | `transit_300` | `f995_701` | `reward_300` | `hide_644` |
|---|---|---|---|---|---|---|
| Go-to arrival | 0.60 | 1.00 | 0.70 | 0.22 | 0.12 | 0.13 |
| Go-to lift over order hidden | 0.40 | none | 0.59 | 0.07 | 0.01 | 0.01 |
| Attack: any damage on the target | 0.90 | 0.98 | 0.98 | 0.81 | 0.75 | 0.81 |
| Attack: chose the named side | 0.75 | 0.99 | 0.92 | 0.53 | 0.50 | 0.53 |
| Attack: flipped with the order | 0.70 | 0.97 | 0.87 | 0.14 | 0.13 | 0.18 |
| Defend: named attackers took more | 0.85 | 0.99 | 0.98 | 0.57 | 0.54 | 0.64 |
| Defend: chose the named side | 0.85 | 1.00 | 1.00 | 0.49 | 0.50 | 0.56 |
| Defend: flipped with the order | 0.75 | 1.00 | 1.00 | 0.11 | 0.10 | 0.18 |

**Built:** `apply_gate` in `spacefight/eval/drills.py` reads `spacefight/eval/drill_bars.yaml`.
A failed bar fails the pilot. Otherwise any unset bar means `report_only`, stated plainly,
never a pass. `exempt` names pilots it does not judge; the member list that
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

- **Commander means the scripted one unless the run names a stable.** Since 2026-11-08 a
  run can draw learned commanders too (`commander_stable`, below).
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

### Commanders in pilot training: `commander_stable`

Set in the trainer's config (`spacefight/rl/spike_ppo.py`), off by default; unset, every
match keeps its roster's scripted commanders and the roster draws are unchanged.

```bash
--set 'commander_stable=[live]'                          # the live stable, evenly
--set 'commander_stable=[live, random]' --set 'commander_weights=[3, 1]'
```

- **Specs:** `scripted`, `random`, `live` (every commander in `lab/live_commanders.json`,
  the learned ones loaded sha-checked through `tools/live_commanders.py`) or a commander
  checkpoint. A weight per spec, 1 each by default; a `live` weight is split evenly over
  its commanders.
- **Who draws:** each side of a match that is not a drill and shows its orders draws its
  commander per episode, independently per side, as the live page does
  (`spacefight/commander/stable.py`, `StableSampler`, with its own seed, so the rosters
  are the ones drawn without a stable). In `pilots_v1` that is the commander half of
  `commander_p`. A no-commander match keeps the script underneath, which runs the
  logistics. **Drills are left alone:** their orders come from `external` commanders
  queued when the drill is built, not from any commander that could be learned.
- **Decisions:** before every env step the trainer runs the due decisions of the learned
  ones (`spacefight/commander/decide.py`, `decide_learned`, shared with the commander
  eval): no gradient, CPU, one batch per network per team, 1 Hz per team. A learned
  commander also flies its own launches and carrier, and in a deathmatch, unlike the
  script's, its orders are followed by script pilots, so those rows count as ordered.
- **Logs:** `commander_decisions`, `commander_share` (share of match sides),
  `episodes_by_commander`, `win_by_commander` and `win_by_enemy_commander` (the learner's
  side, draws half), keyed by commander id, `no_commander` for hidden orders. They are
  logged without a stable too (`scripted`, `no_commander`).
- **Cost:** at 32 envs and 2 threads (machine shared with a 14-thread eval), rollout time
  per 128-step update went from 1.71 s to 1.80 s at `commander_p` 0.5 and from 1.67 s to
  1.94 s at 1.0, about 1.4 ms per decision, mostly network overhead on batches of one or
  two.

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

**Wins above replacement (WAR), from 2026-11-08.** The owner prefers performance in real
scenarios on random teams to the all-pairs round robin, so a pilot is judged by what its
ships add to whatever team it lands on, in matches like the live page's.

Reported but not judged: drills (section 2), following in real matches, and the round
robin's combat rating (Bradley-Terry, below), which still runs.

### WAR

`spacefight/population/war.py` (fit, pure numpy), `war_matches.py` (matches), JSON
`rlf.population.war/1` with every match and the fit, and a phone table beside it.

- **Matches** are the live page's, through the commander eval's `play_matches`: live
  rosters (deathmatch: 24 live drafts), orders shown, capital ships by script. Each
  strike craft's pilot is drawn uniformly from the candidates **plus the script**, the
  one difference from live, and each side's commander uniformly from the stable
  (`lab/live_commanders.json` by default).
- **Model:** ridge logistic regression, as basketball's RAPM. Team 0 wins (a draw is two
  half-weight rows) on, per pilot, ships flown for team 0 minus for team 1, plus a side
  term per roster and a commander term per commander and mission (against `scripted`).
  The script has no column: it is replacement, 0 by definition.
- **Ridge:** a fixed prior, 1 logit per ship on pilots and 3 on the nuisance terms.
  Pilots are drawn at random, so the design is near orthogonal; the prior only keeps a
  small, separated sample finite. `prior_weight` in the JSON shows how little it moves a
  real fit (under 1 % at 1,000 matches a mission).
- **WAR** of a pilot: over the matches it flew in, the model's win probability for its
  side minus the same with its ships flown by the script, per 100 of those matches. A
  draw counts half. Also reported: per-ship coefficient, matches and ships flown, WAR
  per mission.
- **Interval:** 95 % percentile bootstrap, 500 refits, matches resampled within mission.
- **Read it within one measurement.** WAR per 100 matches grows with the ships a pilot
  flies per match, which falls as the pool grows. The per-ship coefficient travels better.

**Size.** Synthetic matches with live ship counts give a 95 % half-width of about ±6.4
wins at 240 matches a mission, ±4.8 at 480, ±3.8 at 960, ±3.0 at 1,440, nearly the same
for 10 or 14 pilots. Speed: about 1.2 matches a second over the mix at 8 threads (the
commander eval's smoke at 48 a mission), so 1,440 a mission is roughly an hour. Each
chunk prints its rate.

**Combat rating (round robin).** Matches with no commander on either side, on live
rosters, all pairs. Kept as a report.

## 6. Culling and the family tree

**Shadow mode first.** For the first few phases nothing is culled. Every phase records who
would have been, and the owner reviews it before the rule goes live.

**WAR rule (from 2026-11-08), `war_shadow_cull`:**

1. Below replacement: a member whose whole WAR interval is below 0 would go. The script
   never; it is replacement.
2. Founder cap, kept: over 4 survivors from one founder, its lowest WAR would go.
3. Over the cap of 10 learned members: the lowest WAR would go, but never the last of a
   family. That protection replaces the diversity bonus, which would mix made-up points
   into wins. The script's drill rule goes too: WAR has no use for it.

Close calls are flagged as before: a gap within the two pilots' bootstrap sds.

Round-robin rule, still reported with `report --results`:

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

`f995_701` stays the champion until a member passes the drill gate and beats it in combat,
or the owner waives that.

**On the live page (owner's call, 2026-11-02):** each strike craft flies one of up to 10
pilots, drawn at random for each ship: the highest-rated members who are not the script,
listed in `lab/live_pilots.json`. Archived members can fly there, and a pilot need not pass
the drill gate. The list changes only when `tools.live_pilots publish` is run, so a new
rating alone deploys nothing. `publish --war <war.json>` picks by WAR instead (not the
default yet); `rating` then holds WAR per 100, and the page's inspector still says
"Rated".

## 8. Still open

1. One network that both fights and follows, or separate skill networks. Working default:
   one network, with the fallback in section 4.
2. How much combat a follower may give up to get in. Today the gate has no combat floor.
3. Where the owner reviews the tree and shadow culls. Default: a phone-friendly page.
4. Runs are started by hand at first. Nightly automation comes later.

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

All 8 items are done. The first night's results and the next night's plan are in
`lab/runs/2026-11-01-pilot-families/plan.md`, and the population's state is in
`lab/population/2026-11-sim6/report.md`. Weighted sampling runs on live results but logs no win
rates yet, and `pool_seed` is still filled by hand.

The tools are in `spacefight/population/`, with records in
`lab/population/2026-11-sim6/`. The rating is Bradley-Terry, and the cull constants are
guesses to be judged in shadow mode. The round robin rates deathmatch on the live page's
drafts.

**Script pilots in no-commander matches.** Hidden orders only change what a pilot sees, so
in carrier and convoy the script still flies the commander's orders. Read its mission
results with that in mind.

Commander training starts once a pilot passes the drill gate.
