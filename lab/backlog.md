# Lab backlog

Experiment and engineering ideas, added by the user or the agent (DESIGN §3). Each entry
says why it might pay and how we would know.

## Speed: training and the sim

Measured on the order pilot run (`2026-10-31-order-pilot`, two arms at once, 6 sim + 6
torch threads each, i5-1340P: 4 P-cores + 8 E-cores = 16 threads, no GPU). One update is
about 22 s: **rollout 4.5 s (20 %), GAE and credit 0.6 s, PPO update 16.4 s (75 %)**.
A night is about 2.4 h of PPO and 1.7 h of gate evals. So the PPO update and the evals
are where the time goes; the sim is not the bottleneck today.

Ranked by expected payoff per effort:

1. **Cache the anchor's (and the script's) log-probs at rollout time.** `_anchor_term`
   runs the frozen v1 actor on every minibatch of every epoch (4 epochs), though its
   output never changes. Compute it once per sample in `_collect` (or once per update
   before the epochs) and store `[rows, 61]` float16 logits. Expect about 10–15 % of the
   PPO update. The same applies to any β script pull (labels are already cached; check
   nothing else is recomputed). Exactness test: the loss is identical.
2. **Evaluate during training, not after.** Gate evals are about 6.5 min per candidate and
   about 35 % of the night. Options: eval each checkpoint as it lands on a few cores
   reserved for it; **sequential stopping** (SPRT-style: stop a win-rate eval once the gate
   is clearly passed or failed, n ≥ 128 minimum) for candidates far from the bound;
   score the losing arm's candidates with a short screen and the full n only for
   contenders. Expect the eval tail to shrink from about 1.7 h to under 0.5 h.
3. **Thread placement on the hybrid CPU.** Two arms × 12 threads oversubscribe 16
   hardware threads, and torch's GEMM threads wait for the slowest one, an E-core. Try:
   (a) arms one after the other with 12–14 torch threads each; (b) `taskset` torch onto the
   P-cores (8 threads) and the sim's rayon pool onto the E-cores; (c) 4 torch threads per
   arm. Measure s/update and samples/s for each; this is an afternoon of benchmarking.
4. **Overlap rollout and update.** Collect rollout k+1 with policy k while update k
   runs (one update of policy lag, as IMPALA does; PPO's ratio clip tolerates it, or use
   V-trace-style truncated importance weights). Hides the 4.5 s rollout behind the
   update, which pays only once the update is no longer saturating every core, so after
   item 3.
5. **Fewer, larger minibatches / fewer epochs with a KL early stop.** 4 epochs ×
   4096-row minibatches over about 90 k rows. Try 2–3 epochs with a target-KL stop, or
   8192 rows; check samples-to-quality, not just s/update (it can cost learning).
6. **`torch.compile` on CPU (inductor) for the actor's masked multi-head loss and the
   fleet critic's pooled encoder.** 21 small heads and the group view are many small ops;
   fusion could pay at 4096 rows. Check that it compiles once (no recompiles from changing
   pooled group sizes). bf16 autocast is not worth trying here: Raptor Lake has no
   AMX or AVX512-BF16. The installed torch is a CUDA build; a CPU build is smaller but not
   expected to be faster.
7. **Rollout inference in Rust.** The rollout's policy forward runs in torch 128 times per
   update on about 3 k rows, with GIL hops in between. The MLP already exists in JS for
   the browser; a Rust port (with SIMD, sharing weights via the bundle format) inside
   `step` would also let evals run without torch. It pays more once the update is
   faster (items 1–6) and for evals.
8. **Sim hot spots in the missions.** At 12 slots the missions step about 2× slower than
   4v4 (flak fills the projectile pool). Profile with `perf` before changing anything; a
   uniform-grid broadphase for projectiles vs ships is the likely fix if hit tests
   dominate. Today it is under 20 % of the night, so this is later.
9. **Bigger levers, with behaviour changes (a sim season each):** a decision every 2
   ticks (action repeat) halves policy calls and samples per game second; a 20 Hz sim
   instead of 30 Hz. Both change what the pilot can do and need the pilot facts and
   goldens redone, so they are decisions, not optimisations.
10. **The GPU host** (`192.168.50.202`) when it is back: the PPO update moves there and
    the laptop runs sims. DESIGN §7 "Compute".

How we'd know: `tools/bench_env.py` for the sim; for training a fixed 20-update slice
of a run config (same seed) reporting s/update, samples/s and the loss trace, run
before and after each change.
