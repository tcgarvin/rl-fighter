# Dock and repair: the script docks, the live pilots do not yet

Until now a strike craft (one of the small piloted ships) could launch from its carrier
but never come back. `SIM_VERSION` 11, the eleventh version of the game's rules, lets it
come home. The scripted commander (the hand-written one that gives a side's ships their
orders) sends a craft below half its hull back to its carrier. The craft flies its own
approach, docks through a bay that has not been shot off, repairs in the hangar and
launches again as the same ship. We wanted to know whether the rule works, whether it
upsets the balance of the missions, and whether our trained pilots answer the call.

The rule works for the script, our hand-written rule-based pilot. When the scripts fly
both sides, three recalled craft in five make it home, and nearly every one that survives
the trip docks. A carrier battle (each side has a carrier, and a side wins by destroying
the other's) sees about two docks and two relaunches a side. Who wins barely moves. In
the station assault, where one side defends a space station and the other attacks it
with a carrier and bombers, the attacker wins 0.53 of matches (0.57 under version 10,
the rules before docking). Against the citadel, a much bigger station, the attacker wins
0.59 (v10: 0.58). The live
pilots, the ten trained networks that fly on the website's front page, have never been
asked to dock, and they mostly keep fighting: about 1 recall in 70 ends in a dock, and
the few that reach the bay mostly fly through it too fast. The numbers a pilot reads each
moment now include their own "dock here" signal, so pilots can be trained to it.
Deathmatches (small ships only, last side standing) and convoy escorts (one side guards
freighters, the other attacks them) have no carrier and play exactly as before.

<!-- summary: Damaged fighters can now fly home to their carrier, land, get repaired and launch again as the same ship. When our scripted pilots fly, about three damaged fighters in five make it back, and the other two are shot down on the way. Docking barely changes who wins: the station attack still succeeds about half the time. Our trained pilots have never been asked to land, and almost none of them do: they keep fighting until they are shot down, and the few that reach the bay fly past it too fast. The pilots can now see a separate signal that says "land here" and how the bay is moving, so they can be taught. -->

**Verdict: PARTIAL.** The rule in the sim (the program that runs the game), the
scripted recall, the dock signal in the pilots' inputs and the bindings (the code that
lets Python training scripts and the website drive the sim) are done, and the missions
stay balanced for the script. The live pilots need a docking drill and training (stage 3
of [the plan](plan.md)) before docking means anything on the live page with learned
pilots.

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a neural network
that learned to fly by trial and error. The station assault and the bomber (a slow ship
with a torpedo fixed to its nose) came in
[version 9](../2026-11-19-station-bomber/results.md), the citadel and the dreadnought (a
heavy warship that attacks it) in
[version 10](../2026-11-19-citadel-dreadnought/results.md). Through all those versions a
carrier or station only ever launched craft, and a damaged craft fought on until it was
shot down. On 2026-11-20 the owner noticed this. The project's scripted story demo
already had craft fly back, dock, repair and relaunch, and this entry brings that into
the game. Before any pilot can be taught to come home, the rule itself has to work and
must not tip the missions that had just been balanced. That is what this entry checks.
Retreats and surrender were left out (the owner's call).

<div data-figure="diagram" data-name="missions" data-caption="Docking needs a carrier or a station to land on, so it happens only in the carrier battle and the station assault. In deathmatch and convoy escort the new rule never comes into play."></div>

<!-- figure-idea: shared: the recall loop on one carrier: a craft drops below half hull, the commander recalls it, it flies home, docks, repairs in the hangar at 5% a second and relaunches as the same ship after at least 4 s. Many dock entries could reuse it. -->

## The rules

The rules are in `docs/SIM_SPEC.md` §0.9 (what changed), §5.11 (the rules) and §7.2 (the
pilot's inputs); the design and the numbers are in [the plan](plan.md). In short: the bay
takes a craft in when it is within 10 m of the mouth of any of its carrier's bays that has
not been destroyed and moving at no more than 15 m/s relative to it. In the hangar its
shield is full at once, its hull repairs at 5% a second, and it may launch again after 4
s. If the carrier dies, so does everything in its hangar.

<!-- figure-idea: the dock approach seen from above: the carrier, a bay mouth, the dock point 8 m out, the 10 m capture circle, the 15 m/s speed limit relative to the moving bay, and the script's funnel along the bay axis. It shows at a glance why a pilot that arrives fast flies straight through. -->

**Who recalls.** Only a commander. The scripted commander recalls every own craft below
half its hull, but not one finishing a kill or still under an enemy capital ship's guns,
and relaunches a returned craft at 90% of its hull (half, when it is short of craft). The
random commander (a test commander that gives random orders but keeps the script's
launches) keeps these recalls too. A learned commander has no way to recall yet, so its
craft never come home. The sim recalls nobody on its own. A first version had a
sim-side "recall doctrine" that recalled under every commander, learned ones too. The
owner removed it the same day: docking is to be taught, not stood in for. Under the
scripted commanders, which now make the same recalls themselves, the two versions played
identical matches, so the measurements below hold for either.

**What the pilot sees.** A pilot reads a fixed list of numbers each moment (its own
speed, nearby ships, its orders). A dock order adds five numbers at the end of that list,
which grows from 587 to 592: a "dock" flag, the bay's velocity relative to the ship, and
which way the bay's mouth faces. In the first 587 numbers, which is all a pilot trained
under versions 8 to 10 reads, the order looks like a go-to order (fly to a point) to the
bay's mouth, with a 10 m radius and no deadline. So the live pilots below fly the dock
order as a go-to, which is what they can understand today. Their matches are the same
with and without the new numbers, since they do not read them.

<!-- figure-idea: shared: what a pilot sees and controls: its inputs as a strip of numbers (own state, nearby ships, its order), with the new five dock numbers appended at the end, and its outputs (thrusters, turrets, trigger). -->

**How the tables were measured.** Capital ships are always flown by the sim's scripts,
and both commanders are scripted. Each row from `dock_eval.py` is 512 matches, set up by
seeds (the random numbers that lay out each match) from 1,100,000. ± is the margin of
error, 1.96 standard errors: the true value very likely lies within that range. "Off" is
the same matches with the dock rules off, which is the version 10 game. Code:
`dock_eval.py`, `summary.py`, `run.sh`. The Rust harness, a diagnostic that plays the sim
directly roster by roster, is `crates/sim/tests/dock.rs` (`diag_dock_stats`, 128 starts a
roster, `out/diag_dock_stats.txt`).

## Tuning

The plan started the recall at 30% of hull. In the Rust harness, 86% of recalled craft
were shot down before they reached the bay: by the time a craft is that damaged it is
usually deep in the fight, 300 to 450 m from home and often inside an enemy carrier's or
station's guns. Three changes fixed most of that. The table lists each change and the
reason for it.

| Change | Why |
|---|---|
| Recall at 60% of hull, then 50% | Sent home earlier, a craft has the hull to survive the trip |
| No recall under an enemy capital ship's guns (its longest range plus 40 m) | Turning for home inside a station's flak was the commonest way to die; the craft finishes its run and is recalled once clear |
| The script flies home on engines power, leaves its own carrier out of crash avoidance, and matches the carrier's velocity harder (a pull of 0.8 per second, up from 0.5) | It used to slow down to avoid a collision with its own carrier and never came within 10 m of the mouth |

("Engines power": a ship splits its power between shields, engines and weapons, and a
docking script shifts it to engines and shields. "Crash avoidance" is the script's habit
of steering clear of anything it might hit. The pull is how fast the script corrects the
gap between its own velocity and the carrier's: a bigger number closes it sooner.)

60% gave the most docks (completion, the share of recalls that end in a dock, 0.69, and
3.1 docks a carrier battle) but pulled so many craft out of the fight that the citadel
assault moved to 0.63 for the attacker (v10: 0.58). At 50% it is 0.59, with 0.54 to 0.64
of recalls completed. The capture radius (10 m), the relative speed (15 m/s), the repair
rate and the turnaround stayed at the plan's starting values: a scripted pilot that
survives the trip docks 97 to 100 times in 100 with them, so there was no reason to
loosen them.

One rule came from the live pilots' first run: a commander short of craft relaunched a
returned craft at whatever hull it had, and recalled it again at its first decision out
of the bay (the scripted commander decides every 2 s, on the sim's "slow tick"). The scripted
commander now relaunches a returned craft early only once it is past the recall
threshold.

## 1. Script against script

Each row is a mission played with the script flying every ship. "Team 1 win" is the
share of matches the second team won, with the dock rules off (the v10 game) and on.
Team 1 is the attacker in the convoy, station and citadel rows. A carrier battle is
symmetric, so there team 1 is simply the second side. The deathmatch plays two fixed line-ups that are not mirror
images (one puts two fighters against a strafer and a gunship), so an even 0.5 is not
expected there. What matters in this table is whether each number moves when docking is
turned on. "End reasons" is how the matches with
docking ended: a side eliminated, the clock running out, a carrier or station destroyed,
the convoy through, the attack repelled. The last column is the median match length in
seconds.

| Mission | Team 1 win, dock rules off (v10) | On (v11) | End reasons, on | Median s, off / on |
|---|---|---|---|---|
| Deathmatch | 0.708 ± 0.039 | 0.708 ± 0.039 | eliminated 0.61, clock 0.39 | 42 / 42 |
| Carrier battle | 0.517 ± 0.043 | 0.504 ± 0.043 | carrier 0.87, clock 0.13 | 131 / 132 |
| Convoy escort | 0.002 ± 0.004 | 0.002 ± 0.004 | through 0.75, eliminated 0.24 | 75 / 75 |
| Station assault (attacker) | 0.572 ± 0.043 | 0.527 ± 0.043 | station 0.53, repelled 0.43, clock 0.04 | 103 / 99 |
| Citadel (attacker) | 0.576 ± 0.043 | 0.592 ± 0.043 | station 0.59, repelled 0.31, clock 0.09 | 116 / 118 |

Deathmatch and convoy escort have no carrier, so the dock rules never run: the matches
are identical, down to every bit of the game's state. In the three missions with a
carrier the winner moves by less than two standard errors of the difference, small
enough that chance alone could explain it (the largest, the station assault's −0.045, is 1.5). A few more
matches run to the clock (carrier battle 0.10 to 0.13, citadel 0.05 to 0.09): repaired
craft come back, so a side takes longer to run out of them. The station assault's
attacker, at 0.53, stays inside the 0.45 to 0.6 we aimed for when the mission was built
([station assault and the bomber](../2026-11-19-station-bomber/results.md)).

**Docking, scripted pilots.** "Recalls a match" counts the times a craft was ordered
home in one match. "Completion" is the share of recalls that ended in a dock, as above,
and the next column is that share counting only craft not shot down on the way.

| Mission | Recalls a match | Docked a match | Completion | Of those not shot down | Seconds to dock, median | Relaunches a match | Hull restored a match |
|---|---|---|---|---|---|---|---|
| Carrier battle | 3.57 | 2.16 | 0.61 | 1.00 | 9.5 | 2.16 | 1.29 |
| Station assault | 2.60 | 1.66 | 0.64 | 0.97 | 10.2 | 1.60 | 0.84 |
| Citadel | 2.06 | 1.11 | 0.54 | 0.98 | 7.5 | 1.10 | 0.53 |

"Hull restored" is in whole hulls: a carrier battle gets back about one and a third
strike craft's worth of hull through its hangars. A recalled craft starts 160 to 180 m
from its bay (the citadel's own defenders, which fight near home, 70 m). The ones that do
not make it are shot down soon after the order: half within 3 to 3.7 s, having closed 33
to 57 m of the distance (medians). They were already losing the fight they were in. Of
the few that neither docked nor died, the match ended first; a handful in 512 matches
circled the bay or came in too fast.

## 2. Live pilots, zero-shot

"Zero-shot" means with no training on docking at all. The strike craft are flown by the
ten live pilots (`lab/live_pilots.json`), each ship's pilot drawn at random for each
match, on both sides, under the scripted commanders, which recall them. None has been
trained on a dock order. All read 587 numbers or fewer, so they see a go-to with no
deadline whose point is next to their own carrier. The columns are as in the tables
above.

| Mission | Team 1 win, off | On | Recalls a match | Docked a match | Completion | Of those not shot down |
|---|---|---|---|---|---|---|
| Carrier battle | 0.539 ± 0.043 | 0.508 ± 0.043 | 4.81 | 0.08 | 0.02 | 0.14 |
| Station assault (attacker) | 0.371 ± 0.042 | 0.424 ± 0.043 | 5.00 | 0.07 | 0.01 | 0.20 |
| Citadel (attacker) | 0.268 ± 0.038 | 0.289 ± 0.039 | 3.12 | 0.04 | 0.01 | 0.24 |

**How they fail: two gaps.**

*They do not go home.* Nine recalls in ten end with the pilot shot down, and later than
the script's: half live 7 to 13 s past the order (the script: 3 s), but in that time
they close only 11 to 22 m of the 225 to 285 m to the bay (the script closes 33 to 57 m
in 3 s). They stay in the fight.

*The few that reach the bay fly through it.* The next table follows each recalled craft
from the moment it first comes within 30 m of its dock point. It gives the number that
did, the share of those that then docked, the number that got inside the 10 m capture
circle but never slowed below the bay's 15 m/s, and the median of the slowest speed those
craft reached there, relative to the bay. "Of them docked" is lower than the 0.97 to 1.00
of survivors that dock in the table above, because it also counts craft shot down after
they came near: the citadel's defenders fight close to home, so many are hit right by
the bay (of the citadel's 869 that came near, 569 docked, and of all its 1,054 recalls only 11
ended any other way than docked or shot down).

| Run | Came within 30 m (number) | Of them docked (share) | Inside 10 m but never slow enough (number) | Their slowest there, median |
|---|---|---|---|---|
| Script, carrier battle | 1,287 | 0.86 | 46 | 22 m/s |
| Script, station assault | 1,013 | 0.84 | 65 | 26 m/s |
| Script, citadel | 869 | 0.65 | 65 | 25 m/s |
| Pilots, carrier battle | 248 | 0.16 | 58 | 26 m/s |
| Pilots, station assault | 354 | 0.10 | 85 | 26 m/s |
| Pilots, citadel | 159 | 0.11 | 17 | 37 m/s |

For every pilot that docked, one or two more were inside the bay's 10 m and went through
it at 26 m/s or more (the bay takes 15). The script, which matches the carrier's
velocity, rarely does. A go-to is done once the ship is inside its radius at any speed,
and that is how these pilots fly it. About half the pilots' few docks in a carrier battle
came within a second of the order: craft already at the mouth, defending their carrier.

By pilot (carrier battles): a pilot's name is its training line followed by the training
update (one round of training) it was saved at. `followers_v8_352`, from the followers family (bred to fight
and follow orders) and widened to read go-to deadlines
([pilots v8](../2026-11-12-pilots-v8/results.md)), docks most (16 of 256 recalls; 0.40 of
those not shot down). Next come its child `followers_pay3_810`, paid more for go-to
deadlines in [go-to school](../2026-11-14-goto-school/results.md) (8), and `f99_696` (5).
`f99_696` and the two `f995` pilots are strong fighters that ignore orders, from
[fighters v2](../2026-11-01-fighters-v2/results.md), named for how far ahead they plan.
The two `f995` pilots never docked there. Recalling them changes little else: no mission's winner moves by two
standard errors of the difference (the largest, the station assault's +0.05, is 1.7),
since a recalled pilot keeps fighting. It does take the craft out of its squad (the group
of ships that share one order), so it loses its squad's attack or defend order.

## Was reading the dock order as a go-to a crutch?

Partly, and that is why the pilots' inputs now have their own dock signal.

- **The far part is a go-to.** Flying 200 m home under fire is what a go-to asks. The
  pilots' failure there (staying in the fight) is the weak obedience the drill bars (pass
  marks in the practice scenarios that test order following) already show for go-tos in
  a real fight; no input changes that, drills and pay do.
- **The near part is not.** A go-to ends inside its radius at any speed, and since
  version 8 a go-to can carry a deadline that pays a pilot to get there fast
  ([pilots v8](../2026-11-12-pilots-v8/results.md)). Docking needs the opposite: arrive
  slowly, at the carrier's velocity, from the bay's side. With only the go-to inputs a
  pilot taught to slow down at a dock point would also slow down at go-to points, or have
  to guess "dock" from its carrier being next to the point. And the go-to inputs give the
  point's position, not its velocity. The new numbers give the flag, the bay's velocity
  relative to the ship and the bay's direction, and keep the go-to reading for the older
  pilots.

## What we learned

- **The rule works for a pilot that flies it.** Nearly every scripted craft that
  survives the trip home docks, in 7 to 10 s; a carrier battle sees two docks and two
  relaunches a side.
- **The danger is the trip, not the bay.** Two recalls in five end with the craft shot
  down on the way. Recalling earlier and not under the enemy's guns is what made docking
  worth having; nothing about the bay needed loosening.
- **Docking does not change who wins.** Every mission stays within two standard errors
  of v10; the station assault stays balanced at 0.53 for the attacker.
- **The live pilots ignore the order, and overshoot when they do not.** 1 to 2 recalls
  in 100 end in a dock. They need a docking drill and training on the 592-number inputs
  (stage 3 of the plan) before the live page shows learned pilots docking.
- **Learned commanders never recall.** Until one is trained to (stage 4), a side run by
  a learned commander keeps its damaged craft in the fight.

## Not done here

The docking drill (stage 3) is not built: drills touch the sim's drill rules, the drill
generator, the ledger, the eval and the bars, more than fitted beside this change. No
training was run. The drill and the first training on it came next, in
[the dock pilot run](../2026-11-20-dock-pilot/results.md).
