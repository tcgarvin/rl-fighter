"""The commander's actor and critic (docs/COMMANDER.md "Network").

Both share a shape (a trunk): a per-entity encoder, one self-attention layer over the
valid entities, and a pooled summary joined with the globals. The actor puts its heads
on the trunk; the critic, used only in training, also sees which pilot flies each ship
and puts a value head on its own trunk. Attention is written out by hand, not with
``nn.MultiheadAttention``, so the browser can mirror it line by line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import torch
from torch import nn
from torch.distributions import Categorical

from spacefight.commander.io import (
    ACTION_DIM,
    ATTACK_TARGET,
    COMMANDER_IO_VERSION,
    DEFEND_WARD,
    ENTITY_DIM,
    GLOBAL_DIM,
    GOTO_POINT,
    LAUNCH,
    MAX_ENTITIES,
    N_LAUNCH_HULLS,
    N_ORDER_CHOICES,
    N_POINTS,
    N_SQUAD_CHOICES,
    N_SQUADS,
    N_WAYPOINT_CHOICES,
    ORDER,
    ORDER_ATTACK,
    ORDER_DEFEND,
    ORDER_GOTO,
    SQUAD_GLOBAL_DIM,
    SQUAD_GLOBALS,
    SQUAD_OF_SLOT,
    WAYPOINT,
    CommanderInputs,
)

WIDTH: Final = 64
SUMMARY: Final = 128
HEADS: Final = 4
SQUAD_EMBED: Final = 32
# A masked-out logit: finite, so an all-masked row cannot make NaNs.
MASKED: Final = -1.0e9
CHECKPOINT_FORMAT: Final = "rlf.commander/1"


class Trunk(nn.Module):
    """Entity encoder, one attention layer, pooled summary.

    Args:
        entity_dim: Width of each entity's input row.
    """

    def __init__(self, entity_dim: int = ENTITY_DIM) -> None:
        super().__init__()
        self.entity_dim = entity_dim
        self.encode = nn.Sequential(
            nn.Linear(entity_dim, WIDTH),
            nn.Tanh(),
            nn.Linear(WIDTH, WIDTH),
            nn.Tanh(),
        )
        self.q = nn.Linear(WIDTH, WIDTH)
        self.k = nn.Linear(WIDTH, WIDTH)
        self.v = nn.Linear(WIDTH, WIDTH)
        self.o = nn.Linear(WIDTH, WIDTH)
        self.summary = nn.Sequential(nn.Linear(WIDTH + GLOBAL_DIM, SUMMARY), nn.Tanh())

    def forward(
        self, globals_: torch.Tensor, entities: torch.Tensor, valid: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """``(entity vectors [B, E, WIDTH], summary [B, SUMMARY])``."""
        b, e, _ = entities.shape
        # A row with no valid entity (cannot happen in a running match) attends to
        # slot 0 rather than to nothing.
        valid = valid.clone()
        valid[:, 0] |= ~valid.any(dim=1)
        h = self.encode(entities)
        d = WIDTH // HEADS
        q = self.q(h).view(b, e, HEADS, d).transpose(1, 2)
        k = self.k(h).view(b, e, HEADS, d).transpose(1, 2)
        v = self.v(h).view(b, e, HEADS, d).transpose(1, 2)
        scores = q @ k.transpose(-1, -2) / math.sqrt(d)
        scores = scores.masked_fill(~valid[:, None, None, :], MASKED)
        mixed = (scores.softmax(dim=-1) @ v).transpose(1, 2).reshape(b, e, WIDTH)
        h = h + self.o(mixed)
        w = valid.to(h.dtype).unsqueeze(-1)
        pooled = (h * w).sum(dim=1) / w.sum(dim=1).clamp(min=1.0)
        return h, self.summary(torch.cat([pooled, globals_], dim=-1))


@dataclass
class HeadLogits:
    """Masked logits of every head.

    Attributes:
        launch: [B, 3, 2]. waypoint: [B, 26]. squad: [B, 20, 6]. order: [B, 4, 5].
        target: [B, 4, 20]. ward: [B, 4, 20]. point: [B, 4, 25].
    """

    launch: torch.Tensor
    waypoint: torch.Tensor
    squad: torch.Tensor
    order: torch.Tensor
    target: torch.Tensor
    ward: torch.Tensor
    point: torch.Tensor


def _masked(logits: torch.Tensor, allowed: torch.Tensor) -> torch.Tensor:
    """``logits`` with disallowed choices at ``MASKED``. A row with nothing allowed
    keeps choice 0, so its distribution is defined (such a head is never counted)."""
    allowed = allowed.clone()
    allowed[..., 0] |= ~allowed.any(dim=-1)
    return logits.masked_fill(~allowed, MASKED)


class CommanderActor(nn.Module):
    """The commander: a ``Trunk`` and the heads of docs/COMMANDER.md "Outputs"."""

    def __init__(self) -> None:
        super().__init__()
        self.trunk = Trunk(ENTITY_DIM)
        self.launch = nn.Linear(SUMMARY, N_LAUNCH_HULLS * 2)
        self.waypoint = nn.Linear(SUMMARY, N_WAYPOINT_CHOICES)
        self.squad = nn.Sequential(
            nn.Linear(WIDTH + SUMMARY, WIDTH),
            nn.Tanh(),
            nn.Linear(WIDTH, N_SQUAD_CHOICES),
        )
        self.squad_embed = nn.Parameter(torch.randn(N_SQUADS, SQUAD_EMBED) * 0.1)
        self.query = nn.Sequential(
            nn.Linear(SQUAD_EMBED + SQUAD_GLOBAL_DIM + SUMMARY, WIDTH), nn.Tanh()
        )
        self.order = nn.Linear(WIDTH, N_ORDER_CHOICES)
        self.point = nn.Linear(WIDTH, N_POINTS)
        self.attack_q = nn.Linear(WIDTH, WIDTH, bias=False)
        self.attack_k = nn.Linear(WIDTH, WIDTH, bias=False)
        self.defend_q = nn.Linear(WIDTH, WIDTH, bias=False)
        self.defend_k = nn.Linear(WIDTH, WIDTH, bias=False)
        for head in (self.launch, self.waypoint, self.order, self.point):
            nn.init.orthogonal_(head.weight, gain=0.01)
            nn.init.zeros_(head.bias)
        nn.init.orthogonal_(self.squad[-1].weight, gain=0.01)
        nn.init.zeros_(self.squad[-1].bias)

    def forward(self, x: CommanderInputs) -> HeadLogits:
        h, s = self.trunk(x.globals_, x.entities, x.valid)
        b = s.shape[0]
        launch_allowed = torch.stack(
            [torch.ones_like(x.launch_mask), x.launch_mask], dim=-1
        )
        squad_in = torch.cat([h, s[:, None, :].expand(-1, MAX_ENTITIES, -1)], dim=-1)
        squad_globals = x.globals_[:, SQUAD_GLOBALS].view(b, N_SQUADS, SQUAD_GLOBAL_DIM)
        q = self.query(
            torch.cat(
                [
                    self.squad_embed[None].expand(b, -1, -1),
                    squad_globals,
                    s[:, None, :].expand(-1, N_SQUADS, -1),
                ],
                dim=-1,
            )
        )
        scale = 1.0 / math.sqrt(WIDTH)
        target = (self.attack_q(q) @ self.attack_k(h).transpose(-1, -2)) * scale
        ward = (self.defend_q(q) @ self.defend_k(h).transpose(-1, -2)) * scale
        expand = (-1, N_SQUADS, -1)
        return HeadLogits(
            launch=_masked(self.launch(s).view(b, N_LAUNCH_HULLS, 2), launch_allowed),
            waypoint=_masked(self.waypoint(s), x.waypoint_mask),
            squad=_masked(self.squad(squad_in), x.squad_mask),
            order=_masked(self.order(q), x.order_mask),
            target=_masked(target, x.target_mask[:, None, :].expand(*expand)),
            ward=_masked(ward, x.ward_mask[:, None, :].expand(*expand)),
            point=self.point(q),
        )


def _split(actions: torch.Tensor) -> dict[str, torch.Tensor]:
    return {
        "launch": actions[:, LAUNCH],
        "waypoint": actions[:, WAYPOINT],
        "squad": actions[:, SQUAD_OF_SLOT],
        "order": actions[:, ORDER],
        "target": actions[:, ATTACK_TARGET],
        "ward": actions[:, DEFEND_WARD],
        "point": actions[:, GOTO_POINT],
    }


def _dists(logits: HeadLogits, validate: bool = True) -> dict[str, Categorical]:
    """Each head's distribution; ``validate=False`` skips torch's argument checks
    (the same distributions, cheaper to build)."""
    return {
        name: Categorical(
            logits=getattr(logits, name), validate_args=None if validate else False
        )
        for name in ("launch", "waypoint", "squad", "order", "target", "ward", "point")
    }


def _gates(order: torch.Tensor) -> dict[str, torch.Tensor]:
    """Per squad, which pointer and point heads the chosen order uses."""
    return {
        "target": (order == ORDER_ATTACK).float(),
        "ward": (order == ORDER_DEFEND).float(),
        "point": (order == ORDER_GOTO).float(),
    }


def _log_prob_entropy(
    dists: dict[str, Categorical], acts: dict[str, torch.Tensor]
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
    gates = _gates(acts["order"])
    logp = torch.zeros(acts["order"].shape[0])
    entropy = torch.zeros_like(logp)
    per_head: dict[str, torch.Tensor] = {}
    for name, dist in dists.items():
        lp = dist.log_prob(acts[name])
        ent = dist.entropy()
        if name in gates:
            lp = lp * gates[name]
            ent = ent * gates[name]
        if lp.dim() > 1:
            lp, ent = lp.sum(dim=-1), ent.sum(dim=-1)
        logp = logp + lp
        entropy = entropy + ent
        per_head[name] = ent
    return logp, entropy, per_head


@torch.no_grad()
def act(
    actor: CommanderActor, x: CommanderInputs, deterministic: bool = False
) -> tuple[torch.Tensor, torch.Tensor]:
    """Choose decisions: ``(actions [B, ACTION_DIM] int64, log-prob [B])``.

    Pointer and point heads are filled for every squad; the decoder reads them only
    when the squad's order chose their kind, and only then do they count in the
    log-probability.
    """
    dists = _dists(actor(x))
    acts = _choose(dists, deterministic)
    actions = _assemble(acts, x.batch_size)
    logp, _, _ = _log_prob_entropy(dists, acts)
    return actions, logp


@torch.no_grad()
def sample_actions(actor: CommanderActor, x: CommanderInputs) -> torch.Tensor:
    """``act``'s sampled decisions without their log-probability, for frozen
    commanders that only play: ``[B, ACTION_DIM]`` int64. The heads are sampled in
    ``act``'s order from the same distributions, so under the same torch RNG state
    the decisions are ``act``'s exactly; skipping the log-probability, entropy and
    argument checks makes a small batch about twice as fast.
    """
    acts = _choose(_dists(actor(x), validate=False), deterministic=False)
    return _assemble(acts, x.batch_size)


def _choose(
    dists: dict[str, Categorical], deterministic: bool
) -> dict[str, torch.Tensor]:
    """Each head's choice: the most likely, or a sample (in ``dists`` order)."""
    if deterministic:
        return {n: d.probs.argmax(dim=-1) for n, d in dists.items()}
    return {n: d.sample() for n, d in dists.items()}


