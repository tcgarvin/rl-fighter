"""The ``/pilot/`` page states only facts that ``tools/pilot_facts.py`` computes."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest

from spacefight.rl.spike_policy import load_policy, param_count
from tools.champion import DEFAULT_CACHE, find_champion
from tools.pilot_facts import (
    DEFAULT_PAGE,
    PilotFactsError,
    check_manifest,
    check_manifest_champion,
    check_page,
    compute_facts,
    page_facts,
)

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def facts() -> dict[str, str]:
    return compute_facts()


@pytest.fixture(scope="module")
def page() -> str:
    return DEFAULT_PAGE.read_text()


def _manifest(facts: dict[str, str]) -> dict[str, Any]:
    """A policy manifest as tools/export_policy.py writes it, for these facts."""
    return {
        "obs_dim": int(facts["actor.in"]),
        "n_logits": int(facts["actor.logits"]),
        "action_width": int(facts["actor.heads"]),
        "hidden": [int(facts["actor.hidden"])] * 2,
        "weights_floats": int(facts["actor.params"].replace(",", "")),
        "layers": [
            {"activation": "tanh"},
            {"activation": "tanh"},
            {"activation": "none"},
        ],
        "match_config": {"reaction_ticks": int(facts["reaction.ticks"])},
        "source": {"sha256": find_champion("current").weights.sha256},
    }


def test_every_number_on_the_page_matches_the_code(
    page: str, facts: dict[str, str]
) -> None:
    assert check_page(page, facts) == []
    keys = {key for key, _ in page_facts(page)}
    # The headline numbers are all checked, not just present somewhere.
    for key in (
        "obs.dim",
        "actor.params",
        "actor.heads",
        "critic.params",
        "champion.id",
    ):
        assert key in keys


def test_the_actor_is_the_mlp_the_page_describes(facts: dict[str, str]) -> None:
    assert facts["actor.activation"] == "tanh"
    assert (facts["actor.in"], facts["actor.hidden"], facts["actor.logits"]) == (
        "385",
        "256",
        "61",
    )
    assert (
        facts["actor.params"]
        == f"{385 * 256 + 256 + 256 * 256 + 256 + 256 * 61 + 61:,}"
    )


def test_a_stale_number_is_reported(page: str, facts: dict[str, str]) -> None:
    stale = page.replace(
        '<dd data-fact="actor.params">180,285</dd>',
        '<dd data-fact="actor.params">180,000</dd>',
    )
    assert stale != page
    [mismatch] = check_page(stale, facts)
    assert (mismatch.key, mismatch.page, mismatch.expected) == (
        "actor.params",
        "180,000",
        facts["actor.params"],
    )


def test_an_unknown_fact_key_is_an_error(facts: dict[str, str]) -> None:
    with pytest.raises(PilotFactsError, match="unknown fact keys"):
        check_page('<span data-fact="actor.depth">3</span>', facts)
    with pytest.raises(PilotFactsError, match="no data-fact"):
        check_page("<p>nothing to check</p>", facts)


def test_mask_diagram_cells_match_each_hulls_live_heads(
    page: str, facts: dict[str, str]
) -> None:
    for hull in ("fighter", "strafer", "gunship"):
        live = re.findall(
            rf'class="cell on" data-hull="{hull}" data-head="(\w+)"', page
        )
        cells = re.findall(rf'data-hull="{hull}" data-head="(\w+)"', page)
        assert len(cells) == int(facts["action.width"])
        assert len(live) == int(facts[f"hull.{hull}.heads"])
        assert live.count("throttle") == int(facts[f"hull.{hull}.thrusters"])
        assert live.count("slew") == int(facts[f"hull.{hull}.slewing"])
        assert live.count("fire") == int(facts[f"hull.{hull}.turrets"])
        assert live.count("power") == 1


def test_manifest_check_accepts_the_champion_export(facts: dict[str, str]) -> None:
    manifest = _manifest(facts)
    check_manifest(manifest, facts)
    check_manifest_champion(manifest, find_champion("current"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("hidden", [128, 128], "hidden"),
        ("weights_floats", 1, "weights_floats"),
        (
            "layers",
            [{"activation": "relu"}] * 2 + [{"activation": "none"}],
            "activations",
        ),
    ],
)
def test_manifest_check_rejects_a_different_network(
    facts: dict[str, str], field: str, value: object, message: str
) -> None:
    manifest = copy.deepcopy(_manifest(facts))
    manifest[field] = value
    with pytest.raises(PilotFactsError, match=message):
        check_manifest(manifest, facts)


def test_manifest_from_another_checkpoint_is_rejected(facts: dict[str, str]) -> None:
    manifest = _manifest(facts)
    manifest["source"]["sha256"] = "0" * 64
    with pytest.raises(PilotFactsError, match="not champion"):
        check_manifest_champion(manifest, find_champion("current"))


def _champion_checkpoint() -> Path | None:
    champion = find_champion("current")
    candidates = [
        REPO / champion.checkpoint,
        DEFAULT_CACHE / f"{champion.weights.sha256}.pt",
    ]
    return next((path for path in candidates if path.is_file()), None)


def test_champion_weights_have_the_stated_shapes(facts: dict[str, str]) -> None:
    checkpoint = _champion_checkpoint()
    if checkpoint is None:
        pytest.skip(
            "champion weights not on this machine (python -m tools.champion fetch)"
        )
    actor, critic, _ = load_policy(checkpoint)
    assert f"{param_count(actor):,}" == facts["actor.params"]
    assert f"{param_count(critic):,}" == facts["critic.params"]
    assert type(critic).__name__ == "FleetCritic"
