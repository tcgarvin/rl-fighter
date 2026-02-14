"""Pygame visualization for 2v2 space combat matches.

Renders a single 2v2 match with ship triangles, bullets, HP bars, and HUD.

Controls:
    Space - pause/unpause
    R     - reset match
    Q     - quit
"""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np
import pygame

from spacefight.sim.core import SimState, reset, step

# Display constants
WINDOW_W = 1200
WINDOW_H = 800
FPS = 30
BG_COLOR = (0, 0, 0)

# Ship colors: team 0 (blue shades), team 1 (red shades)
SHIP_COLORS = [
    (60, 120, 255),   # team 0, ship 0 (blue-light)
    (30, 80, 200),    # team 0, ship 1 (blue-dark)
    (255, 80, 80),    # team 1, ship 2 (red-light)
    (200, 50, 50),    # team 1, ship 3 (red-dark)
]
TEAM_NAMES = ["Blue-1", "Blue-2", "Red-1", "Red-2"]
DEAD_COLOR = (100, 100, 100)
BULLET_RADIUS = 3
SHIP_SIZE = 14  # half-length of triangle

# HP bar
HP_BAR_W = 40
HP_BAR_H = 5
HP_BAR_OFFSET = 20  # pixels above ship

# World-to-screen transform: center the arena
WORLD_CENTER_X = 0.0
WORLD_CENTER_Y = 0.0
SCALE = 0.7  # pixels per world unit (smaller for larger arena)


def world_to_screen(wx: float, wy: float) -> tuple[int, int]:
    """Convert world coordinates to screen pixel coordinates."""
    sx = int(WINDOW_W / 2 + (wx - WORLD_CENTER_X) * SCALE)
    sy = int(WINDOW_H / 2 - (wy - WORLD_CENTER_Y) * SCALE)  # flip Y
    return sx, sy


def draw_ship(
    surface: pygame.Surface,
    x: float,
    y: float,
    theta: float,
    color: tuple[int, int, int],
    alive: bool,
) -> None:
    """Draw a ship as a triangle pointing in its heading direction."""
    draw_color = color if alive else DEAD_COLOR
    sx, sy = world_to_screen(x, y)

    # Triangle vertices: nose, left wing, right wing
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    nose = (
        sx + int(SHIP_SIZE * cos_t),
        sy - int(SHIP_SIZE * sin_t),
    )
    left = (
        sx + int(SHIP_SIZE * 0.6 * math.cos(theta + 2.4)),
        sy - int(SHIP_SIZE * 0.6 * math.sin(theta + 2.4)),
    )
    right = (
        sx + int(SHIP_SIZE * 0.6 * math.cos(theta - 2.4)),
        sy - int(SHIP_SIZE * 0.6 * math.sin(theta - 2.4)),
    )

    pygame.draw.polygon(surface, draw_color, [nose, left, right])


def draw_hp_bar(
    surface: pygame.Surface,
    x: float,
    y: float,
    hull_frac: float,
) -> None:
    """Draw a small HP bar above a ship."""
    sx, sy = world_to_screen(x, y)
    bar_x = sx - HP_BAR_W // 2
    bar_y = sy - HP_BAR_OFFSET

    # Background (red)
    pygame.draw.rect(surface, (180, 30, 30), (bar_x, bar_y, HP_BAR_W, HP_BAR_H))
    # Foreground (green)
    fill_w = max(0, int(HP_BAR_W * hull_frac))
    if fill_w > 0:
        pygame.draw.rect(surface, (30, 200, 30), (bar_x, bar_y, fill_w, HP_BAR_H))


def draw_bullet(
    surface: pygame.Surface,
    x: float,
    y: float,
    owner: int,
) -> None:
    """Draw a bullet dot colored by owner's team."""
    sx, sy = world_to_screen(x, y)
    color = SHIP_COLORS[owner % len(SHIP_COLORS)]
    # Slightly dimmer for bullets
    bullet_color = tuple(max(0, c - 60) for c in color)
    pygame.draw.circle(surface, bullet_color, (sx, sy), BULLET_RADIUS)


