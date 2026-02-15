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
import random
import sys

import numpy as np
import pygame

from spacefight.sim.core import SimState, load_hulls, reset, step

# Display constants (WINDOW_W, WINDOW_H, SCALE are set dynamically at startup)
WINDOW_W = 1200  # default fallback, overwritten by run_visualizer
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
BASE_SHIP_SIZE = 14  # reference half-length (scaled per hull radius)
REFERENCE_RADIUS = 18.0  # "fighter" radius used as the 1x baseline

# Hull type abbreviations for HUD
HULL_ABBREVS = {
    "interceptor": "INT",
    "fighter": "FTR",
    "gunboat": "GUN",
    "bomber": "BMR",
}

# HP bar
HP_BAR_W = 40
HP_BAR_H = 5
HP_BAR_OFFSET = 20  # pixels above ship

# World-to-screen transform: center the arena
WORLD_CENTER_X = 0.0
WORLD_CENTER_Y = 0.0
WORLD_EXTENT = 1200.0  # half-width of visible world (fits zone + spawn + margin)
SCALE = 0.45  # default fallback, overwritten by run_visualizer
SCREEN_FRACTION = 0.9  # use 90% of display dimensions


def world_to_screen(wx: float, wy: float) -> tuple[int, int]:
    """Convert world coordinates to screen pixel coordinates."""
    sx = int(WINDOW_W / 2 + (wx - WORLD_CENTER_X) * SCALE)
    sy = int(WINDOW_H / 2 - (wy - WORLD_CENTER_Y) * SCALE)  # flip Y
    return sx, sy


def _rotated_point(
    sx: int, sy: int, size: float, theta: float, local_angle: float, local_r: float
) -> tuple[int, int]:
    """Compute a screen-space point rotated around (sx, sy)."""
    angle = theta + local_angle
    return (
        sx + int(size * local_r * math.cos(angle)),
        sy - int(size * local_r * math.sin(angle)),
    )


def _ship_vertices_interceptor(
    sx: int, sy: int, size: float, theta: float
) -> list[tuple[int, int]]:
    """Narrow/pointy triangle for interceptor (fast, small)."""
    nose = (sx + int(size * 1.2 * math.cos(theta)),
            sy - int(size * 1.2 * math.sin(theta)))
    left = _rotated_point(sx, sy, size, theta, 2.6, 0.5)
    right = _rotated_point(sx, sy, size, theta, -2.6, 0.5)
    return [nose, left, right]


def _ship_vertices_fighter(
    sx: int, sy: int, size: float, theta: float
) -> list[tuple[int, int]]:
    """Standard triangle for fighter (default shape)."""
    nose = (sx + int(size * math.cos(theta)),
            sy - int(size * math.sin(theta)))
    left = _rotated_point(sx, sy, size, theta, 2.4, 0.6)
    right = _rotated_point(sx, sy, size, theta, -2.4, 0.6)
    return [nose, left, right]


def _ship_vertices_gunboat(
    sx: int, sy: int, size: float, theta: float
) -> list[tuple[int, int]]:
    """Wide/blunt pentagon for gunboat — elongated along heading for clarity."""
    nose = (sx + int(size * 1.0 * math.cos(theta)),
            sy - int(size * 1.0 * math.sin(theta)))
    fl = _rotated_point(sx, sy, size, theta, 1.0, 0.6)
    fr = _rotated_point(sx, sy, size, theta, -1.0, 0.6)
    bl = _rotated_point(sx, sy, size, theta, 2.3, 0.7)
    br = _rotated_point(sx, sy, size, theta, -2.3, 0.7)
    return [nose, fl, bl, br, fr]


def _ship_vertices_bomber(
    sx: int, sy: int, size: float, theta: float
) -> list[tuple[int, int]]:
    """Diamond/kite shape for bomber."""
    nose = (sx + int(size * 1.0 * math.cos(theta)),
            sy - int(size * 1.0 * math.sin(theta)))
    left = _rotated_point(sx, sy, size, theta, math.pi / 2, 0.55)
    tail = _rotated_point(sx, sy, size, theta, math.pi, 0.7)
    right = _rotated_point(sx, sy, size, theta, -math.pi / 2, 0.55)
    return [nose, left, tail, right]


