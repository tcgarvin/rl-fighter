# Crashes now hurt: the learned pilot rams 82 % less and still wins every duel

<!-- summary: Our first trained pilot and the hand-written one kept flying into each other, nose to nose, because a crash cost nothing. We changed the game's rules so that a crash does damage, taught the hand-written pilot to swerve, and retrained the learned pilot under the new rules. The pilot we chose has 82 % fewer fast crashes and still wins every duel against the hand-written pilot, though its fights are still one approach and a close brawl. -->

Ships kept colliding head-on in duels, and nothing in the game made that costly. We
made crashes do damage, with the fighter's nose the most fragile part, so that pilots
have a reason to turn away. The learned pilot, retrained under the new rules, now has
82 % fewer fast crashes (collisions closing faster than 30 m/s), still wins all 512 test duels against the script (our
hand-written pilot), and beats its own earlier self in 82 % of duels. It still fights
the same short way: one approach, then a close brawl. The chosen version, arm A at
update 600 (explained below), replaced the earlier champion on the site's duel page.

Run 2026-10-29, plan: `plan.md` (gates, the targets in the table below, fixed before any test under the new v3 rules). Shipped:
**arm A (pure RL), update 600**.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural
network that learned to fly by trial and error. Its rules run in a simulation that
plays many matches at once, far faster than real time.
[The first training run](../2026-10-28-learnability-spike/results.md), the day
before, produced a learned fighter pilot, the champion `ppo_bc_1200`, that beat the
script in all 512 test duels.

But a survey of those duels ([the plan](plan.md) §1) found collisions in every match,
nearly all of them nose to nose: the champion and the script met at a typical closing
speed of 96 m/s and bumped through each other, because a crash was a harmless bounce.
The owner asked for crashes to hurt, for fighters to be fragile, and for the nose to be
more fragile than the flanks. We made the change in the game's physics rather than as a
penalty in the training reward, so it applies to every pilot, learned or scripted.

## What changed

- **Sim v3**, the third version of the game's rules (`SIM_VERSION` 3). A closing
  contact (two ships colliding while moving toward each other) now does damage that
  grows with the square of the closing speed above 10 m/s. Fighters take 1.5× on the
  nose, so a ~96 m/s head-on costs each one about 55 of its 80 hit points (hp). In
  training, neither pilot earns reward for the crash damage the other ship takes. A
  crash shows as a white flash with amber sparks.
- **Script.** The hand-written fighter predicts the closest approach and sidesteps
  so its pass (attacking run) misses the other ship. Script vs script: fast contacts
  (collisions closing faster than 30 m/s) per match fell from 8.4 to 0.02 and passes
  rose from 2.9 to 4.9. Its hit rate fell from 0.60 to 0.46.
- **Pilot.** The champion from the first run (the "spike champion") was fine-tuned,
  trained further from where it was, for 800 PPO updates under v3. PPO is our
  trial-and-error training method, and an update is one round of play and adjustment.
  It trained in two arms, two versions run side by side: A with no script pull, B with
  a script pull (an extra training term that pulls the pilot's choices toward the
  script's) toward the new script, fading out by update 400. A name like A-600 means
  arm A, saved at update 600.

## Gates (512 duels; contact survey of 128 duels vs the script)

The gates are pass marks fixed in [the plan](plan.md) (§4) before any test under the
new rules. Each row is one saved pilot. "Old champion, on v3" is the first run's
champion flown under the new rules. Win rates are shares of duels won, where 0.5 is an
even fight. The crash columns come from the survey of 128 duels against the script:
fast contacts per match, and the share of matches in which a ship died in a crash.
Engine duty is the main engine's average thrust level, from 0 (off) to 1 (full).
Passes are attacking runs per duel, and ticks are the simulation's time steps, 30 a
second.

| pilot | win vs script | win vs old champion | fast contacts / match | matches with a crash death | engine duty | passes | median ticks |
|---|---|---|---|---|---|---|---|
| old champion, on v3 | 1.000 | 0.50 | 1.16 | 19.5 % | 0.90 | 1.0 | 387 |
| **A, update 600 (shipped)** | **1.000** | **0.82** | **0.21** | **7.8 %** | 0.78 | 1.0 | 307 |
| A, update 800 | 1.000 | 0.74 | 0.46 | 16.4 % | 0.75 | 1.1 | 326 |
| B, update 600 | 1.000 | 0.46 | 0.23 | 0.8 % | 0.23 | 1.0 | 370 |
| B, update 800 | 1.000 | 0.56 | 0.01 | 0 % | 0.15 | 1.0 | 276 |

- Gates: G1 fast contacts ≤ 0.3, G2 win vs script ≥ 0.9 and vs old champion > 0.5,
  G3 health: engine duty 0.2–0.95 (the plan's health gate also caps time outside the
  arena and draws). **A-600 is the only candidate to pass all three.**
- **B-800 crashes least but fails health (G3).** It learned to barely use the engine
  (duty 0.15) and wait for the script to come to it. That is safe but dull, so the
  duty gate rejects it.
- **A drifted back toward contact between updates 600 and 800.** That is why the
  earlier checkpoint (saved copy) was picked.
- Hit rate rose from 0.57 to 0.76 for A-600, and only 4 % of the hull damage it deals
  or takes comes from crashes (21 % for the old champion).

<!-- figure-idea: a diagram of a crash under the new rules: two fighters closing head-on, with the damage curve against closing speed (nothing below 10 m/s, about 55 of 80 hp at 96 m/s) and the fighter's nose marked as the 1.5x arc. It would make "damage grows with the square of the closing speed" concrete. -->

## What did not change

- **Each duel is still one approach and a close fight.** That is about one pass, with
  the median match around 10 s.
- **The pilot no longer flies into the other ship, but it still doesn't extend (fly on
  out of range) and come round** the way the new script does.
- **Against the script, A-600 rarely touches now:** the survey finds contacts in 27 %
  of its matches (0.27 a match), and only 37 % of those are head-on (98 % for the old
  champion under the old rules).

## Next

- Gate on passes or duel length (the watchability gate in
  [the first run's backlog](../2026-10-28-learnability-spike/results.md)) so selection
  rewards longer, readable fights rather than only fewer crashes.
- Rerun DAgger from the new, passing script (the one that makes passes instead of
  ramming) before PPO. DAgger is the correction step
  of the first run's recipe: the learned pilot flies, and the script says what it would
  have done in each situation. The current pilot was cloned (trained to copy) from the
  old ramming script, and fine-tuning kept its close-brawl style.
- The script's heading controller (the part of it that steers the nose) wobbles about
  ±0.3 rad (about 17°), so most of its shots are sweeps across the target. Fixing that
  would make it a better teacher.