def run_visualizer(checkpoint_path: str | None = None, seed: int = 42) -> None:
    """Main visualization loop."""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Space Fight 2v2")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 18)

    n_ships = 4

    # Load policy if checkpoint provided
    policy = None
    if checkpoint_path is not None:
        try:
            import torch
            from spacefight.rl.policy import ActorCritic

            policy = ActorCritic()
            policy.load_state_dict(torch.load(checkpoint_path, weights_only=True))
            policy.eval()
            print(f"Loaded policy from {checkpoint_path}")
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
            print("Falling back to random actions.")
            policy = None

    rng = np.random.default_rng(seed)

    def make_state() -> SimState:
        return reset(n_envs=1, seed=int(rng.integers(0, 2**31)), n_ships=n_ships)

    state = make_state()
    paused = False
    outcome_text = ""

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    state = make_state()
                    outcome_text = ""

        if not paused and not state.done[0]:
            # Get actions
            if policy is not None:
                import torch
                from spacefight.rl.obs import build_egocentric_obs
                from spacefight.env.vec_env import build_critic_obs

                obs = build_egocentric_obs(state)
                obs_tensor = torch.from_numpy(obs)
                critic_obs_np = build_critic_obs(obs, n_ships)
                critic_obs_tensor = torch.from_numpy(critic_obs_np)
                with torch.no_grad():
                    actions_t, _, _, _ = policy.get_action_and_value(
                        obs_tensor, critic_obs_tensor
                    )
                actions = actions_t.numpy()
            else:
                # Random actions
                actions = np.zeros((1, n_ships, 4), dtype=np.int32)
                actions[:, :, 0] = rng.integers(-1, 2, size=(1, n_ships))
                actions[:, :, 1] = rng.integers(0, 2, size=(1, n_ships))
                actions[:, :, 2] = rng.integers(0, 2, size=(1, n_ships))
                actions[:, :, 3] = rng.integers(0, 2, size=(1, n_ships))

            state, rewards, dones = step(state, actions)

            if dones[0] and not outcome_text:
                # Check which team won
                team_0_alive = any(
                    state.alive[0, s] for s in range(n_ships) if state.team[0, s] == 0
                )
                team_1_alive = any(
                    state.alive[0, s] for s in range(n_ships) if state.team[0, s] == 1
                )
                if team_0_alive and not team_1_alive:
                    outcome_text = "BLUE TEAM WINS"
                elif team_1_alive and not team_0_alive:
                    outcome_text = "RED TEAM WINS"
                else:
                    outcome_text = "DRAW"

        # --- Render ---
        screen.fill(BG_COLOR)

        # Draw engagement zone circle
        zone_sx, zone_sy = world_to_screen(
            float(state.zone_cx[0]), float(state.zone_cy[0])
        )
        zone_screen_r = int(float(state.zone_r[0]) * SCALE)
        pygame.draw.circle(
            screen, (40, 60, 40), (zone_sx, zone_sy), zone_screen_r, 1
        )

        # Draw bullets
        for p in range(state.proj_alive.shape[1]):
            if state.proj_alive[0, p]:
                owner = int(state.proj_owner[0, p])
                draw_bullet(
                    screen,
                    float(state.proj_x[0, p]),
                    float(state.proj_y[0, p]),
                    owner,
                )

        # Draw ships
        max_hull = np.maximum(state.max_hull[0], 1e-8)
        for s in range(state.n_ships):
            draw_ship(
                screen,
                float(state.x[0, s]),
                float(state.y[0, s]),
                float(state.theta[0, s]),
                SHIP_COLORS[s % len(SHIP_COLORS)],
                bool(state.alive[0, s]),
            )
            hull_frac = float(state.hull[0, s] / max_hull[s])
            draw_hp_bar(
                screen,
                float(state.x[0, s]),
                float(state.y[0, s]),
                hull_frac,
            )

        # HUD
        tick_text = font.render(f"Tick: {int(state.tick[0])}", True, (200, 200, 200))
        screen.blit(tick_text, (10, 10))

        y_offset = 35
        for s in range(state.n_ships):
            name = TEAM_NAMES[s] if s < len(TEAM_NAMES) else f"Ship {s}"
            ammo_str = f"{state.ammo[0, s]}/{state.magazine_size}"
            reload_str = (
                f" R:{state.reload_timer[0, s]:.1f}s"
                if state.reload_timer[0, s] > 0
                else ""
            )
            hull_str = (
                f"{name} HP:{state.hull[0, s]:.0f}/{state.max_hull[0, s]:.0f}"
                f" Ammo:{ammo_str}{reload_str}"
            )
            color = SHIP_COLORS[s % len(SHIP_COLORS)]
            screen.blit(font.render(hull_str, True, color), (10, y_offset))
            y_offset += 20

        if paused:
            pause_surf = font.render("PAUSED", True, (255, 255, 0))
            screen.blit(pause_surf, (WINDOW_W // 2 - 40, 10))

        if outcome_text:
            out_surf = font.render(outcome_text, True, (255, 255, 255))
            screen.blit(
                out_surf,
                (WINDOW_W // 2 - out_surf.get_width() // 2, WINDOW_H // 2),
            )

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Space Fight 2v2 Visualizer")
    parser.add_argument("--checkpoint", type=str, default=None, help="Policy checkpoint .pt file")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run_visualizer(checkpoint_path=args.checkpoint, seed=args.seed)


if __name__ == "__main__":
    main()
