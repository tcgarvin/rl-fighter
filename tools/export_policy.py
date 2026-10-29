"""Export a spike-policy checkpoint for in-browser inference (``web/duel/``).

Writes two files into ``--out``:

- ``weights.bin``: the actor's float32 little-endian parameters, concatenated in
  layer order ``l0.weight, l0.bias, l1.weight, l1.bias, l2.weight, l2.bias``
  (``SpikeActor.net`` linears 0, 2, 4). Each weight is row-major ``[out, in]``
  (PyTorch's ``nn.Linear`` layout), so ``y[o] = b[o] + sum_i W[o * in + i] * x[i]``.
  Hidden layers are followed by tanh; the last layer gives the 61 raw logits.
- ``manifest.json`` (``rlf.web_policy/1``): sim_version, obs_dim, the action/logit
  layout of the 21 heads, layer shapes and float offsets into ``weights.bin``, the
  weights' sha256, the source checkpoint's path, sha256 and meta (update index,
  kind), the match config the policy was trained on, and an eval summary when
  ``--eval-json`` is given.

The export refuses a checkpoint whose obs_dim or sim_version does not match the
WASM build it will run against (``--wasm-sim-version`` / ``--wasm-obs-dim``, which
``scripts/build_site.sh`` reads from the freshly built bundle).

    python -m tools.export_policy --checkpoint X.pt --out dist/duel/policy \\
        --wasm-sim-version 2 --wasm-obs-dim 385 [--eval-json eval/x_vs_script.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch.nn as nn

from spacefight.rl.spike_policy import (
    ACTION_WIDTH,
    HEAD_CHOICES,
    HEAD_GROUPS,
    N_LOGITS,
    OBS_DIM,
    SLEW_HOLD,
    THROTTLE_HOLD,
    FIRE_NONE,
    SpikeActor,
    load_policy,
)

MANIFEST_FORMAT = "rlf.web_policy/1"
WEIGHTS_FILE = "weights.bin"
MANIFEST_FILE = "manifest.json"
# Value a masked head takes (SpikeActor.sample); power is never masked.
_HEAD_HOLD: dict[str, int | None] = {
    "throttle": THROTTLE_HOLD,
    "slew": SLEW_HOLD,
    "fire": FIRE_NONE,
    "power": None,
}
# Defaults of rlf_sim.VecEnv / RustVecEnv, used when a checkpoint has no config.
_DEFAULT_MATCH = {
    "fleets": [["fighter"], ["fighter"]],
    "arena_radius": 450.0,
    "time_limit_s": 90.0,
    "reaction_ticks": 2,
}


class ExportError(ValueError):
    """The checkpoint cannot be exported for this WASM build."""


@dataclass(frozen=True)
class SimVersion:
    """A checkpoint's sim version and where it was read from."""

    version: int
    source: str


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def actor_linears(actor: SpikeActor) -> list[nn.Linear]:
    """The actor's linear layers in forward order."""
    linears = [m for m in actor.net if isinstance(m, nn.Linear)]
    if len(linears) != 3:
        raise ExportError(f"expected 3 linear layers, found {len(linears)}")
    return linears


def checkpoint_sim_version(
    meta: dict[str, object], eval_summary: dict[str, Any] | None
) -> SimVersion:
    """The sim version a checkpoint was trained on.

    Spike checkpoints do not stamp it, so this falls back to the eval JSON's config
    and then to the ``rlf_sim`` extension the lab trains with.

    Raises:
        ExportError: No source gives a version.
    """
    stamped = meta.get("sim_version")
    if isinstance(stamped, int):
        return SimVersion(stamped, "checkpoint meta")
    if eval_summary is not None and isinstance(eval_summary.get("sim_version"), int):
        return SimVersion(int(eval_summary["sim_version"]), "eval json config")
    try:
        import rlf_sim  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ExportError(
            "checkpoint has no sim_version and rlf_sim is not importable; "
            "pass --eval-json from an eval of this checkpoint"
        ) from exc
    return SimVersion(int(rlf_sim.SIM_VERSION), "rlf_sim (training extension)")


def summarize_eval(path: Path) -> dict[str, Any]:
    """Pick the headline numbers out of a ``rlf.eval.duel/1`` or ``/2`` JSON."""
    raw = json.loads(path.read_text())
    try:
        side_a = raw["side_a"]
        config = raw["config"]
        return {
            "file": str(path),
            "a": raw["a"],
            "b": raw["b"],
            "n": config["n"],
            "sim_version": config.get("sim_version"),
            "wins": side_a["wins"],
            "draws": side_a["draws"],
            "losses": side_a["losses"],
            "win_rate": side_a["win_rate"],
            "hit_rate": side_a.get("hit_rate"),
            "length_median_ticks": raw.get("match", {}).get("length_median"),
        }
    except KeyError as exc:
        raise ExportError(f"{path} is not a duel eval JSON: missing {exc}") from exc


