# Station mix: the station assault and the bomber in pilot training

Prepared 2026-11-19, 00:40, on Beast. The laptop session chose the run; the owner is
asleep. Nothing is launched by this plan; a later task starts `run.sh` from the main
checkout once its venv is rebuilt at SIM_VERSION 9.

## Question

Can a pilot fine-tune learn the bomber and the station assault without losing what it
has on the old missions?

[The station and bomber results](../2026-11-19-station-bomber/results.md) found the live
pilots fly the station assault zero-shot. But the attacker wins only 0.36 to 0.39 with
them, against 0.55 with the script, because they barely fire the bomber's torpedo:
pilot-flown bombers deal 36 damage to capital ships each, the script's 305. Swapping a
gunship for a bomber costs a learned pilot's side 0.38 of a 3 v 3 deathmatch; the
script's side loses 0.06. On this box, `followers_school_1052` in a bomber hits the
attack drill's target 0.16 of the time, against 0.96 in its own hulls. The script in a
bomber still hits it 0.97 of the time (`eval_before/bomber_drills_1052.json`, 64 drills
a kind, each with its swap partner). So the drills are passable with a fixed rack, and
the pilot has simply never flown one.

## The new keys

All three are in `pilots_v1`'s `roster_overrides` (`docs/PILOT_TRAINING.md` §3). Each
defaults to 0, and at 0 it draws nothing, so old configs draw byte-identically
(`tests/test_station_mix.py`).

- `station_as_convoy_share`: the share of station assaults the nets read as a convoy
  escort, with the station's side as the defender. The rest read as a carrier battle.
- `bomber_share`: in a deathmatch, carrier battle or convoy, each strike slot of either
  team becomes a bomber with this chance, drawn slot by slot. A drafted side keeps its
  size, so its cost moves by the hull difference (bomber 25, gunship 30). A station
  assault keeps the sim's roster, which already has 3 bombers among its 14 strike craft.
- `drill_bomber_share`: the same for each pilot slot of an attack or defend drill. The
  enemies and wards keep their hulls, and so do go-to drills, because their deadlines
  come from the drawn hulls' speeds.

`mission_weights` already took a fourth (station) weight. The trainer's
`win_by_class` now logs a station assault as `station_assault/defend` or `/attack` by
the learner's side, as it does for a convoy.

Pool opponents fly the new mission. A snapshot or pool seed is only a net reading obs:
the station reads to it as a carrier battle or a convoy, and a bomber as a strike hull.
Pool seeds from before v8 (583 inputs) take their usual slice. The scratch run below
drew pool, self and scripted opponents in station matches.

## Arms

There are two arms with the same config on two seeds, because a single seed per arm
has misled us before. Both are fresh from `followers_school_1052`
(`lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt`,
`--init`). They use followers_school's config and the mixed-orders `control` arm's
changes (`drill_share` 0.3, `drill_weights` [6, 1, 1], `commander_p` 0.667, `mixed_p`
0), plus:

| Key | Value |
|---|---|
| `mission_weights` | [0.3, 0.225, 0.225, 0.25] |
| `station_as_convoy_share` | 0.5 |
| `bomber_share` | 0.2 |
| `drill_bomber_share` | 0.2 |
| `checkpoint_every` | 25 |

| Arm | seed | Where |
|---|---|---|
| `mix_s1` | 191 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `mix_s2` | 192 | Beast, `update_device=cuda:1`, 3 + 3 threads |

Like the mixed-orders arms, each is a fresh run: a fresh Adam state and snapshot pool,
20 updates of critic warm-up, and 50 of early clip.

### Why these shares

- **Station assault: a quarter of matches.** The old three keep their 0.4 : 0.3 : 0.3
  ratio, scaled to 0.75. A quarter is enough for the new mission to be learned in a
  night. A station match is also long (median 111 s of 150) and has 14 strike craft, so
  its share of training rows is above a quarter. It is not so much that the old
  missions lose most of their rows. The bar on (c) checks that.
