from __future__ import annotations

from datetime import date

from fight_whr.data.mma_insights_loader import FightRow
from fight_whr.fit_outcome_weights import (
    DEFAULT_WEIGHT_GRID_COUNT,
    DEFAULT_WEIGHT_GRID_VALUES,
    describe_weight_search_grid,
    format_weight_grid_arg,
    grid_search_outcome_weights,
    linspace_weight_grid,
)


def test_linspace_weight_grid_endpoints_and_count() -> None:
    grid = linspace_weight_grid(low=0.7, high=2.7, count=DEFAULT_WEIGHT_GRID_COUNT)
    assert len(grid) == DEFAULT_WEIGHT_GRID_COUNT
    assert grid == DEFAULT_WEIGHT_GRID_VALUES
    assert grid[0] == 0.7
    assert abs(grid[-1] - 2.7) < 1e-12
    step = (grid[-1] - grid[0]) / (DEFAULT_WEIGHT_GRID_COUNT - 1)
    assert abs(grid[1] - grid[0] - step) < 1e-12


def test_format_weight_grid_arg_round_trip() -> None:
    grid = linspace_weight_grid()
    assert len(grid) == DEFAULT_WEIGHT_GRID_COUNT
    text = format_weight_grid_arg(grid)
    parsed = [float(x) for x in text.split(",")]
    assert len(parsed) == len(grid)
    for a, b in zip(parsed, grid, strict=True):
        assert abs(a - b) < 1e-5


def test_describe_weight_search_grid_lists_outcomes() -> None:
    text = describe_weight_search_grid(
        ko_values=[0.7, 1.0],
        split_values=[1.0],
        submission_values=[2.0, 2.7],
    )
    assert "KO/TKO" in text
    assert "Unanimous decision" in text
    assert "anchor" in text
    assert "2 × 1 × 2 = 4 combinations" in text


def _fight_row(
    *,
    fighter_a: str,
    fighter_b: str,
    day: int,
    winner: str,
    outcome: int,
) -> FightRow:
    return FightRow(
        fighter_a=fighter_a,
        fighter_b=fighter_b,
        date=date(2020, 1, 1),
        winner=winner,
        outcome=outcome,
        time_step=day,
    )


def test_grid_search_outcome_weights_runs_on_small_slice() -> None:
    rows = [
        _fight_row(fighter_a="A", fighter_b="B", day=0, winner="A", outcome=3),
        _fight_row(fighter_a="C", fighter_b="D", day=1, winner="B", outcome=0),
        _fight_row(fighter_a="A", fighter_b="C", day=2, winner="A", outcome=2),
        _fight_row(fighter_a="B", fighter_b="D", day=3, winner="B", outcome=1),
        _fight_row(fighter_a="A", fighter_b="D", day=4, winner="A", outcome=3),
        _fight_row(fighter_a="C", fighter_b="B", day=5, winner="B", outcome=0),
        _fight_row(fighter_a="D", fighter_b="C", day=6, winner="A", outcome=3),
        _fight_row(fighter_a="A", fighter_b="B", day=7, winner="B", outcome=1),
        _fight_row(fighter_a="C", fighter_b="D", day=8, winner="A", outcome=2),
        _fight_row(fighter_a="B", fighter_b="C", day=9, winner="A", outcome=0),
    ]
    results = grid_search_outcome_weights(
        rows=rows,
        ko_values=[0.8, 1.2],
        split_values=[0.5, 1.0],
        submission_values=[1.0],
        train_ratio=0.8,
        iterations=2,
    )
    assert len(results) == 4
    assert results[0].holdout_log_loss <= results[-1].holdout_log_loss
    assert results[0].weights[3] == 1.0
