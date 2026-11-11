"""The commander's input and output layout (docs/COMMANDER.md), on the Python side.

The sim builds the features and masks and decodes actions; this module holds the
layout constants the network is shaped by and the batch type that carries one or more
decisions' inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

import numpy as np
import torch
from numpy.typing import NDArray

COMMANDER_IO_VERSION: Final = 1
MAX_ENTITIES: Final = 20
ENTITY_DIM: Final = 40
GLOBAL_DIM: Final = 53
ACTION_DIM: Final = 40
N_POINTS: Final = 25
N_SQUADS: Final = 4
N_LAUNCH_HULLS: Final = 3
# A ship keeps a changed order this many decisions unless the order is spent first.
HOLD_DECISIONS: Final = 5

# Action columns (docs/COMMANDER.md "Outputs").
LAUNCH: Final = slice(0, 3)
WAYPOINT: Final = 3
SQUAD_OF_SLOT: Final = slice(4, 24)
ORDER: Final = slice(24, 28)
ATTACK_TARGET: Final = slice(28, 32)
DEFEND_WARD: Final = slice(32, 36)
GOTO_POINT: Final = slice(36, 40)

# Choices of the order head.
ORDER_KEEP, ORDER_NONE, ORDER_ATTACK, ORDER_DEFEND, ORDER_GOTO = range(5)
N_ORDER_CHOICES: Final = 5
N_SQUAD_CHOICES: Final = 2 + N_SQUADS  # keep, no squad, squad 1-4
N_WAYPOINT_CHOICES: Final = 1 + N_POINTS

# Per-squad block of the globals: size, kind one-hot (4), hold left, point x, y.
SQUAD_GLOBALS: Final = slice(18, 50)
SQUAD_GLOBAL_DIM: Final = 8

MASK_SHAPES: Final[dict[str, tuple[int, ...]]] = {
    "launch_mask": (N_LAUNCH_HULLS,),
    "waypoint_mask": (N_WAYPOINT_CHOICES,),
    "squad_mask": (MAX_ENTITIES, N_SQUAD_CHOICES),
    "order_mask": (N_SQUADS, N_ORDER_CHOICES),
    "target_mask": (MAX_ENTITIES,),
    "ward_mask": (MAX_ENTITIES,),
}


def check_sim_layout(io: Mapping[str, object]) -> None:
    """Check the sim's ``rlf_sim.commander_io()`` constants against this module's.

    Raises:
        ValueError: A constant differs (the sim and the network disagree on a layout).
    """
    expected = {
        "version": COMMANDER_IO_VERSION,
        "entity_dim": ENTITY_DIM,
        "global_dim": GLOBAL_DIM,
        "action_dim": ACTION_DIM,
        "n_points": N_POINTS,
        "hold_decisions": HOLD_DECISIONS,
    }
    for key, value in expected.items():
        if key not in io:
            raise ValueError(
                f"the sim's commander_io() has no {key!r}: rebuild rlf_sim"
            )
        if int(io[key]) != value:  # type: ignore[call-overload]
            raise ValueError(f"sim {key} = {io[key]}, the commander expects {value}")


@dataclass
class CommanderInputs:
    """A batch of decisions' inputs, as torch tensors.

    Attributes:
        globals_: [B, GLOBAL_DIM] float.
        entities: [B, MAX_ENTITIES, ENTITY_DIM] float.
        valid: [B, MAX_ENTITIES] bool.
        launch_mask: [B, 3] bool: launching that hull is allowed (holding always is).
        waypoint_mask: [B, 26] bool.
        squad_mask: [B, 20, 6] bool.
        order_mask: [B, 4, 5] bool.
        target_mask: [B, 20] bool.
        ward_mask: [B, 20] bool.
    """

    globals_: torch.Tensor
    entities: torch.Tensor
    valid: torch.Tensor
    launch_mask: torch.Tensor
    waypoint_mask: torch.Tensor
    squad_mask: torch.Tensor
    order_mask: torch.Tensor
    target_mask: torch.Tensor
    ward_mask: torch.Tensor

    @property
    def batch_size(self) -> int:
        return int(self.globals_.shape[0])

    @classmethod
    def from_numpy(cls, arrays: Mapping[str, NDArray]) -> CommanderInputs:
        """From the sim's ``commander_features`` dict (or rows of it).

        Raises:
            ValueError: A missing array or a wrong shape.
        """
        try:
            globals_ = np.asarray(arrays["globals"], dtype=np.float32)
            entities = np.asarray(arrays["entities"], dtype=np.float32)
            valid = np.asarray(arrays["valid"], dtype=np.bool_)
            masks = {k: np.asarray(arrays[k], dtype=np.bool_) for k in MASK_SHAPES}
        except KeyError as e:
            raise ValueError(f"commander features lack {e}") from e
        b = globals_.shape[0]
        shapes = {
            "globals": (globals_, (b, GLOBAL_DIM)),
            "entities": (entities, (b, MAX_ENTITIES, ENTITY_DIM)),
            "valid": (valid, (b, MAX_ENTITIES)),
        } | {k: (masks[k], (b, *s)) for k, s in MASK_SHAPES.items()}
        for name, (arr, shape) in shapes.items():
            if arr.shape != shape:
                raise ValueError(f"{name} has shape {arr.shape}, expected {shape}")
        return cls(
            globals_=torch.from_numpy(globals_),
            entities=torch.from_numpy(entities),
            valid=torch.from_numpy(valid),
            **{k: torch.from_numpy(v) for k, v in masks.items()},
        )

    def index(self, idx: torch.Tensor | slice) -> CommanderInputs:
        """Rows ``idx`` of every tensor."""
        return CommanderInputs(
            **{k: getattr(self, k)[idx] for k in self.__dataclass_fields__}
        )

    @classmethod
    def cat(cls, parts: list[CommanderInputs]) -> CommanderInputs:
        """Concatenate batches along the batch dimension.

        Raises:
            ValueError: ``parts`` is empty.
        """
        if not parts:
            raise ValueError("nothing to concatenate")
        return cls(
            **{
                k: torch.cat([getattr(p, k) for p in parts])
                for k in cls.__dataclass_fields__
            }
        )
