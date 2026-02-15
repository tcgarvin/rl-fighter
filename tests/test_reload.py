"""Tests for manual reload action."""

import numpy as np
import pytest

from spacefight.sim.core import DT, reset, step


def _make_state(n_envs=1, seed=0):
    """Create a default 2v2 state with fighters."""
    return reset(n_envs=n_envs, seed=seed)


def _zero_actions(n_envs=1, n_ships=4):
    """Create a no-op action array [N, S, 5]."""
    return np.zeros((n_envs, n_ships, 5), dtype=np.int32)


class TestManualReload:
    def test_manual_reload_starts_timer(self):
        """Sending reload with empty ammo should start the reload timer."""
        state = _make_state()
        state.ammo[0, 0] = 0  # empty magazine

        actions = _zero_actions()
        actions[0, 0, 4] = 1  # reload

        state, _, _ = step(state, actions)

        assert state.reload_timer[0, 0] > 0.0

    def test_reload_ignored_when_full(self):
        """Reload command with full ammo should be ignored."""
        state = _make_state()
        # ammo starts full (== magazine_size)

        actions = _zero_actions()
        actions[0, 0, 4] = 1  # reload

        state, _, _ = step(state, actions)

        assert state.reload_timer[0, 0] == 0.0

    def test_reload_completes_and_refills(self):
        """Stepping through the full reload cycle should refill ammo."""
        state = _make_state()
        state.ammo[0, 0] = 0
        mag_size = int(state.magazine_size[0, 0])
        reload_time = float(state.reload_time[0, 0])

        # Send reload once to start the timer
        actions = _zero_actions()
        actions[0, 0, 4] = 1
        state, _, _ = step(state, actions)
        assert state.reload_timer[0, 0] > 0.0

        # Step enough ticks to complete reload (no reload_cmd needed after start)
        ticks_needed = int(np.ceil(reload_time / DT)) + 1
        actions = _zero_actions()  # no reload command
        for _ in range(ticks_needed):
            state, _, _ = step(state, actions)

        assert state.ammo[0, 0] == mag_size
        assert state.reload_timer[0, 0] == 0.0

    def test_fire_during_reload_causes_self_damage(self):
        """Firing while reloading should deal 1 HP self-damage per tick."""
        state = _make_state()
        state.ammo[0, 0] = 0
        initial_hull = float(state.hull[0, 0])

        # Start reload
        actions = _zero_actions()
        actions[0, 0, 4] = 1
        state, _, _ = step(state, actions)
        assert state.reload_timer[0, 0] > 0.0

        # Now fire while reloading
        actions = _zero_actions()
        actions[0, 0, 3] = 1  # fire
        state, rewards, _ = step(state, actions)

        # Should have lost 1 HP
        assert float(state.hull[0, 0]) == pytest.approx(initial_hull - 1.0)
        # Agent should get negative reward for self-damage
        assert rewards[0, 0] < 0.0

    def test_reload_cannot_be_interrupted(self):
        """Reload timer keeps ticking even without reload_cmd."""
        state = _make_state()
        state.ammo[0, 0] = 0

        # Start reload
        actions = _zero_actions()
        actions[0, 0, 4] = 1
        state, _, _ = step(state, actions)
        timer_after_start = float(state.reload_timer[0, 0])

        # Step without reload command — timer should still tick down
        actions = _zero_actions()
        state, _, _ = step(state, actions)

        assert float(state.reload_timer[0, 0]) < timer_after_start
        assert state.reload_timer[0, 0] > 0.0  # not done yet (reload_time >> DT)

    def test_reload_not_interrupted_by_other_actions(self):
        """Firing and thrusting during reload don't cancel the reload."""
        state = _make_state()
        state.ammo[0, 0] = 0

        # Start reload
        actions = _zero_actions()
        actions[0, 0, 4] = 1
        state, _, _ = step(state, actions)
        timer_after_start = float(state.reload_timer[0, 0])

        # Thrust and fire during reload
        actions = _zero_actions()
        actions[0, 0, 1] = 1  # thrust
        actions[0, 0, 3] = 1  # fire
        state, _, _ = step(state, actions)

        # Timer should have decreased (not reset to 0)
        assert float(state.reload_timer[0, 0]) < timer_after_start
        assert state.reload_timer[0, 0] > 0.0

    def test_no_auto_reload_on_empty(self):
        """Emptying the magazine should NOT auto-start reload."""
        state = _make_state()
        state.ammo[0, 0] = 1  # one shot left

        # Fire the last shot
        actions = _zero_actions()
        actions[0, 0, 3] = 1  # fire
        state, _, _ = step(state, actions)

        # Ammo should be 0, but reload_timer should NOT have started
        assert state.ammo[0, 0] == 0
        assert state.reload_timer[0, 0] == 0.0
