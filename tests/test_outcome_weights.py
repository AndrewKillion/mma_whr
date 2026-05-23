from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fight_whr import Base
from fight_whr.outcome_weights import (
    ANCHOR_OUTCOME,
    DEFAULT_OUTCOME_WEIGHTS,
    NEUTRAL_OUTCOME_WEIGHTS,
    PRIOR_GUESS_OUTCOME_WEIGHTS,
    anchor_outcome_weights,
    build_outcome_weights,
    load_outcome_weights_from_json,
)


def test_neutral_defaults_all_one() -> None:
    assert DEFAULT_OUTCOME_WEIGHTS == NEUTRAL_OUTCOME_WEIGHTS
    assert all(v == 1.0 for v in DEFAULT_OUTCOME_WEIGHTS.values())


def test_anchor_outcome_weights() -> None:
    anchored = anchor_outcome_weights({0: 1.2, 1: 0.5, 2: 1.1, 3: 1.0})
    assert anchored[ANCHOR_OUTCOME] == 1.0
    assert anchored == PRIOR_GUESS_OUTCOME_WEIGHTS


def test_build_outcome_weights_anchors_ud() -> None:
    weights = build_outcome_weights(ko=1.4, split=0.6, submission=1.1)
    assert weights[3] == 1.0
    assert weights[0] == 1.4
    assert weights[1] == 0.6
    assert weights[2] == 1.1


def test_base_uses_default_outcome_weights() -> None:
    whr = Base()
    assert whr.config["outcome_weights"] == DEFAULT_OUTCOME_WEIGHTS


def test_load_outcome_weights_from_json_anchors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "weights.json"
        path.write_text(json.dumps({"0": 1.3, "1": 0.4, "2": 1.0, "3": 0.9}))
        loaded = load_outcome_weights_from_json(path)
    assert loaded[3] == 1.0
    assert abs(loaded[0] - 1.3 / 0.9) < 1e-9