def _assemble(acts: dict[str, torch.Tensor], b: int) -> torch.Tensor:
    """The ``[b, ACTION_DIM]`` decision rows of the heads' choices.

    Raises:
        RuntimeError: The heads do not fill ``ACTION_DIM`` columns.
    """
    actions = torch.cat(
        [
            acts["launch"],
            acts["waypoint"].view(b, 1),
            acts["squad"],
            acts["order"],
            acts["target"],
            acts["ward"],
            acts["point"],
        ],
        dim=1,
    )
    if actions.shape != (b, ACTION_DIM):
        raise RuntimeError(f"built actions of shape {tuple(actions.shape)}")
    return actions


def evaluate(
    actor: CommanderActor, x: CommanderInputs, actions: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
    """``(log-prob [B], entropy [B], entropy per head)`` of ``actions`` under ``actor``."""
    return _log_prob_entropy(_dists(actor(x)), _split(actions))


class CommanderCritic(nn.Module):
    """Value of a decision state for the commander's team. Each entity row also carries
    a one-hot of the pilot flying it (``n_pilots`` nets, plus one for "a script")."""

    def __init__(self, n_pilots: int) -> None:
        super().__init__()
        self.n_pilots = n_pilots
        self.trunk = Trunk(ENTITY_DIM + n_pilots + 1)
        self.value = nn.Linear(SUMMARY, 1)
        nn.init.orthogonal_(self.value.weight, gain=1.0)
        nn.init.zeros_(self.value.bias)

    def forward(self, x: CommanderInputs, pilot: torch.Tensor) -> torch.Tensor:
        """Values [B]. ``pilot``: [B, 20] int64, the pilot index per slot, or
        ``n_pilots`` for a ship the scripts fly."""
        one_hot = nn.functional.one_hot(pilot, self.n_pilots + 1).to(x.entities.dtype)
        entities = torch.cat([x.entities, one_hot], dim=-1)
        _, s = self.trunk(x.globals_, entities, x.valid)
        return self.value(s).squeeze(-1)


def lean_to_keep(actor: CommanderActor, keep_prior: float) -> None:
    """Start a fresh actor's order and squad heads at ``keep_prior`` odds of "keep".

    Both heads start near even odds over their choices (keep is one in five, one in
    six), so an untrained commander re-orders whenever it is allowed to. This sets the
    bias of choice 0 so that, with every choice allowed, keep has probability
    ``keep_prior``. It mutates ``actor`` in place and is meant for a new network only.

    Raises:
        ValueError: ``keep_prior`` is not in (0, 1).
    """
    if not 0.0 < keep_prior < 1.0:
        raise ValueError(f"keep_prior must be in (0, 1), got {keep_prior}")
    with torch.no_grad():
        for head, choices in (
            (actor.order, N_ORDER_CHOICES),
            (actor.squad[-1], N_SQUAD_CHOICES),
        ):
            head.bias.zero_()
            head.bias[0] = math.log(keep_prior * (choices - 1) / (1.0 - keep_prior))


def n_params(module: nn.Module) -> int:
    return sum(p.numel() for p in module.parameters())


def save_commander(path: Path, actor: CommanderActor, meta: dict[str, Any]) -> None:
    """Write the actor and ``meta`` (plain types only) for eval, export and opponents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    torch.save(
        {
            "format": CHECKPOINT_FORMAT,
            "io_version": COMMANDER_IO_VERSION,
            "actor": actor.state_dict(),
            "meta": meta,
        },
        tmp,
    )
    tmp.replace(path)


def load_commander(path: Path) -> tuple[CommanderActor, dict[str, Any]]:
    """Load an actor written by ``save_commander``.

    Raises:
        ValueError: Not a commander file, or one for another io version.
    """
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or payload.get("format") != CHECKPOINT_FORMAT:
        raise ValueError(f"{path} is not a {CHECKPOINT_FORMAT} file")
    if payload.get("io_version") != COMMANDER_IO_VERSION:
        raise ValueError(
            f"{path} has commander io {payload.get('io_version')}, "
            f"expected {COMMANDER_IO_VERSION}"
        )
    actor = CommanderActor()
    actor.load_state_dict(payload["actor"])
    return actor.eval(), dict(payload["meta"])