_HULL_SHAPE_FN = {
    "interceptor": _ship_vertices_interceptor,
    "fighter": _ship_vertices_fighter,
    "gunboat": _ship_vertices_gunboat,
    "bomber": _ship_vertices_bomber,
}


def draw_ship(
    surface: pygame.Surface,
    x: float,
    y: float,
    theta: float,
    color: tuple[int, int, int],
    alive: bool,
    hull_type: str = "fighter",
    radius: float = REFERENCE_RADIUS,
) -> None:
    """Draw a ship using a hull-type-specific polygon scaled by radius."""
    draw_color = color if alive else DEAD_COLOR
    sx, sy = world_to_screen(x, y)
    size = BASE_SHIP_SIZE * (radius / REFERENCE_RADIUS)
    shape_fn = _HULL_SHAPE_FN.get(hull_type, _ship_vertices_fighter)
    vertices = shape_fn(sx, sy, size, theta)
    pygame.draw.polygon(surface, draw_color, vertices)


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


# --- Explosion visual effects ---

# Hit explosion: small, fast flash
HIT_EXPLOSION_RADIUS = 6.0  # max screen-space radius
HIT_EXPLOSION_DURATION = 8  # ticks (~0.27s at 30 Hz)

# Death explosion: multiple bursts around the hull
DEATH_EXPLOSION_RADIUS = 9.0
DEATH_EXPLOSION_DURATION = 10  # ticks per burst
DEATH_BURST_COUNT = 8  # total bursts to spawn
DEATH_BURST_SPREAD = 1.5  # seconds over which bursts appear
DEATH_BURST_SCATTER = 30.0  # world-space scatter radius around ship center


