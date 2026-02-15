"""MAPPO self-play training for 2v2 space combat.

All ships share the same policy with egocentric observations.
Centralized critic sees concatenated team observations.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch

from spacefight.env.vec_env import VecEnv, build_critic_obs
from spacefight.rl.policy import ActorCritic, OBS_DIM, CRITIC_OBS_DIM, TURN_MAP
from spacefight.rl.rollout_buffer import RolloutBuffer
from spacefight.rl.ppo import ppo_update
from spacefight.rl.credit import CreditAssigner

# Hyperparameters
N_ENVS = 256
N_SHIPS = 4
T_STEPS = 128
T_TAIL = 48  # tail buffer for retroactive credit (covers bullet/gauss TTL)
N_UPDATES = 5000
GAMMA = 0.99
LAM = 0.95
LR = 3e-4
CLIP_EPS = 0.2
K_EPOCHS = 4
BATCH_SIZE = 4096
ENT_COEFF = 0.01
VF_COEFF = 0.5
MAX_GRAD_NORM = 0.5
CHECKPOINT_INTERVAL = 100
CHECKPOINT_DIR = Path("checkpoints")


def _fmt_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def train(args: argparse.Namespace) -> None:
    """Run MAPPO self-play training loop."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    train_start = time.time()
    print(f"Training started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Config: {args.n_envs} envs × {N_SHIPS} ships × {T_STEPS} steps = "
          f"{args.n_envs * N_SHIPS * T_STEPS:,} transitions/update")
    print(f"Credit assignment: T_TAIL={T_TAIL} ({T_TAIL/30:.1f}s)")

    CHECKPOINT_DIR.mkdir(exist_ok=True)

    env = VecEnv(
        n_envs=args.n_envs,
        seed=args.seed,
        n_ships=N_SHIPS,
        randomize_hulls=True,
    )
    model = ActorCritic().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    buf = RolloutBuffer(
        n_steps=T_STEPS,
        n_envs=args.n_envs,
        n_ships=N_SHIPS,
        obs_dim=OBS_DIM,
        critic_obs_dim=CRITIC_OBS_DIM,
        t_tail=T_TAIL,
    )

    credit = CreditAssigner(
        n_envs=args.n_envs,
        n_ships=N_SHIPS,
        buf_len=T_STEPS + T_TAIL,
    )

    obs = env.reset()  # [N, S, OBS_DIM]

    total_episodes = 0
    episode_rewards = []
    tail_data = None

    steps_per_update = args.n_envs * N_SHIPS * T_STEPS

    for update in range(1, args.n_updates + 1):
        t_start = time.time()
        rollout_reward = 0.0
        zone_violation_count = 0
        zone_total_count = 0
        first_damage_ticks: list[int] = []
        episode_has_damage = np.zeros(args.n_envs, dtype=np.bool_)
        credit_hits = 0

        # --- Rollout phase ---
        model.eval()
        buf.reset()
        credit.reset_for_rollout()

        # Prepend tail from previous rollout
        tail_size = 0
        if tail_data is not None:
            buf.prepend_tail(tail_data)
            tail_size = T_TAIL

        for t in range(T_STEPS):
            buf_step = tail_size + t

            # Stamp episode generation for credit tracking
            credit.stamp_step(buf_step)

            obs_tensor = torch.from_numpy(obs).to(device)
            critic_obs_np = build_critic_obs(obs, N_SHIPS)
            critic_obs_tensor = torch.from_numpy(critic_obs_np).to(device)

            with torch.no_grad():
                actions, log_probs, _, values = model.get_action_and_value(
                    obs_tensor, critic_obs_tensor
                )

            # Convert back to numpy for env
            actions_np = actions.cpu().numpy()  # [N, S, 4] with turn as -1/0/1

            # We need raw categorical indices for the buffer (turn as 0/1/2)
            raw_actions_np = actions_np.copy().astype(np.int64)
            raw_actions_np[:, :, 0] = actions_np[:, :, 0] + 1  # -1/0/1 -> 0/1/2

            next_obs, rewards, dones, infos = env.step(actions_np, rollout_step=buf_step)

            # Record projectile hits for credit assignment
            if "proj_hit" in infos:
                proj_hit = infos["proj_hit"]
                if np.any(proj_hit):
                    credit.record_hits(
                        buf_step,
                        proj_hit,
                        infos["proj_owner"],
                        infos["proj_damage"],
                        infos["proj_fire_step"],
                    )
                    credit_hits += int(proj_hit.sum())

            # Zone violation tracking
            st = env.state
            dx_z = st.x - st.zone_cx[:, None]
            dy_z = st.y - st.zone_cy[:, None]
            dist_z = np.sqrt(dx_z**2 + dy_z**2)
            margin_z = (st.zone_r[:, None] - dist_z) / st.zone_r[:, None]
            zone_violation_count += int((margin_z < 0).sum())
            zone_total_count += margin_z.size

            # Time to first damage: record tick when damage first occurs
            newly_damaged = (st.t_since_damage == 0) & ~episode_has_damage
            if newly_damaged.any():
                for idx in np.where(newly_damaged)[0]:
                    first_damage_ticks.append(int(st.tick[idx]))
                episode_has_damage |= newly_damaged

            # Handle episode resets for credit tracking
            if dones.any():
                credit.on_reset(np.where(dones)[0])
                episode_has_damage[dones] = False

            buf.insert(
                obs=obs,
                critic_obs=critic_obs_np,
                raw_actions=raw_actions_np,
                log_probs=log_probs.cpu().numpy(),
                values=values.cpu().numpy(),
                rewards=rewards,
                dones=dones,
            )

            rollout_reward += rewards.sum()
            obs = next_obs

            # Track episodes
            n_done = dones.sum()
            if n_done > 0:
                total_episodes += int(n_done)

        t_rollout_end = time.time()

        # --- Inject retroactive credits into reward buffer ---
        credit.inject_into_rewards(buf.rewards, 0, tail_size + T_STEPS)

        # --- Compute GAE ---
        with torch.no_grad():
            last_obs_tensor = torch.from_numpy(obs).to(device)
            last_critic_obs_np = build_critic_obs(obs, N_SHIPS)
            last_critic_obs_tensor = torch.from_numpy(last_critic_obs_np).to(device)
            _, last_values = model(last_obs_tensor, last_critic_obs_tensor)
            last_values = last_values.cpu().numpy()

        # dones from last step of rollout (already in buf, use env state)
        last_dones = env.state.done

        advantages, returns = buf.compute_gae_with_tail(
            last_values=last_values,
            last_dones=last_dones,
            gamma=GAMMA,
            lam=LAM,
            tail_size=tail_size,
        )

        # --- PPO update phase ---
        model.train()
        flat_obs, flat_critic_obs, flat_actions, flat_lp, flat_vals = (
            buf.get_flat_tensors(skip=tail_size)
        )

        stats = ppo_update(
            model=model,
            optimizer=optimizer,
            obs=flat_obs,
            critic_obs=flat_critic_obs,
            raw_actions=flat_actions,
            old_log_probs=flat_lp,
            advantages=advantages,
            returns=returns,
            clip_eps=CLIP_EPS,
            vf_coeff=VF_COEFF,
            ent_coeff=ENT_COEFF,
            max_grad_norm=MAX_GRAD_NORM,
            k_epochs=K_EPOCHS,
            batch_size=BATCH_SIZE,
        )

        # --- Save tail for next rollout ---
        tail_data = buf.extract_tail()
        credit.shift_tail(T_STEPS)

        t_end = time.time()
        elapsed = t_end - t_start
        rollout_time = t_rollout_end - t_start
        ppo_time = t_end - t_rollout_end
        sim_steps_sec = (args.n_envs * T_STEPS) / rollout_time
        total_elapsed = t_end - train_start
        remaining = (args.n_updates - update) * (total_elapsed / update)

        mean_reward = rollout_reward / steps_per_update
        zone_viol_frac = (
            zone_violation_count / zone_total_count if zone_total_count > 0 else 0.0
        )
        mean_first_dmg = (
            np.mean(first_damage_ticks) if first_damage_ticks else float("nan")
        )

        if update % 10 == 0 or update == 1:
            print(
                f"U {update:4d} | "
                f"r {mean_reward:+.4f} pg {stats['pg_loss']:.4f} "
                f"vf {stats['vf_loss']:.4f} ent {stats['entropy']:.3f} | "
                f"ep {total_episodes} zv {zone_viol_frac:.3f} fd {mean_first_dmg:.0f} ch {credit_hits} | "
                f"{elapsed:.1f}s {sim_steps_sec/1000:.0f}k sps | "
                f"{_fmt_duration(total_elapsed)} eta {_fmt_duration(remaining)}"
            )

        # Checkpoint
        if update % CHECKPOINT_INTERVAL == 0:
            path = CHECKPOINT_DIR / f"policy_{update}.pt"
            torch.save(model.state_dict(), path)
            print(f"  Saved checkpoint: {path}")

    # Final save
    final_path = CHECKPOINT_DIR / "policy_final.pt"
    torch.save(model.state_dict(), final_path)
    total_time = time.time() - train_start
    total_steps = args.n_updates * args.n_envs * T_STEPS
    print(
        f"Training complete in {_fmt_duration(total_time)} "
        f"({total_steps:,} env steps, "
        f"{total_steps / total_time:.0f} avg env·steps/s). "
        f"Final checkpoint: {final_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MAPPO self-play training")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-envs", type=int, default=N_ENVS)
    parser.add_argument("--n-updates", type=int, default=N_UPDATES)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
