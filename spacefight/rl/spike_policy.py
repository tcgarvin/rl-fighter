"""Masked multi-head MLP actor and critic for the learnability spike.

Spec: ``lab/runs/2026-10-28-learnability-spike/plan.md`` §3 (Policy, Critic) and
``docs/SIM_SPEC.md`` §7.1/§7.2. One ship's 385-d obs goes through a
385 → 256 → 256 tanh trunk into a single 61-logit layer, sliced into 21
independent categorical heads:

```
action col  head            logits         choices
[0..8)      throttle        [0..24)        3   (0 decrease, 1 hold, 2 increase)
[8..14)     slew            [24..42)       3   (0 left, 1 hold, 2 right)
[14..20)    fire            [42..54)       2
[20]        power           [54..61)       7
```

Head masking: a throttle head whose thruster slot is absent, a slew head whose
turret is absent or fixed, and a fire head whose turret is absent are *masked*.
Masked heads contribute exactly 0 log-prob and 0 entropy (and no gradient), and
their sampled values are overwritten with HOLD (throttle/slew) or 0 (fire), so the
action row is what the sim would do anyway. The power head is never masked.

Rows whose ``act_mask`` is false (SIM_SPEC §7.1: the row has no effect) are a
different, per-row mask; they are excluded from losses with ``masked_mean``.

The module does not import ``rlf_sim`` so checkpoints can be loaded without the
extension; ``tests/test_spike_policy.py`` checks the constants against it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

OBS_DIM = 385
ACTION_WIDTH = 21
N_LOGITS = 61
HIDDEN = 256

N_THRUSTERS = 8
N_TURRETS = 6
THROTTLE_HOLD = 1
SLEW_HOLD = 1
FIRE_NONE = 0

# Action columns per head group (SIM_SPEC §7.1 layout).
HEAD_GROUPS: dict[str, slice] = {
    "throttle": slice(0, 8),
    "slew": slice(8, 14),
    "fire": slice(14, 20),
    "power": slice(20, 21),
}
HEAD_CHOICES: dict[str, int] = {"throttle": 3, "slew": 3, "fire": 2, "power": 7}

# The 14 three-way heads (throttle then slew) are contiguous in both the action
# row and the logits, so they share one [B, 14, 3] log_softmax.
_N_TERNARY = 14
_TERNARY_LOGITS = slice(0, 42)
_FIRE_LOGITS = slice(42, 54)
_POWER_LOGITS = slice(54, 61)

# Value written into a masked head, per action column.
HOLD_ROW: tuple[int, ...] = (THROTTLE_HOLD,) * 8 + (SLEW_HOLD,) * 6 + (FIRE_NONE,) * 7
# Largest valid value per action column.
ACTION_HIGHS: tuple[int, ...] = (2,) * 14 + (1,) * 6 + (6,)

_ACTOR_OUTPUT_GAIN = 0.01
_CRITIC_OUTPUT_GAIN = 1.0
_HIDDEN_GAIN = math.sqrt(2.0)
_CHECKPOINT_FORMAT = "spike_policy/1"


def _flatten_leading(arr: np.ndarray, width: int, name: str) -> np.ndarray:
    if arr.shape[-1] != width:
        raise ValueError(f"{name} last axis must be {width}, got shape {arr.shape}")
    return arr.reshape(-1, width)


@dataclass(frozen=True)
class HeadMasks:
    """Static per-ship slot masks that decide which action heads are meaningful.

    Attributes:
        thruster: [B, 8] bool, True = thruster slot present.
        turret: [B, 6] bool, True = turret slot present.
        fixed_turret: [B, 6] bool, True = fixed gun (slew head meaningless).

    Raises:
        ValueError: Wrong shapes, dtypes, or mismatched batch sizes.
    """

    thruster: torch.Tensor
    turret: torch.Tensor
    fixed_turret: torch.Tensor

    def __post_init__(self) -> None:
        expected = {
            "thruster": N_THRUSTERS,
            "turret": N_TURRETS,
            "fixed_turret": N_TURRETS,
        }
        batch = self.thruster.shape[0] if self.thruster.dim() == 2 else -1
        for name, width in expected.items():
            mask = getattr(self, name)
            if mask.dtype != torch.bool:
                raise ValueError(f"{name} mask must be bool, got {mask.dtype}")
            if mask.dim() != 2 or mask.shape[1] != width or mask.shape[0] != batch:
                raise ValueError(
                    f"{name} mask must be [B, {width}] with a shared B, "
                    f"got {tuple(mask.shape)}"
                )

    @classmethod
    def from_numpy(
        cls, thruster: np.ndarray, turret: np.ndarray, fixed_turret: np.ndarray
    ) -> HeadMasks:
        """Build CPU masks from env arrays; leading axes (e.g. ``[N, S]``) are
        flattened to B in C order, matching ``obs.reshape(-1, OBS_DIM)``.
        """
        return cls(
            thruster=torch.from_numpy(
                _flatten_leading(np.asarray(thruster, dtype=np.bool_), 8, "thruster")
            ),
            turret=torch.from_numpy(
                _flatten_leading(np.asarray(turret, dtype=np.bool_), 6, "turret")
            ),
            fixed_turret=torch.from_numpy(
                _flatten_leading(
                    np.asarray(fixed_turret, dtype=np.bool_), 6, "fixed_turret"
                )
            ),
        )

    @property
    def batch_size(self) -> int:
        """Number of rows B."""
        return int(self.thruster.shape[0])

    def to(self, device: torch.device | str) -> HeadMasks:
        """Return the masks on ``device``."""
        return HeadMasks(
            thruster=self.thruster.to(device),
            turret=self.turret.to(device),
            fixed_turret=self.fixed_turret.to(device),
        )

    def index(self, rows: torch.Tensor) -> HeadMasks:
        """Return the masks of a subset of rows (e.g. a PPO minibatch)."""
        return HeadMasks(
            thruster=self.thruster[rows],
            turret=self.turret[rows],
            fixed_turret=self.fixed_turret[rows],
        )

    def head_valid(self) -> torch.Tensor:
        """[B, 21] bool: True where the action head is meaningful (not masked)."""
        slew = self.turret & ~self.fixed_turret
        power = torch.ones(
            (self.batch_size, 1), dtype=torch.bool, device=self.thruster.device
        )
        return torch.cat([self.thruster, slew, self.turret, power], dim=-1)


@dataclass(frozen=True)
class SampleOut:
    """Result of ``SpikeActor.sample``.

    Attributes:
        actions: [B, 21] int64; masked heads hold HOLD (throttle/slew) or 0 (fire).
        log_prob: [B] summed log-prob over unmasked heads.
        entropy: [B] summed entropy over unmasked heads.
    """

    actions: torch.Tensor
    log_prob: torch.Tensor
    entropy: torch.Tensor


@dataclass(frozen=True)
class _HeadLogSoftmax:
    ternary: torch.Tensor  # [B, 14, 3]
    fire: torch.Tensor  # [B, 6, 2]
    power: torch.Tensor  # [B, 7]

    @classmethod
    def from_logits(cls, logits: torch.Tensor) -> _HeadLogSoftmax:
        batch = logits.shape[0]
        return cls(
            ternary=F.log_softmax(
                logits[:, _TERNARY_LOGITS].reshape(batch, _N_TERNARY, 3), dim=-1
            ),
            fire=F.log_softmax(
                logits[:, _FIRE_LOGITS].reshape(batch, N_TURRETS, 2), dim=-1
            ),
            power=F.log_softmax(logits[:, _POWER_LOGITS], dim=-1),
        )

    def gather(self, actions: torch.Tensor) -> torch.Tensor:
        """[B, 21] log-prob of each head's chosen value (no masking)."""
        ternary = self.ternary.gather(-1, actions[:, :14, None]).squeeze(-1)
        fire = self.fire.gather(-1, actions[:, 14:20, None]).squeeze(-1)
        power = self.power.gather(-1, actions[:, 20:21])
        return torch.cat([ternary, fire, power], dim=-1)

    def entropy(self) -> torch.Tensor:
        """[B, 21] entropy of each head (no masking)."""
        ternary = -(self.ternary.exp() * self.ternary).sum(-1)
        fire = -(self.fire.exp() * self.fire).sum(-1)
        power = -(self.power.exp() * self.power).sum(-1, keepdim=True)
        return torch.cat([ternary, fire, power], dim=-1)

    def mean_log_prob(self) -> torch.Tensor:
        """[B, 21] mean log-prob over each head's choices (for label smoothing)."""
        ternary = self.ternary.mean(-1)
        fire = self.fire.mean(-1)
        power = self.power.mean(-1, keepdim=True)
        return torch.cat([ternary, fire, power], dim=-1)

    def sample(self, deterministic: bool) -> torch.Tensor:
        """[B, 21] int64 raw samples (argmax if deterministic)."""
        if deterministic:
            return torch.cat(
                [
                    self.ternary.argmax(-1),
                    self.fire.argmax(-1),
                    self.power.argmax(-1, keepdim=True),
                ],
                dim=-1,
            )
        batch = self.power.shape[0]
        ternary = torch.multinomial(self.ternary.exp().reshape(-1, 3), 1)
        fire = torch.multinomial(self.fire.exp().reshape(-1, 2), 1)
        power = torch.multinomial(self.power.exp(), 1)
        return torch.cat(
            [
                ternary.reshape(batch, _N_TERNARY),
                fire.reshape(batch, N_TURRETS),
                power,
            ],
            dim=-1,
        )


