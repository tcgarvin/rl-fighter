# The citadel and the dreadnought: balanced for the script, and the pilots shoot at the dreadnought

`SIM_VERSION` 10 lets a capital ship's turrets and bays be destroyed one by one
(hardpoints), adds a capital-only weapon (the lance) and a gun capital ship (the
`dreadnought`), and gives the station assault a second roster in which a much bigger
station, the `citadel`, faces a carrier and a dreadnought. When the scripts fly both
sides, the attacker wins 0.56 of these assaults and 4% run to the clock. A typical match
loses one or two of the citadel's twelve turrets and one bay in two. The lance is what
holds the dreadnought off: with a 1-damage lance the attacker wins every match. The
dreadnought beats a lone carrier every time and loses every time to a carrier with a
wing of eight. The live pilots fly the new roster unchanged and do attack the
dreadnought, which they read as a hull class they have never seen; the attacker wins
less often with them (0.25 to 0.29). Every old mission plays exactly as it did in v9.

<!-- summary: We built a much bigger space station whose turrets and launch bays can each be shot off, and a new heavy warship, the dreadnought, that attacks it alongside a carrier. With scripted pilots on both sides the attackers win a little over half the time, which is the balance we aimed for. The station's heavy anti-ship guns are what keep the dreadnought in check: without them the attackers won every match. Our trained pilots have never seen a dreadnought, but they shoot at it anyway. Nothing about the older missions changed. -->

The rules are in `docs/SIM_SPEC.md` §0.8; the mounts (positions, ids, hit points) are
in `plan.md`, the contract with the art work, and none of them moved. The new roster is
"citadel"; v9's "strike of 8" stays the default and plays exactly as before.

| Side | Ships |
|---|---|
| Garrison (team 0) | citadel, fighter, strafer, fighter, gunship, fighter, strafer, fighter |
| Attackers (team 1) | carrier, dreadnought, fighter, bomber, fighter, bomber, strafer, bomber, fighter, gunship, fighter |

