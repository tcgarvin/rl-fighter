# Fighters v2: stronger pilots by plain RL, plus one test of paying pilots for orders

Planned 2026-10-31 at 22:50, before any candidate of this run was trained or evaluated.

**Why this run.** The user, going to bed: back off from the ambitious work and run
experiments with a better chance of deploying something tonight, maybe just better
fighters. No check-in until about 08:00.

Three order-following runs failed their gates (run 1, B2b, B3), but every one of them
that ran without a script pull produced a clearly stronger fighter. So plain PPO on the
missions is the part that works, and this run does more of it.

## 1. Shipping first: `reward_300` as champion

Run B3's `reward_300` wins 0.726 of missions against fleet pilot v1 and passes B3's M, D
and H gates. It fails only O, the order-following gate. **O is waived for this one
promotion** on the user's instruction above; orders stay a stated goal, not a claim about
this pilot. Its order following stays reported, as in B3.

A blocker found while checking: with `reward_300` on both sides, convoy attackers win
about 97 % in a median 33 s (v1 mirror on the same sim: about 55 % in 68 s). So the
convoy needs a balance pass for the new pilot before it goes live: attackers 35-65 % on
every default roster, the mission survey's existing band.

## 2. The training arms

All three: init `reward_300` (583 inputs), no script pull at any row, 256 envs, `orders_v1`
rosters, learner side random, fleet critic, actor LR 1e-4, critic LR 3e-4, checkpoints
every 50 updates, 4 sim + 4 torch threads, 20 critic warm-up updates, clip 0.1 for the
first 50 updates and then 0.2. Opponents: 20 % scripts, 40 % self, 40 % frozen pool (v1,
w1_400, reward_300, half the pool draws; the run's own snapshots the rest).

**Constant LR.** Every earlier run decayed LR linearly to 0 over its length, so half of
B3 ran under 50 % LR and its last updates did nothing (actor_lr ~3e-7 at update 299).
A constant LR also lets the run stop at a clock time without wasting any schedule.

| arm | gamma | order reward w | KL anchor on no-order rows | hide damage under orders | question |
|---|---|---|---|---|---|
| `f99` | 0.99 | 0 | none | no | Does more plain PPO on the team reward make a better fighter? |
| `f995` | 0.995 | 0 | none | no | Does doubling the horizon, 3.3 s to 6.7 s at 30 Hz decisions, help? |
| `hide` | 0.99 | 1 | reward_300, 0.1 | **yes** | If an ordered pilot is paid only for its order, does it follow? What does it cost? |

- `f99` is the safe bet and the control for the other two.
- `f995` has w = 0 because the sim's potential shaping is hard-coded to gamma 0.99
  (`ORDER_SHAPING_GAMMA`), which would bias order rewards at another gamma.
- `hide` is the order experiment, deliberately simple: feudal RL's "reward hiding"
  (Dayan & Hinton 1993). On rows with an order, a shot earns no team damage reward; the
  order reward pays damage to the attack target or the ward's threat set, and go-to pays
  arrival. Damage taken, fire cost, arena and the terminal stay. After a go-to arrives
  the order is none, so normal pay resumes: a pilot's way back to paid fighting runs
  through finishing the order.

## 3. Clock

PPO stops by SIGTERM at 05:30 at the latest, each arm checkpointing cleanly. Screen and
gates 05:30-07:15. Any promotion and deploy by 07:45.

## 4. Candidates and gates (fixed now, before any eval)

The **reigning pilot** R is `reward_300`, on the live default rosters as rebalanced in §1.

**Screen.** Every arm's checkpoints at 200, 400 and the last: mean mission win vs R,
n = 258 per mission, seed 300000. The two best F candidates (`f99`, `f995`) and the best
`hide` candidate go to the gates. Screening picks; it decides nothing.

**Gate F, a better fighter** (fresh seed 310000, so the screen's winner's curse does not
count), for an `f99` or `f995` candidate:
- F1: mean mission win vs R >= 0.55, n = 1032 per mission (0.55 is about 4 standard
  errors above 0.5), and each mission >= 0.47.
- F2: deathmatch `fleet_v1` suite vs R >= 0.50 and vs the script >= 0.85.
- F3: health: NaN or stuck <= 1 %, outside arena <= 0.02, time-limit rate <= 0.10 in
  carrier battles and in convoys.
- Reported, not gated (the user waived engine duty on 2026-10-30): engine duty per hull.
  Match lengths reported; a median mission under 30 s is called out as a watchability
  problem whatever the gates say.

**Gate H, following at a price we can accept**, for a `hide` candidate: B3's bars,
unchanged, using `order_gates_b3`:
- O: as B3: attack share >= hidden + 0.05, threat share >= hidden + 0.05, go-to in time
  >= 0.7, attack close <= 150 ticks, the defend hull-lost bound from B3's `o_bounds.json`.
- M: mission win vs v1, each >= 0.47 and mean >= 0.52.
- D: deathmatch vs script >= 0.85 and vs v1 >= 0.45.
- H: as B3.

**What ships.** A `hide` candidate passing gate H ships first, because it is the only
result that moves the commander goal, unless an F candidate also passes and beats it
head to head. Otherwise the F candidate with the highest mean mission win vs R. Otherwise
R stays. After a promotion: convoy balance re-checked for the new pilot (band of §1) and
retuned by the roster if outside; bundle smoke, phone shots, deploy.

**Kill rules.** An arm whose rollout win vs the snapshot pool falls below 0.25 for 50
updates after update 100 is stopped and its threads given to the others.

## 5. What this run will not answer

Whether from-scratch RL can replace the BC ancestry (nothing here starts from scratch;
every arm descends from the script-cloned v1 even though no script is pulled tonight);
whether a learned commander is worth building.