class Explosion:
    """A single explosion effect fixed in world space."""

    __slots__ = ("wx", "wy", "age", "max_radius", "duration")

    def __init__(self, wx: float, wy: float, max_radius: float, duration: int) -> None:
        self.wx = wx
        self.wy = wy
        self.age = 0
        self.max_radius = max_radius
        self.duration = duration

    @property
    def alive(self) -> bool:
        return self.age < self.duration

    def tick(self) -> None:
        self.age += 1

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        t = self.age / self.duration  # 0..1
        # Radius: quick expand then hold
        r = self.max_radius * min(1.0, t * 4.0)
        # Alpha: bright at start, fading out
        alpha = max(0, int(255 * (1.0 - t)))
        if alpha <= 0 or r < 1:
            return
        sx, sy = world_to_screen(self.wx, self.wy)
        # Draw filled circle with fading color (yellow -> orange -> dark)
        color = (
            min(255, 255),
            min(255, int(200 * (1.0 - t * 0.5))),
            max(0, int(60 * (1.0 - t))),
        )
        # Use a surface with per-pixel alpha for smooth fade
        diameter = int(r * 2) + 2
        if diameter < 2:
            return
        circle_surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            circle_surf, (*color, alpha), (diameter // 2, diameter // 2), int(r)
        )
        surface.blit(circle_surf, (sx - diameter // 2, sy - diameter // 2))


class ExplosionManager:
    """Manages all active explosions."""

    def __init__(self) -> None:
        self.explosions: list[Explosion] = []
        # Pending death bursts: list of (wx, wy, ticks_remaining, scatter_radius)
        self._death_queues: list[tuple[float, float, int, float]] = []

    def spawn_hit(self, wx: float, wy: float) -> None:
        """Spawn a small hit explosion at the given world position."""
        self.explosions.append(
            Explosion(wx, wy, HIT_EXPLOSION_RADIUS, HIT_EXPLOSION_DURATION)
        )

    def spawn_death(self, wx: float, wy: float, hull_radius: float) -> None:
        """Queue a series of explosions around a destroyed ship."""
        scatter = max(DEATH_BURST_SCATTER, hull_radius * 1.5)
        total_ticks = int(DEATH_BURST_SPREAD * FPS)
        for _ in range(DEATH_BURST_COUNT):
            delay = random.randint(0, total_ticks)
            ox = random.gauss(0, scatter * 0.5)
            oy = random.gauss(0, scatter * 0.5)
            self._death_queues.append((wx + ox, wy + oy, delay, DEATH_EXPLOSION_RADIUS))

    def tick(self) -> None:
        """Advance all explosions and spawn pending death bursts."""
        # Process death queues
        remaining = []
        for wx, wy, ticks_left, radius in self._death_queues:
            if ticks_left <= 0:
                self.explosions.append(
                    Explosion(wx, wy, radius, DEATH_EXPLOSION_DURATION)
                )
            else:
                remaining.append((wx, wy, ticks_left - 1, radius))
        self._death_queues = remaining

        # Tick and prune active explosions
        for e in self.explosions:
            e.tick()
        self.explosions = [e for e in self.explosions if e.alive]

    def draw(self, surface: pygame.Surface) -> None:
        for e in self.explosions:
            e.draw(surface)

    def clear(self) -> None:
        self.explosions.clear()
        self._death_queues.clear()


RESPAWN_DELAY_TICKS = 60  # 2 seconds at 30 Hz
RESPAWN_ZONE_PAD = 200.0  # spawn 200–400 units outside zone edge


def _update_respawns(
    state: SimState,
    respawn_timers: NDArray[np.int32],
    hulls_data: dict,
    hull_types: list[str],
    rng: np.random.Generator,
) -> None:
    """Track respawn countdowns and respawn ships outside the zone when ready."""
    for s in range(state.n_ships):
        if not state.alive[0, s]:
            if respawn_timers[s] <= 0:
                # Just died — start countdown
                respawn_timers[s] = RESPAWN_DELAY_TICKS
            else:
                respawn_timers[s] -= 1
                if respawn_timers[s] <= 0:
                    # Pick a random hull type
                    new_hull = str(rng.choice(hull_types))
                    h = hulls_data[new_hull]
                    state.hull_names[s] = new_hull
                    state.max_hull[0, s] = h["hp"]
                    state.radius[0, s] = h["radius"]
                    state.max_speed[0, s] = h["speed"]
                    state.turn_rate[0, s] = math.radians(h["turn_rate"])
                    state.thrust_accel[0, s] = h["thrust"]

                    # Respawn outside the engagement zone, aimed inward
                    state.alive[0, s] = True
                    state.hull[0, s] = h["hp"]
                    angle = rng.uniform(0, 2 * math.pi)
                    zone_r = float(state.zone_r[0])
                    dist = zone_r + rng.uniform(RESPAWN_ZONE_PAD, RESPAWN_ZONE_PAD * 2)
                    state.x[0, s] = float(state.zone_cx[0]) + dist * math.cos(angle)
                    state.y[0, s] = float(state.zone_cy[0]) + dist * math.sin(angle)
                    state.vx[0, s] = 0.0
                    state.vy[0, s] = 0.0
                    # Face toward zone center
                    state.theta[0, s] = angle + math.pi
                    # Reset weapon state
                    state.cooldown[0, s] = 0.0
                    state.ammo[0, s] = state.magazine_size
                    state.reload_timer[0, s] = 0.0


def run_visualizer(checkpoint_path: str | None = None, seed: int = 42, demo: bool = False) -> None:
    """Main visualization loop."""
    global WINDOW_W, WINDOW_H, SCALE

    pygame.init()

    # Size window to 90% of the active display
    display_info = pygame.display.Info()
    WINDOW_W = int(display_info.current_w * SCREEN_FRACTION)
    WINDOW_H = int(display_info.current_h * SCREEN_FRACTION)

    # Compute scale so that ±WORLD_EXTENT fits in both axes
    SCALE = min(WINDOW_W / 2, WINDOW_H / 2) / WORLD_EXTENT

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
    hulls_data = load_hulls()
    hull_types = list(hulls_data.keys())

    def make_state() -> SimState:
        hull_names = [str(rng.choice(hull_types)) for _ in range(n_ships)]
        return reset(
            n_envs=1,
            hull_names=hull_names,
            seed=int(rng.integers(0, 2**31)),
            n_ships=n_ships,
        )

    state = make_state()
    respawn_timers = np.zeros(n_ships, dtype=np.int32)
    explosions = ExplosionManager()
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
                    respawn_timers[:] = 0
                    explosions.clear()
                    outcome_text = ""

        if not paused and (demo or not state.done[0]):
            # In demo mode, keep the episode alive
            if demo:
                state.done[0] = False

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

            # Snapshot state before step for hit/death detection
            prev_alive = state.alive[0].copy()
            prev_proj_alive = state.proj_alive[0].copy()

            state, rewards, dones = step(state, actions)

            # Find projectiles that just died (hit a ship or expired)
            newly_dead_projs = prev_proj_alive & ~state.proj_alive[0]
            dead_indices = np.where(newly_dead_projs)[0]

            # For each newly dead projectile near a ship, spawn hit explosion
            # at the projectile's position (where it intersected the hull)
            for p_idx in dead_indices:
                px = float(state.proj_x[0, p_idx])
                py = float(state.proj_y[0, p_idx])
                # Check if this projectile is within any ship's radius
                for s in range(n_ships):
                    if not state.alive[0, s] and not prev_alive[s]:
                        continue
                    dx = px - float(state.x[0, s])
                    dy = py - float(state.y[0, s])
                    r = float(state.radius[0, s])
                    if dx * dx + dy * dy < r * r * 4:  # generous check
                        explosions.spawn_hit(px, py)
                        break

            # Detect deaths
            for s in range(n_ships):
                if prev_alive[s] and not state.alive[0, s]:
                    explosions.spawn_death(
                        float(state.x[0, s]),
                        float(state.y[0, s]),
                        float(state.radius[0, s]),
                    )

            # Demo mode: tick respawn timers and respawn when ready
            if demo:
                _update_respawns(state, respawn_timers, hulls_data, hull_types, rng)

            if not demo and dones[0] and not outcome_text:
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

        # Tick explosions even when sim is paused (so they fade out)
        explosions.tick()

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
                hull_type=state.hull_names[s],
                radius=float(state.radius[0, s]),
            )
            hull_frac = float(state.hull[0, s] / max_hull[s])
            draw_hp_bar(
                screen,
                float(state.x[0, s]),
                float(state.y[0, s]),
                hull_frac,
            )

        # Draw explosions
        explosions.draw(screen)

        # HUD
        tick_text = font.render(f"Tick: {int(state.tick[0])}", True, (200, 200, 200))
        screen.blit(tick_text, (10, 10))

        y_offset = 35
        for s in range(state.n_ships):
            name = TEAM_NAMES[s] if s < len(TEAM_NAMES) else f"Ship {s}"
            hull_abbrev = HULL_ABBREVS.get(state.hull_names[s], "???")
            ammo_str = f"{state.ammo[0, s]}/{state.magazine_size}"
            reload_str = (
                f" R:{state.reload_timer[0, s]:.1f}s"
                if state.reload_timer[0, s] > 0
                else ""
            )
            hull_str = (
                f"{name} [{hull_abbrev}]"
                f" HP:{state.hull[0, s]:.0f}/{state.max_hull[0, s]:.0f}"
                f" Ammo:{ammo_str}{reload_str}"
            )
            color = SHIP_COLORS[s % len(SHIP_COLORS)]
            screen.blit(font.render(hull_str, True, color), (10, y_offset))
            y_offset += 20

        if demo:
            demo_surf = font.render("DEMO", True, (255, 200, 0))
            screen.blit(demo_surf, (WINDOW_W - demo_surf.get_width() - 10, 10))

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
    parser.add_argument("--demo", action="store_true", help="Demo mode: respawn destroyed ships for endless combat")
    args = parser.parse_args()
    run_visualizer(checkpoint_path=args.checkpoint, seed=args.seed, demo=args.demo)


if __name__ == "__main__":
    main()