The citadel is a static carrier-role hull with 3,200 hp, a 600 hp shield and twelve
turrets on a ring of six modules: two lances (anti-capital), six flak and four gauss.
Its four bays launch the garrison. Every turret and bay has its own hit points (lance
250, flak 120, gauss 100, bay 200). A hull hit within 8 m of a mount (7 m for a bay)
damages that mount by the same amount; the hull still takes the full hit. A mount at 0
hp is gone for the match: a dead turret never fires, a dead bay never launches. The
dreadnought (1,800 hp, shield 350, 7 m/s) has two rails, two flak and a gauss, all of
them destroyable, and an armoured bow (0.4 of the damage, the flanks 0.7, the stern
1.3). Its script closes to 0.8 of rail range and holds the target 40° off the bow, so
the armour faces the enemy and both rails bear. Its rails aim at the nearest live enemy
hardpoint in range, lances first. The attacker is repelled only when its carrier, its
dreadnought and every strike craft are gone. With 19 ships the arena is 550 m (450 for
the 16 of v9's roster).

Capital ships are always flown by the sim's scripts, and both commanders are scripted.
Each Python row is 512 matches; the ± is 1.96 standard errors. Code: `citadel_eval.py`,
`compare_v9.py`, `run.sh`; the Rust harness is `crates/sim/tests/citadel.rs`
(`diag_v10_assault`, `diag_dreadnought_vs_carrier`).

## Tuning

The plan's starting numbers (citadel 3,000 hp, rail 40 damage, lance 55) gave the
attacker all 64 of 64 matches. The dreadnought did about 2,200 damage to the citadel a
match, and the lance barely scratched it through its 0.4 bow. The sweep below (Rust
harness, 128 starts a variant unless noted, seeds 1000 on) moved the rail down and the
lance up:

| Variant (rail / lance damage, citadel hp) | Attacker win | Clock |
|---|---|---|
| 40 / 55, 3,000 (plan) | 1.00 (64 starts) | 0 |
| 40 / 110, 3,000 | 1.00 | 0 |
| 24 / 120, 3,000 | 0.67 | – |
| 24 / 130, 3,000 | 0.68 | – |
| 24 / 120, 3,300 | 0.71 | – |
| 22 / 120, 3,000 | 0.66 | – |
| 20 / 110, 3,000 | 0.59 | 10 / 128 |
| 20 / 120, 3,000 | 0.56 | 12 / 128 |
| 20 / 130, 3,000 | 0.56 | 6 / 128 |
| 18 / 120, 3,000 | 0.45 | 15 / 128 |
| **22 / 130, 3,200** (shipped) | **0.57** | **6 / 128** |

The shipped rail does 22 damage every 1.6 s at 260 m/s out to 380 m. The lance does 130
every 2.2 s at 300 m/s out to 430 m and passes through strike craft. Turret, bay and
dreadnought hit points are the plan's.

## 1. Balance, script against script

| Run | Attacker win | End reasons | Median s | p90 s | Citadel damage a match: dreadnought / gunship / bomber / carrier / fighter / strafer |
|---|---|---|---|---|---|
| as carrier | 0.559 ± 0.043 | station 0.56, repelled 0.40, clock 0.04 | 114 | 136 | 923 / 920 / 841 / 374 / 34 / 16 |
| as convoy | 0.559 ± 0.043 | station 0.56, repelled 0.40, clock 0.04 | 114 | 136 | 923 / 920 / 841 / 374 / 34 / 16 |

The two readings give the same match, since the scripts read no obs. The damage on the
citadel is spread evenly over the dreadnought, the gunship and the three bombers.

**Hardpoints.**

| Run | Citadel turrets lost a match: flak / gauss / lance (all) | Bays lost | Matches with a mount lost | First mount lost: flak / gauss / bay / lance | Dreadnought turrets lost |
|---|---|---|---|---|---|
| script | 0.78 / 0.48 / 0.46 (1.72) | 0.59 | 0.82 | 152 / 120 / 109 / 39 | 1.30 |
| pilots, as carrier | 0.62 / 0.37 / 0.19 (1.19) | 0.38 | 0.57 | 96 / 76 / 93 / 29 | 1.73 |
| pilots, as convoy | 0.63 / 0.39 / 0.20 (1.22) | 0.49 | 0.63 | 100 / 95 / 100 / 27 | 1.72 |

Mounts go on most matches, but a few at a time: about one turret in seven and one bay in
seven. Flak goes first most often (it is the most numerous, and on the module faces),
then gauss and the bays. The lances, with the most hit points, go first in fewer than
one match in ten.

**The lance and the dreadnought.** The same harness assault with a lance that does 1
damage (`out/diag_lance_1.txt`, 128 starts against the shipped `out/diag_shipped.txt`):

| Lance | Attacker win | Citadel damage to the dreadnought a match | Dreadnought died | Dreadnought damage to the citadel |
|---|---|---|---|---|
| shipped (130) | 0.57 | 1,715 | 49 / 128 | 975 |
| 1 damage | 1.00 | 28 | 0 / 128 | 1,537 |

Nearly all of the citadel's damage on the dreadnought is the lance's: the flak and the
gauss spend themselves on strike craft. Without the lance the dreadnought sits at its
standoff untouched and the attacker wins every match.

**Dreadnought against a carrier** (the Rust harness, a deathmatch start, the dreadnought
alone against a carrier with 0, 4 or 8 strike craft, 40 starts each, 150 s clock;
`out/dreadnought_vs_carrier.txt`):

| Carrier side | Dreadnought wins | Mean length (s) | Dreadnought hull left |
|---|---|---|---|
| carrier alone | 1.00 (40 / 40) | 79 | 1,800 |
| carrier + 4 | 0.98 (39 / 40) | 115 | 569 |
| carrier + wing of 8 | 0.00 (0 / 40) | 38 | 0 |

The dreadnought wins a gun duel with a carrier without losing any hull: the carrier never gets
through its shield. Four strike craft cost it two thirds of its hull,
and a full wing of eight kills it in 38 s. This is what the plan asked for.

## 2. Live pilots, zero-shot

The strike craft are flown by the ten live pilots (`lab/live_pilots.json`), drawn per
slot per match. No pilot has seen a dreadnought: its hull class in the obs is `spare`,
which no hull used before.

| Run | Attacker win | End reasons | Median s | p90 s | Citadel damage a match: dreadnought / gunship / bomber / carrier / fighter / strafer |
|---|---|---|---|---|---|
| as carrier | 0.254 ± 0.038 | station 0.25, repelled 0.62, clock 0.13 | 120 | 150 | 686 / 814 / 150 / 104 / 224 / 64 |
| as convoy | 0.295 ± 0.040 | station 0.29, repelled 0.62, clock 0.09 | 115 | 148 | 755 / 886 / 173 / 116 / 197 / 64 |

**Do the pilots engage the dreadnought?** Yes. Damage by the garrison's strike craft:

| Run | To the dreadnought a match | Share of their damage on the dreadnought | Garrison strike craft that hit it | Dreadnought died | Carrier died |
|---|---|---|---|---|---|
| script | 123 | 0.25 | 0.16 | 0.40 | 0.54 |
| pilots, as carrier | 251 | 0.21 | 0.35 | 0.73 | 0.65 |
| pilots, as convoy | 253 | 0.22 | 0.35 | 0.69 | 0.66 |

The pilots put twice the script's damage on the dreadnought, and twice as many of them
land a hit on it. A fifth of everything they hit is the dreadnought. So the `spare`
class is not a blind spot, and the fallback in the plan (reading it as a carrier) is not
needed. This does not say whether they choose it or are sent: the scripted defence's
intercept order names the dreadnought once the carrier is gone.

## What we learned

- **The citadel assault is balanced for the script.** The attacker wins 0.56 ± 0.04,
  4% of matches run to the clock, and the median match lasts 114 s of the 150.
- **Hardpoints matter without deciding the match.** Most matches lose a mount, about
  1.7 turrets and 0.6 bays for the script. The plan's rule that a mount never soaks
  damage keeps the hull's balance where the sweep put it.
- **The lance is the citadel's answer to the dreadnought.** At the plan's 55 damage it
  was no answer at all through the armoured bow; at 130 it does almost all the damage
  the dreadnought takes; with a 1-damage lance the attacker wins every match.
- **The dreadnought is a capital-ship killer, not a fighter killer.** It wins gun to
  gun against a carrier and loses to a carrier's wing.
- **Pilots fight the dreadnought zero-shot, but lose the assault more.** The attacker
  wins 0.25–0.29 with pilots (v9's station: 0.36–0.39). Pilot-flown bombers still barely
  torpedo (150 damage on the citadel a match against the script's 841), the same gap as
  in v9.
- **Nothing old moved.** The v9 entry's script-vs-script evaluations (`out/v9_rerun/`,
  `out/v9_compare.txt`) give the same numbers to the last digit under v10, and the
  eleven v9 golden traces replay bit for bit.

## One sim fix found here

The first Python run gave the attacker 0.94 where the Rust harness said 0.57. An action
row has six turret slots, so a citadel flown through the bindings (or the web page)
fired only six of its twelve turrets. Every capital ship is flown by its script, so the
sim now gives a hull with more than six turrets the script's slew and fire for the rest
(step stage 0). A row-driven citadel now hashes the same as a script-driven one every
tick.
