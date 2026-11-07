"""Export a learned commander for the browser (``web/src/live/commander.js``).

Reads a ``spacefight.commander.policy.save_commander`` checkpoint (``rlf.commander/1``)
and writes into ``<out>/``:

- ``weights.bin``: every actor tensor, float32 little-endian, in ``state_dict`` order
  (a Linear's weight is ``[out, in]`` row-major, as torch keeps it);
- ``manifest.json`` (``rlf.web_commander/1``): the commander io version, the network's
  dimensions, the flat feature layout the browser reads (``WasmMatch.
  commander_features``), each tensor's name, shape and offset, and the source
  checkpoint (path, sha256, training update).

The checks happen here, before anything reaches a page: the checkpoint must be a
commander file of this io version (``load_commander``), and, given the wasm build's
``commanderIoJson()`` (``--wasm-io-json``), the wasm must agree with the network on
the io version, every dimension and the flat layout. The browser checks the manifest
against its wasm once more when it loads the bundle.

    python -m tools.export_commander --checkpoint <commander.pt> --out <dir> \\
        [--wasm-io-json '<commanderIoJson() output>']
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

import numpy as np

from spacefight.commander.io import (
    ACTION_DIM,
    COMMANDER_IO_VERSION,
    ENTITY_DIM,
    GLOBAL_DIM,
    MASK_SHAPES,
    MAX_ENTITIES,
    N_LAUNCH_HULLS,
    N_ORDER_CHOICES,
    N_POINTS,
    N_SQUAD_CHOICES,
    N_SQUADS,
    N_WAYPOINT_CHOICES,
    SQUAD_GLOBAL_DIM,
    SQUAD_GLOBALS,
)
from spacefight.commander.policy import (
    HEADS,
    MASKED,
    SQUAD_EMBED,
    SUMMARY,
    WIDTH,
    load_commander,
)
from tools.champion import sha256_of

FORMAT: Final = "rlf.web_commander/1"
WEIGHTS_FILE: Final = "weights.bin"


class CommanderExportError(ValueError):
    """The checkpoint cannot run in the browser build it is exported for."""


def flat_layout() -> list[tuple[str, int, int]]:
    """``(name, offset, width)`` of the flat features, as the network reads them:
    globals, entities (slot-major), valid, then the masks (docs/COMMANDER.md
    "Bindings")."""
    widths = [
        ("globals", GLOBAL_DIM),
        ("entities", MAX_ENTITIES * ENTITY_DIM),
        ("valid", MAX_ENTITIES),
    ] + [(name, int(np.prod(shape))) for name, shape in MASK_SHAPES.items()]
    layout = []
    offset = 0
    for name, width in widths:
        layout.append((name, offset, width))
        offset += width
    return layout


def features_len() -> int:
    name, offset, width = flat_layout()[-1]
    return offset + width


def dims() -> dict[str, int]:
    """The network's shape constants the browser's forward pass is written for."""
    return {
        "entity_dim": ENTITY_DIM,
        "global_dim": GLOBAL_DIM,
        "action_dim": ACTION_DIM,
        "n_entities": MAX_ENTITIES,
        "n_points": N_POINTS,
        "n_squads": N_SQUADS,
        "n_launch_hulls": N_LAUNCH_HULLS,
        "n_waypoint_choices": N_WAYPOINT_CHOICES,
        "n_squad_choices": N_SQUAD_CHOICES,
        "n_order_choices": N_ORDER_CHOICES,
        "squad_globals_offset": int(SQUAD_GLOBALS.start),
        "squad_global_dim": SQUAD_GLOBAL_DIM,
        "width": WIDTH,
        "summary": SUMMARY,
        "attention_heads": HEADS,
        "squad_embed": SQUAD_EMBED,
    }


def check_wasm_io(io: Mapping[str, Any]) -> None:
    """Check the wasm's ``commanderIoJson()`` against the network's layout.

    Raises:
        CommanderExportError: The io version, a dimension or the flat layout differs.
    """
    expected = {
        "version": COMMANDER_IO_VERSION,
        "entity_dim": ENTITY_DIM,
        "global_dim": GLOBAL_DIM,
        "action_dim": ACTION_DIM,
        "n_entities": MAX_ENTITIES,
        "n_points": N_POINTS,
        "flat_dim": features_len(),
    }
    for key, want in expected.items():
        if key not in io:
            raise CommanderExportError(f"wasm commander io has no {key}")
        if int(io[key]) != want:
            raise CommanderExportError(
                f"wasm commander io {key} = {io[key]}, the commander expects {want}"
            )
    got = [(str(n), int(o), int(w)) for n, o, w in io.get("flat_layout", [])]
    if got != flat_layout():
        raise CommanderExportError(
            f"wasm flat layout {got} differs from the commander's {flat_layout()}"
        )


def export(
    checkpoint: Path, out: Path, wasm_io: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Write ``manifest.json`` and ``weights.bin`` for ``checkpoint`` into ``out``.

    Args:
        checkpoint: A ``save_commander`` file.
        out: The export directory (created).
        wasm_io: The wasm build's ``commanderIoJson()``, parsed; checked if given.

    Returns:
        The manifest written.

    Raises:
        CommanderExportError: Not a commander file of this io version, or a wasm that
            disagrees with the network.
    """
    if wasm_io is not None:
        check_wasm_io(wasm_io)
    try:
        actor, meta = load_commander(checkpoint)
    except ValueError as err:
        raise CommanderExportError(str(err)) from err
    tensors = []
    chunks = []
    offset = 0
    for name, tensor in actor.state_dict().items():
        data = tensor.detach().cpu().numpy().astype("<f4").ravel()
        if not np.isfinite(data).all():
            raise CommanderExportError(f"{checkpoint}: {name} has non-finite weights")
        tensors.append({"name": name, "shape": list(tensor.shape), "offset": offset})
        chunks.append(data)
        offset += data.size
    out.mkdir(parents=True, exist_ok=True)
    np.concatenate(chunks).tofile(out / WEIGHTS_FILE)
    update = meta.get("update")
    manifest: dict[str, Any] = {
        "format": FORMAT,
        "io_version": COMMANDER_IO_VERSION,
        "dims": dims(),
        "masked_logit": MASKED,
        "features_len": features_len(),
        "flat_layout": [list(entry) for entry in flat_layout()],
        "weights_file": WEIGHTS_FILE,
        "weights_floats": offset,
        "tensors": tensors,
        "source": {
            "checkpoint": checkpoint.as_posix(),
            "sha256": sha256_of(checkpoint),
            "update": int(update) if isinstance(update, int) else None,
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--wasm-io-json", default="", help="the wasm build's commanderIoJson()"
    )
    args = parser.parse_args(argv)
    try:
        wasm_io = json.loads(args.wasm_io_json) if args.wasm_io_json else None
        manifest = export(args.checkpoint, args.out, wasm_io)
    except (CommanderExportError, FileNotFoundError, json.JSONDecodeError) as err:
        print(f"export_commander: {err}", file=sys.stderr)
        return 1
    print(
        f"export_commander: {args.out} ({manifest['weights_floats']:,} weights, "
        f"io {manifest['io_version']}, update {manifest['source']['update']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