def match_config(meta: dict[str, object]) -> dict[str, Any]:
    """The MatchConfig the policy trained on (checkpoint config, else defaults)."""
    config = meta.get("config")
    source = config if isinstance(config, dict) else {}
    out = {key: source.get(key, default) for key, default in _DEFAULT_MATCH.items()}
    out["time_limit_ticks"] = int(round(float(out.pop("time_limit_s")) * 30))
    out["source"] = "checkpoint config" if source else "defaults"
    return out


def head_layout() -> list[dict[str, Any]]:
    """Action columns, logit offsets, choices and masked value of each head group."""
    heads = []
    logit = 0
    for name, cols in HEAD_GROUPS.items():
        choices = HEAD_CHOICES[name]
        n_heads = cols.stop - cols.start
        heads.append(
            {
                "name": name,
                "action_start": cols.start,
                "count": n_heads,
                "choices": choices,
                "logit_start": logit,
                "masked_value": _HEAD_HOLD[name],
            }
        )
        logit += n_heads * choices
    if logit != N_LOGITS:
        raise ExportError(f"head layout covers {logit} logits, expected {N_LOGITS}")
    return heads


def export(
    checkpoint: Path,
    out_dir: Path,
    wasm_sim_version: int,
    wasm_obs_dim: int,
    eval_json: Path | None = None,
) -> dict[str, Any]:
    """Write ``weights.bin`` and ``manifest.json``; return the manifest.

    Raises:
        ExportError: obs_dim or sim_version mismatch, or a malformed checkpoint.
    """
    actor, _critic, meta = load_policy(checkpoint)
    linears = actor_linears(actor)
    obs_dim = int(linears[0].in_features)
    if obs_dim != wasm_obs_dim or obs_dim != OBS_DIM:
        raise ExportError(
            f"checkpoint obs_dim {obs_dim} != wasm OBS_DIM {wasm_obs_dim} "
            f"(spike_policy OBS_DIM {OBS_DIM})"
        )
    if int(linears[-1].out_features) != N_LOGITS:
        raise ExportError(f"checkpoint has {linears[-1].out_features} logits")
    eval_summary = summarize_eval(eval_json) if eval_json is not None else None
    sim_version = checkpoint_sim_version(meta, eval_summary)
    if sim_version.version != wasm_sim_version:
        raise ExportError(
            f"checkpoint sim_version {sim_version.version} ({sim_version.source}) "
            f"!= wasm sim_version {wasm_sim_version}"
        )

    layers = []
    chunks: list[np.ndarray] = []
    offset = 0
    for i, layer in enumerate(linears):
        weight = layer.weight.detach().cpu().numpy().astype("<f4", copy=True)
        bias = layer.bias.detach().cpu().numpy().astype("<f4", copy=True)
        layers.append(
            {
                "name": f"l{i}",
                "in": int(layer.in_features),
                "out": int(layer.out_features),
                "weight_offset": offset,
                "bias_offset": offset + weight.size,
                "activation": "tanh" if i < len(linears) - 1 else "none",
            }
        )
        offset += weight.size + bias.size
        chunks.extend([weight.ravel(), bias.ravel()])
    blob = np.concatenate(chunks).astype("<f4").tobytes()

    out_dir.mkdir(parents=True, exist_ok=True)
    weights_path = out_dir / WEIGHTS_FILE
    weights_path.write_bytes(blob)
    plain_meta = {k: v for k, v in meta.items() if k != "config"}
    manifest: dict[str, Any] = {
        "format": MANIFEST_FORMAT,
        "sim_version": sim_version.version,
        "sim_version_source": sim_version.source,
        "obs_dim": obs_dim,
        "action_width": ACTION_WIDTH,
        "n_logits": N_LOGITS,
        "hidden": [int(layer.out_features) for layer in linears[:-1]],
        "dtype": "float32-le",
        "weights_file": WEIGHTS_FILE,
        "weights_floats": offset,
        "weights_sha256": hashlib.sha256(blob).hexdigest(),
        "layers": layers,
        "heads": head_layout(),
        "sampling": "stochastic: each unmasked head samples its softmax independently",
        "match_config": match_config(meta),
        "source": {
            "checkpoint": str(checkpoint.resolve()),
            "sha256": sha256_file(checkpoint),
            "kind": meta.get("kind", meta.get("source")),
            "update": meta.get("update"),
            "meta": plain_meta,
        },
        "eval": eval_summary,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wasm-sim-version", type=int, required=True)
    parser.add_argument("--wasm-obs-dim", type=int, required=True)
    parser.add_argument("--eval-json", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        manifest = export(
            args.checkpoint,
            args.out,
            args.wasm_sim_version,
            args.wasm_obs_dim,
            args.eval_json,
        )
    except (ExportError, FileNotFoundError) as exc:
        print(f"export_policy: {exc}", file=sys.stderr)
        return 1
    size = (args.out / WEIGHTS_FILE).stat().st_size
    print(
        f"export_policy: {args.checkpoint} -> {args.out} "
        f"({size} bytes, sim_version {manifest['sim_version']}, "
        f"update {manifest['source']['update']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
