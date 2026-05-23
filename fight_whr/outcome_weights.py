from __future__ import annotations

import json
from pathlib import Path

# Method-of-victory types stored on each fight (see mma_insights_loader.method_to_outcome).
# Grid search for tunable multipliers lives in fight_whr.fit_outcome_weights.
ANCHOR_OUTCOME = 3

OUTCOME_TYPES: dict[int, str] = {
    0: "KO/TKO",
    1: "Split/Majority decision",
    2: "Submission",
    3: "Unanimous decision",
}

NEUTRAL_OUTCOME_WEIGHTS: dict[int, float] = {
    0: 1.4,
    1: 1.0,
    2: 1.2,
    3: 1.0,
}

PRIOR_GUESS_OUTCOME_WEIGHTS: dict[int, float] = {
    0: 1.2,
    1: 0.5,
    2: 1.1,
    3: 1.0,
}

DEFAULT_OUTCOME_WEIGHTS: dict[int, float] = dict(PRIOR_GUESS_OUTCOME_WEIGHTS)


def anchor_outcome_weights(
    weights: dict[int, float], 
    anchor: int = ANCHOR_OUTCOME
) -> dict[int, float]:
    """Rescale weights so the anchor outcome (unanimous decision) is exactly 1.0."""
    if anchor not in weights:
        raise KeyError(f"anchor outcome {anchor} missing from weights")
    anchor_value = float(weights[anchor])
    if anchor_value <= 0:
        raise ValueError(f"anchor outcome weight must be positive, got {anchor_value}")
    scale = 1.0 / anchor_value
    return {int(k): float(v) * scale for k, v in weights.items()}


def build_outcome_weights(
    ko: float,
    split: float,
    submission: float,
    unanimous: float = 1.0,
) -> dict[int, float]:
    """Build weights for outcomes 0–3 and rescale to unanimous = 1.0."""
    return anchor_outcome_weights(
        {
            0: ko,
            1: split,
            2: submission,
            3: unanimous,
        }
    )


def load_outcome_weights_from_json(path: str | Path) -> dict[int, float]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("outcome weights JSON must be an object")
    loaded = {int(k): float(v) for k, v in data.items()}
    if ANCHOR_OUTCOME in loaded:
        return anchor_outcome_weights(loaded)
    return loaded


if __name__ == "__main__":
    print("Outcome types (OUTCOME_TYPES):")
    for key, label in sorted(OUTCOME_TYPES.items()):
        anchor = " [anchor]" if key == ANCHOR_OUTCOME else ""
        print(f"  {key}: {label}{anchor}")
    print(
        "\nFit-script search grid (candidate multipliers, not outcome names): "
        "fight_whr/fit_outcome_weights.py → DEFAULT_WEIGHT_GRID_VALUES"
    )
