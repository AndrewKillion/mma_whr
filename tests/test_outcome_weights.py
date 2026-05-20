from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fight_whr import Base
from fight_whr.outcome_weights import (
    DEFAULT_OUTCOME_WEIGHTS,
    load_outcome_weights_from_json,
)


def test_default_outcome_weights_ordering() -> None:
    assert DEFAULT_OUTCOME_WEIGHTS[0] > DEFAULT_OUTCOME_WEIGHTS[2]
    assert DEFAULT_OUTCOME_WEIGHTS[2] > DEFAULT_OUTCOME_WEIGHTS[3]
    assert DEFAULT_OUTCOME_WEIGHTS[3] > DEFAULT_OUTCOME_WEIGHTS[1]
    assert DEFAULT_OUTCOME_WEIGHTS[1] == 0.5


def test_base_uses_default_outcome_weights() -> None:
    whr = Base()
    assert whr.config["outcome_weights"] == DEFAULT_OUTCOME_WEIGHTS


def test_load_outcome_weights_from_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "weights.json"
        path.write_text(json.dumps({"0": 1.3, "1": 0.4, "2": 1.0, "3": 0.9}))
        loaded = load_outcome_weights_from_json(path)
    assert loaded[0] == 1.3
    assert loaded[1] == 0.4
