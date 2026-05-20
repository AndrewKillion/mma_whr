from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Outcome keys match method_to_outcome in mma_insights_loader:
# 0 KO/TKO, 1 Split/Majority, 2 Submission, 3 Unanimous decision
DEFAULT_OUTCOME_WEIGHTS: dict[int, float] = {
    0: 1.2,
    1: 0.5,
    2: 1.1,
    3: 1.0,
}


def load_outcome_weights_from_json(path: str | Path) -> dict[int, float]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("outcome weights JSON must be an object")
    return {int(k): float(v) for k, v in data.items()}