- **Both readings half each.** The live page can use either one. The script balance is
  identical under both, and the zero-shot pilots differ by only 0.03 between them. Training on both
  keeps either reading open and stops the pilot from leaning on one obs mapping.
- **Bombers: a fifth of strike slots.** At `bomber_share` 0.2 the sampler gives 0.206
  bombers among all match strike slots: 0.20 in deathmatch, carrier and convoy, and
  0.214 in the station's own roster (`n` 20,000 draws). So a pilot meets a bomber, and
  flies one, at about the same rate everywhere. A fifth is enough for a learner side
  to fly a bomber in most station and carrier matches. Four strike slots in five stay
  the old hulls, so the fighter, strafer and gunship skills keep most of their rows.
- **Drills with bombers, also a fifth.** The attack drill pays for damage on the named
  target, which is exactly "point the hull at it and fire". That is the skill 1052
  lacks in a bomber (0.16 target hit), and the script shows the drill can be passed
  with a fixed rack (0.97). Leaving bombers out of drills would leave the torpedo to
  be learned from match reward alone. Set `drill_bomber_share` 0 to test that instead.
  The drill eval and its gate are unchanged: they still fly the old hulls.

## Measures

All are in `eval.sh` (one checkpoint, against 1052). It is resumable, and `SMOKE=1` gives tiny
sizes. `summary.py` prints the table and the bars. Run it at about update 725, about
2200, and on the last checkpoint of each arm. `eval_before/` is the same on 1052
itself (`NAME=parent_1052 OUT=lab/runs/2026-11-19-station-mix/eval_before eval.sh`),
which skips the candidate-against-1052 parts.

(a) **Station assault**, scripted commanders on both sides, both readings, 256 matches
each (512 a pairing): the candidate attacking 1052, the candidate defending against
1052, and the candidate on both sides. This uses
`../2026-11-19-station-bomber/station_eval.py`, which has a new `--pilots-other` option so
that the other team flies a second pilot list.

(b) **The bomber.** The paired swap (`../2026-11-19-station-bomber/swap_eval.py`, the
candidate flying every strike craft): 3 v 3 deathmatch (512 pairs) and carrier battle
(516). Zero-shot, the live pilots scored −0.38 and −0.24. The bomber's damage to
capital ships, per bomber, comes from (a) and the carrier swap. The drills with every
pilot in a bomber come from `bomber_drills.py`, 64 a kind, beside the same drills as
generated.

(c) **No regression.** `spacefight.eval.missions --a cand --b 1052` (carrier and convoy,
192 a mission), `spacefight.eval.fleet --a cand --b 1052` (the fleet_v1 suite, read
at 3 v 3), and the drill gate (`spacefight.eval.drills`, 64 a kind).

During the run, `log.jsonl` has `win_by_class` (with `station_assault/attack` and
`/defend`), `drill_success`, and `drill_sides`.

## Bars

- (b) The 3 v 3 bomber swap delta is better than −0.15.
- (a) The candidate attacking 1052 wins at least 0.45 of station assaults.
- (c) The candidate scores within 0.05 of 1052 on old missions. Against 1052, which
  scores 0.5 against itself, that means at least 0.45 on carrier, convoy and 3 v 3.
  The drill gate passes.
- Both seeds count. If one seed passes and the other does not, the result is not a
  pass; report both.
- Not tested here: a rating. A passing checkpoint enters the population's WAR like any
  other member before it goes near the live list. It also needs bomber certification
  for the page (results.md "Next").

## Smoke (Beast, 2026-11-19)

These are on Beast, from the worktree with its own v9 venv, CPU only.

- `SMOKE=1` with both arms at 1 + 1 threads: 2 updates each, exit 0. Re-running
  resumed both to update 4, exit 0. The config carries seed 191 / 192 and the overrides.
- `SMOKE=1 eval.sh` on `followers_school_1000` (2 threads): every measure ran in 2 min 53 s.
- Scratch: 16 envs × 128 steps, 24 updates at 1 + 1 threads, so that station matches
  finish (see the report for what the log showed).
