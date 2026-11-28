# Station assault and the bomber: balanced for the script, not yet for the pilots

We added a new mission, the station assault, in which one side defends a fixed space
station and the other attacks it, and a new ship to attack it with. `SIM_VERSION` 9 (the
ninth version of the game's rules) adds the mission and two hulls (ship types): the
`station`, a static capital ship (one of the big ships, which scripts fly) with six
turrets and two launch bays, and the `bomber`, a slow strike craft (one of the small
piloted ships) with a torpedo rack fixed to its nose, so it aims by pointing the whole
ship. The first
question was whether the mission is fair. When the scripts (our hand-written pilots) fly
both sides, the attacker wins 0.55 of its assaults and almost no match runs to the
clock, the balance we aimed for. The second was whether our trained pilots can play it
without any training on it. They can, but the attacker wins less often with them (0.36
to 0.39), because they barely fire the bomber's torpedo. Put in a bomber instead of a
gunship, a learned pilot does worse in every test, and so does the script in every
mission we tested other than the station assault. The scripted commander's orders cost learned pilots this mission on
both sides, as they do in fleet fights.

<!-- summary: We added a new mission, a station assault, and a new ship, the bomber, which carries a torpedo fixed to its nose. With scripted pilots on both sides the attackers win about half the time, which is the balance we aimed for. Our trained pilots can already play the new mission, but they hardly ever fire the bomber's torpedo. A bomber flown by a trained pilot does much worse than the gunship it replaces, so pilots will need training with it before it appears on the live page. -->

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a neural network
(a pilot) that learned by trial and error, and each side has a commander that gives its
ships orders. The strike craft are the fighter and strafer, whose guns are fixed to the
nose so they must point at a target to shoot, and the gunship, slower, with turrets that
aim on their own. Until this night there were three missions: team deathmatch (small
ships only, last side standing), and two added in [the mission
survey](../2026-10-30-mission-survey/results.md): the carrier battle, where each side's
carrier launches its strike craft and a side wins by destroying the enemy carrier, and
the convoy escort, where one side's escorts guard freighters flying to a jump point and
the other side attacks them. In fleet fights, commanders had found
nothing to gain by ordering pilots about: a side with no orders beat every commander
([commander 3](../2026-11-15-commander-3/results.md)), because an ordered pilot charges
its target and loses the duel ([the order-cost
night](../2026-11-17-order-cost/results.md)). On 2026-11-18 the owner asked for [new
directions](../2026-11-19-new-directions/results.md): a base assault or piracy mission
with more for a commander to decide, and one to three new ship types. This entry builds
the base assault and the bomber and checks two things before anyone trains on them: is
the mission balanced, and can today's pilots fly it?

## The mission

<!-- figure-idea: shared: the station assault laid out: the station with its picket and bays on the defender's side, the attacking carrier and its jump-in craft arriving from the far side, bombers heading for the station; one of "the four missions" set many entries could share. -->

The rules are in `docs/SIM_SPEC.md` §0.7 and §5.10. Team 0 defends a station placed on
its own side of the arena, 0.35 of the arena's radius from the centre (−0.35 R). It has a
picket of two strike craft already out, and a garrison docked inside that it launches.
Team 1 arrives from the far side with a carrier, three strike craft jumping in, and the
rest docked in the carrier. The roster (the list of ships each side gets) is "strike of
8":

| Side | Ships |
|---|---|
| Garrison (team 0) | station, fighter, strafer, fighter, gunship, fighter, strafer |
| Attackers (team 1) | carrier, fighter, bomber, fighter, bomber, strafer, bomber, fighter, gunship |

How a match ends:

- The attacker wins by destroying the station (`station_destroyed`).
- The defender wins by destroying the carrier and every strike craft (`assault_repelled`), or when the 150 s clock runs out (`time_limit`).

The pilot and commander networks were trained before the station assault existed and
have no inputs made for a station, so the sim presents the mission to them as one they
already know: as a carrier battle for both sides (**as carrier**),
or as a convoy escort with the station's side as the defender (**as convoy**). This is
the `"as"` field of the mission spec, and no input changed.

Capital ships (the big ones) are always flown by the sim's scripts, and both commanders
are scripted unless a row says otherwise. Each row is 512 matches. The ± is the margin
of error: the true value very likely lies within that range (1.96 standard errors).
Code: `station_eval.py`, `swap_eval.py`, `run.sh`; `analyze.py` prints these tables from
`out/`.

## Tuning

The first build had a 1,000 hp station (hp, hit points, is how much damage a hull takes
before it is destroyed), the old torpedo (55 damage every 3.2 s) and a 110 hp bomber
with no shield. Script against script, the defender won 98% of those
matches, and most of them ran to the clock. The attacking carrier now closes on the
station once its wing (its strike craft) is spent, so a repelled assault ends in a flak
duel (the two capital ships trading fire from their flak turrets, the guns built
against small craft) rather than on the clock. The sweep below
(`tune.py`, `out/tune1.jsonl`) then moved the balance. Each row is one set of numbers,
played 128 times script against script. "Attacker win" is the share of matches the
attackers won, and the bold row is the one we kept:

| Variant | Attacker win | Median length (s) |
|---|---|---|
| base (station 1,000 hp) | 0.08 | 129 |
| station 1,600 hp, torpedo 150 dmg / 4.5 s | 0.40 | 119 |
| station 1,200 hp | 0.41 | 115 |
| **station 1,600, torpedo 150 / 4.5 s, bomber 200 hp + 60 shield** (shipped) | **0.51** | **108** |

The shipped torpedo flies at 90 m/s with a 240 m range and turns at 30°/s. That is a
weapon a ship that cannot move cannot dodge. A fighter crossing it within about 115 m
out-turns it, but a fighter flying straight at the rack is killed by one hit (150
against 80 hp).

## 1. Station balance, script against script

Here the scripts fly every ship. "End reasons" are the shares of matches that ended with
the station destroyed, the assault repelled, or the clock. "p90" is the length that 90%
of matches are shorter than. The last column is the damage the station takes in an
average match from each kind of attacking ship.

| Run | Attacker win | End reasons | Median s | p90 s | Station damage a match: bomber / gunship / fighter / strafer / carrier |
|---|---|---|---|---|---|
| as carrier | 0.549 ± 0.043 | station 0.55, repelled 0.44, clock 0.01 | 111 | 136 | 915 / 534 / 93 / 14 / 189 |
| as convoy | 0.549 ± 0.043 | station 0.55, repelled 0.44, clock 0.01 | 111 | 136 | 915 / 534 / 93 / 14 / 189 |

Both readings give the same match: the scripts do not read the networks' inputs, so
the mapping changes nothing. Bombers deal 52% of the damage the station takes. Each bomber deals 518 damage
in all, 305 of it to capital ships and the rest to strike craft, mostly fighters
crossing its nose.

## 2. Live pilots, zero-shot

"Zero-shot" means with no training on this mission at all. The strike craft are flown by
the ten live pilots (`lab/live_pilots.json`, the ten trained pilots the live page draws
from), one drawn at random for each ship in each match. "Unseen" is the scripted
commander with its orders hidden from its own pilots, so that side's pilots fight with
no orders. The first table reads as in section 1.

| Run | Attacker win | End reasons | Median s | p90 s | Station damage a match: bomber / gunship / fighter / strafer / carrier |
|---|---|---|---|---|---|
| as carrier | 0.361 ± 0.042 | station 0.36, repelled 0.46, clock 0.18 | 111 | 150 | 108 / 532 / 330 / 182 / 344 |
| as convoy | 0.391 ± 0.042 | station 0.39, repelled 0.49, clock 0.12 | 110 | 150 | 124 / 553 / 286 / 171 / 413 |
| as carrier, attacker unseen | 0.586 ± 0.043 | station 0.59, repelled 0.21, clock 0.20 | 108 | 150 | 85 / 711 / 498 / 220 / 318 |
| as carrier, defender unseen | 0.246 ± 0.037 | station 0.25, repelled 0.67, clock 0.08 | 91 | 146 | 85 / 409 / 292 / 155 / 306 |

The second table gives the share of each kind of ship still alive at the end of a
match, and what each bomber damaged: capital ships, or strike craft.

| Run | Attacker survival: bomber / fighter / gunship / carrier | Defender survival: fighter / strafer / gunship | Damage per bomber: capital / strike craft |
|---|---|---|---|
| script, as carrier | 0.09 / 0.03 / 0.39 / 0.56 | 0.00 / 0.00 / 0.54 | 305 / 213 |
| pilots, as carrier | 0.08 / 0.01 / 0.18 / 0.53 | 0.03 / 0.06 / 0.36 | 36 / 73 |
| pilots, as convoy | 0.07 / 0.01 / 0.17 / 0.50 | 0.03 / 0.05 / 0.34 | 41 / 79 |
| pilots, attacker unseen | 0.23 / 0.04 / 0.38 / 0.78 | 0.02 / 0.03 / 0.17 | 28 / 68 |
| pilots, defender unseen | 0.04 / 0.01 / 0.12 / 0.31 | 0.07 / 0.11 / 0.52 | 28 / 66 |

The pilots play the mission, and the decisive ends still outnumber the clock four to one.
Under the carrier reading the attacker wins 0.03 less often than under the convoy
reading, which is inside the noise (± 0.06 on the difference). Bombers flown by pilots
deal a ninth of the station damage that scripted bombers deal. The attacker's gunships,
fighters and carrier do the killing instead. Hiding either side's orders from its own
pilots helps that side: the attacker gains 0.23, and the defender gains 0.12 (the
attacker's win rate falls from 0.36 to 0.25).

## 3. The bomber in place of a gunship

This is a swap test: does a side do better or worse when a gunship is replaced by a
bomber flown by the same pilot? Each match is played twice with the same roster, seed
(the random number that sets up the match) and pilot draws: once as it is, and once with
side X's first gunship replaced by a bomber. The deathmatch uses 16 3 v 3 rosters (three
ships a side) in which side X has a gunship, with side X on either team. The carrier
battle uses the sim's default rosters under the scripted commanders. The score counts a
win as 1 and a draw as half. The delta is the bomber score minus the gunship score,
paired match by match, and n is the number of matches. The last two columns are the
damage the swapped ship dealt to capital ships and to strike craft.

<!-- figure-idea: shared: the swap test as a picture: the same match played twice, once with a gunship and once with a bomber in that slot, everything else identical; the swap cost recurs in later bomber entries. -->

| Mission | Pilots | n | Side X score, gunship | Side X score, bomber | Delta | Swapped slot's damage as gunship: capital / strike | As bomber: capital / strike |
|---|---|---|---|---|---|---|---|
| 3 v 3 deathmatch | script | 512 | 0.811 | 0.746 | −0.064 ± 0.037 | 0 / 255 | 0 / 267 |
| carrier battle | script | 516 | 0.496 | 0.378 | −0.118 ± 0.054 | 236 / 245 | 124 / 379 |
| 3 v 3 deathmatch | live pilots | 512 | 0.718 | 0.335 | −0.383 ± 0.049 | 0 / 127 | 0 / 33 |
| carrier battle | live pilots | 516 | 0.492 | 0.248 | −0.244 ± 0.050 | 236 / 146 | 22 / 67 |

The scripted bomber does as much damage to strike craft as the gunship it replaces, but
it is worse in both missions. In the carrier battle the scripted commander has no
bomber-specific orders, so its bombers spend their torpedoes on strike craft (379)
rather than the carrier (124). A learned pilot in a bomber barely fights: 33 damage a
deathmatch against 127 as a gunship. The swap lowers its side's score by 0.38.

<!-- figure-idea: a gunship's self-aiming turrets beside the bomber's fixed nose rack, with the torpedo's 240 m reach; shows why a pilot that treats a bomber as a gunship never lines up a shot. -->

## What we learned

- **The mission is balanced for the script.** Script against script, the attacker wins
  0.55 ± 0.04. Only 1% of matches run to the clock, and the median match lasts 111 s
  of the 150. That is the intended range. The two readings give identical matches.
- **Pilots fly it zero-shot, but not the bomber.** The pilots read a bomber as the slow
  gunship class (a pilot's inputs describe each ship by a class, and the bomber has the
  gunship's class). A gunship's turrets aim themselves, but the bomber's rack points where
  the hull points.
  With no pilot trained on a fixed torpedo, pilot-flown bombers deal
  36 damage to capital ships per ship (the script's deal 305), and the attacker's win
  falls to 0.36–0.39. The bomber needs pilot training (drills and missions with
  bombers in the roster) before it can appear on the live page.
- **Scripted orders hurt the pilots here too.** Hiding the scripted commander's orders
  helps learned pilots on either side (+0.23 attacking, +0.12 defending). The
  attacker's orders hold its wing at the carrier until all of it has launched (up to
  40 s), and then send it in behind the bombers. Pilots that ignore those orders win
  more. This agrees with [the order cost](../2026-11-17-order-cost/results.md): it is
  following orders that costs, not the station rules.
- **The commander should matter through timing and concentration.** The station's turrets punish a wing that arrives piecemeal. The bombers are what kills the station, so escorts that defend them matter, and the attacker has to commit before the clock runs out. On defence, the commander chooses whom to intercept (bombers first) and when to scramble. None of this is learned yet: no commander has trained on the mission, and its mission weight (the share of commander training spent on it) is 0 by default.
- **Outside the station, the bomber is not yet a better pick than the gunship.** Its
  torpedo is tuned against things that cannot dodge. Against strike craft it trades
  about evenly with the gunship's guns, but it dies sooner (200 hp + 60 shield against
  320 + 140). Whether it earns its place, at a listed supply cost of 25 against the
  gunship's 30 (a price in the hull data), depends on commanders that aim it at capital
  ships.

## Next

- Pilot phase with bombers: add bomber slots to the carrier and station rosters, and
  add a torpedo drill (a short practice scenario: a stationary capital target, then a
  moving one). Until then the bomber stays out of `FLEET_HULLS` (the hulls random fleet
  rosters are drawn from) and every default draft.
- Web: a station-assault entry in `web/src/live/missions.ts`, renderer looks for the
  `bomber` and `station` hulls, end reasons 6 and 7 in `sim.ts`, and a HUD brief.

Later the same night, [station mix](../2026-11-19-station-mix/results.md) trained pilots
with the station assault and bombers in their matches, and [station
commander](../2026-11-19-station-commander/results.md) trained the first commander on
the mission.