def _hold_row(device: torch.device) -> torch.Tensor:
    return torch.tensor(HOLD_ROW, dtype=torch.int64, device=device)


def _check_obs(obs: torch.Tensor) -> None:
    if obs.dim() != 2 or obs.shape[1] != OBS_DIM:
        raise ValueError(f"obs must be [B, {OBS_DIM}], got {tuple(obs.shape)}")


def _mlp(hidden: int, out_dim: int, output_gain: float) -> nn.Sequential:
    net = nn.Sequential(
        nn.Linear(OBS_DIM, hidden),
        nn.Tanh(),
        nn.Linear(hidden, hidden),
        nn.Tanh(),
        nn.Linear(hidden, out_dim),
    )
    linears = [m for m in net if isinstance(m, nn.Linear)]
    for layer in linears:
        gain = output_gain if layer is linears[-1] else _HIDDEN_GAIN
        nn.init.orthogonal_(layer.weight, gain=gain)
        nn.init.zeros_(layer.bias)
    return net


class SpikeActor(nn.Module):
    """Decentralised actor: one ship's obs → 21 masked categorical heads.

    Args:
        hidden: Width of both hidden layers.
    """

    def __init__(self, hidden: int = HIDDEN) -> None:
        super().__init__()
        self.hidden = hidden
        self.net = _mlp(hidden, N_LOGITS, _ACTOR_OUTPUT_GAIN)

    @property
    def logits_layer(self) -> nn.Linear:
        """The final 61-logit linear layer."""
        layer = self.net[-1]
        if not isinstance(layer, nn.Linear):
            raise TypeError(f"last layer is {type(layer).__name__}, not Linear")
        return layer

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        """Return raw logits [B, 61] for obs [B, 385]."""
        _check_obs(obs)
        out: torch.Tensor = self.net(obs)
        return out

    def _heads(self, obs: torch.Tensor, masks: HeadMasks) -> _HeadLogSoftmax:
        if masks.batch_size != obs.shape[0]:
            raise ValueError(
                f"masks have {masks.batch_size} rows, obs has {obs.shape[0]}"
            )
        return _HeadLogSoftmax.from_logits(self(obs))

    def sample(
        self, obs: torch.Tensor, masks: HeadMasks, deterministic: bool = False
    ) -> SampleOut:
        """Sample one action row per obs row.

        Args:
            obs: [B, 385] float observations.
            masks: Slot masks for the same B rows.
            deterministic: Take the argmax of every head instead of sampling.

        Returns:
            Actions with masked heads overwritten by HOLD / 0, and their summed
            log-prob and entropy (masked heads contribute 0).
        """
        heads = self._heads(obs, masks)
        valid = masks.head_valid()
        raw = heads.sample(deterministic)
        actions = torch.where(valid, raw, _hold_row(raw.device))
        log_prob, entropy = _masked_head_terms(heads, valid, actions)
        return SampleOut(
            actions=actions, log_prob=log_prob.sum(-1), entropy=entropy.sum(-1)
        )

    def evaluate_heads(
        self, obs: torch.Tensor, masks: HeadMasks, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Per-head log-prob and entropy of ``actions``, one forward pass.

        Values in masked heads are ignored (env labels may hold 0 there).

        Returns:
            ``(log_prob [B, 21], entropy [B, 21])``, both exactly 0 where masked.

        Raises:
            ValueError: Wrong action shape, non-integer dtype, or an unmasked head
                value out of range.
        """
        heads = self._heads(obs, masks)
        valid = masks.head_valid()
        safe = _checked_actions(actions, valid)
        return _masked_head_terms(heads, valid, safe)

    def evaluate(
        self, obs: torch.Tensor, masks: HeadMasks, actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ``(log_prob [B], entropy [B])`` of ``actions``, summed over heads."""
        log_prob, entropy = self.evaluate_heads(obs, masks, actions)
        return log_prob.sum(-1), entropy.sum(-1)

    def head_log_probs(
        self, obs: torch.Tensor, masks: HeadMasks, actions: torch.Tensor
    ) -> torch.Tensor:
        """[B, 21] per-head log-probs of ``actions``, exactly 0 where masked."""
        return self.evaluate_heads(obs, masks, actions)[0]

    def head_entropy(self, obs: torch.Tensor, masks: HeadMasks) -> torch.Tensor:
        """[B, 21] per-head entropy, exactly 0 where masked."""
        heads = self._heads(obs, masks)
        valid = masks.head_valid()
        return torch.where(valid, heads.entropy(), 0.0)

    def head_cross_entropy(
        self,
        obs: torch.Tensor,
        masks: HeadMasks,
        actions: torch.Tensor,
        label_smoothing: float = 0.0,
    ) -> torch.Tensor:
        """[B, 21] per-head cross-entropy to label ``actions``, 0 where masked.

        With smoothing ε the target is ``(1 − ε)·onehot + ε·uniform`` over that
        head's choices (plan §4.1 uses ε = 0.02 for BC).

        Raises:
            ValueError: ``label_smoothing`` outside [0, 1), or bad actions.
        """
        if not 0.0 <= label_smoothing < 1.0:
            raise ValueError(
                f"label_smoothing must be in [0, 1), got {label_smoothing}"
            )
        heads = self._heads(obs, masks)
        valid = masks.head_valid()
        safe = _checked_actions(actions, valid)
        nll = -(
            (1.0 - label_smoothing) * heads.gather(safe)
            + label_smoothing * heads.mean_log_prob()
        )
        return torch.where(valid, nll, 0.0)


class SpikeCritic(nn.Module):
    """State-value critic on one ship's own obs (no centralised critic for 1v1).

    Args:
        hidden: Width of both hidden layers.
    """

    def __init__(self, hidden: int = HIDDEN) -> None:
        super().__init__()
        self.hidden = hidden
        self.net = _mlp(hidden, 1, _CRITIC_OUTPUT_GAIN)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        """Return values [B] for obs [B, 385]."""
        _check_obs(obs)
        out: torch.Tensor = self.net(obs).squeeze(-1)
        return out


def _checked_actions(actions: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
    """Validate unmasked heads and return int64 actions with masked heads at HOLD."""
    if actions.shape != valid.shape:
        raise ValueError(
            f"actions must be [B, {ACTION_WIDTH}] = {tuple(valid.shape)}, "
            f"got {tuple(actions.shape)}"
        )
    if actions.dtype.is_floating_point or actions.dtype == torch.bool:
        raise ValueError(f"actions must be an integer tensor, got {actions.dtype}")
    actions = actions.to(torch.int64)
    highs = torch.tensor(ACTION_HIGHS, dtype=torch.int64, device=actions.device)
    out_of_range = valid & ((actions < 0) | (actions > highs))
    if bool(out_of_range.any()):
        rows, cols = torch.nonzero(out_of_range, as_tuple=True)
        raise ValueError(
            f"action values out of range at (row, col) "
            f"{list(zip(rows.tolist()[:5], cols.tolist()[:5]))}"
        )
    return torch.where(valid, actions, _hold_row(actions.device))


def _masked_head_terms(
    heads: _HeadLogSoftmax, valid: torch.Tensor, actions: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    # torch.where (not multiplication) so masked heads get exactly 0 and no gradient.
    log_prob = torch.where(valid, heads.gather(actions), 0.0)
    entropy = torch.where(valid, heads.entropy(), 0.0)
    return log_prob, entropy


def masked_mean(values: torch.Tensor, row_mask: torch.Tensor) -> torch.Tensor:
    """Mean of ``values`` over rows where ``row_mask`` is True; 0 if there are none.

    Use with ``act_mask`` to drop rows that have no effect (SIM_SPEC §7.1). Masked
    rows contribute no gradient even if their values are non-finite.

    Args:
        values: [B] or [B, ...] tensor.
        row_mask: [B] bool.
    """
    if row_mask.dtype != torch.bool or row_mask.shape != values.shape[:1]:
        raise ValueError(
            f"row_mask must be bool [{values.shape[0]}], got "
            f"{row_mask.dtype} {tuple(row_mask.shape)}"
        )
    mask = row_mask.reshape(-1, *([1] * (values.dim() - 1))).expand_as(values)
    total = torch.where(mask, values, 0.0).sum()
    count = mask.sum().clamp(min=1)
    return total / count


def mean_head_entropy(
    head_entropy: torch.Tensor, head_valid: torch.Tensor
) -> torch.Tensor:
    """[B] entropy averaged over each row's unmasked heads (PPO's per-head mean)."""
    count = head_valid.sum(-1).clamp(min=1)
    return torch.where(head_valid, head_entropy, 0.0).sum(-1) / count


def group_entropy(
    head_entropy: torch.Tensor, head_valid: torch.Tensor, row_mask: torch.Tensor
) -> dict[str, torch.Tensor]:
    """Mean entropy per unmasked head in each head group, over rows in ``row_mask``.

    Args:
        head_entropy: [B, 21] from ``SpikeActor.head_entropy`` / ``evaluate_heads``.
        head_valid: [B, 21] from ``HeadMasks.head_valid``.
        row_mask: [B] bool, e.g. ``act_mask``.

    Returns:
        ``{"throttle", "slew", "fire", "power"} -> scalar tensor``. A group with no
        unmasked head in any selected row (e.g. slew on the fighter's fixed gun)
        reports 0; ``group_head_counts`` tells it apart from a collapsed head.
    """
    valid = head_valid & row_mask[:, None]
    out: dict[str, torch.Tensor] = {}
    for name, cols in HEAD_GROUPS.items():
        group_valid = valid[:, cols]
        total = torch.where(group_valid, head_entropy[:, cols], 0.0).sum()
        out[name] = total / group_valid.sum().clamp(min=1)
    return out


def group_head_counts(head_valid: torch.Tensor) -> dict[str, int]:
    """Number of unmasked heads per group in the first row (static per hull)."""
    return {name: int(head_valid[0, cols].sum()) for name, cols in HEAD_GROUPS.items()}


def act_numpy(
    actor: SpikeActor,
    obs: np.ndarray,
    masks: HeadMasks,
    deterministic: bool = False,
) -> np.ndarray:
    """Sample env-ready int8 actions without building a graph.

    Args:
        actor: The policy.
        obs: [..., 385] float observations (e.g. ``env.obs`` of shape [N, S, 385]).
        masks: Masks for the flattened rows (``HeadMasks.from_numpy`` of the env
            masks); moved to the actor's device.
        deterministic: Argmax instead of sampling.

    Returns:
        int8 actions of shape ``obs.shape[:-1] + (21,)``.
    """
    flat = _flatten_leading(np.asarray(obs, dtype=np.float32), OBS_DIM, "obs")
    device = next(actor.parameters()).device
    with torch.no_grad():
        out = actor.sample(
            torch.from_numpy(flat).to(device), masks.to(device), deterministic
        )
    actions = out.actions.to(torch.int8).cpu().numpy()
    return actions.reshape(*obs.shape[:-1], ACTION_WIDTH)


def save_policy(
    path: Path, actor: SpikeActor, critic: SpikeCritic, meta: dict[str, object]
) -> None:
    """Write actor, critic and ``meta`` to ``path`` (``torch.save``).

    ``meta`` must hold only plain types (str, int, float, bool, lists, dicts) so the
    file loads with ``weights_only=True``.
    """
    payload = {
        "format": _CHECKPOINT_FORMAT,
        "actor_hidden": actor.hidden,
        "critic_hidden": critic.hidden,
        "actor": actor.state_dict(),
        "critic": critic.state_dict(),
        "meta": dict(meta),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_policy(path: Path) -> tuple[SpikeActor, SpikeCritic, dict[str, object]]:
    """Load a checkpoint written by ``save_policy`` onto the CPU.

    Raises:
        ValueError: The file is not a spike-policy checkpoint.
    """
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or payload.get("format") != _CHECKPOINT_FORMAT:
        raise ValueError(f"{path} is not a {_CHECKPOINT_FORMAT} checkpoint")
    actor = SpikeActor(hidden=int(payload["actor_hidden"]))
    critic = SpikeCritic(hidden=int(payload["critic_hidden"]))
    actor.load_state_dict(payload["actor"])
    critic.load_state_dict(payload["critic"])
    meta: dict[str, object] = dict(payload["meta"])
    return actor, critic, meta


def param_count(module: nn.Module) -> int:
    """Number of trainable parameters."""
    return sum(p.numel() for p in module.parameters() if p.requires_grad)
