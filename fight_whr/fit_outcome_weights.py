from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

from fight_whr import Base
from fight_whr.data.mma_insights_loader import FightRow, fetch_fights
from fight_whr.outcome_weights import (
    ANCHOR_OUTCOME,
    DEFAULT_OUTCOME_WEIGHTS,
    OUTCOME_TYPES,
    build_outcome_weights,
)

DEFAULT_WEIGHT_GRID_LOW = 0.7
DEFAULT_WEIGHT_GRID_HIGH = 2.7
DEFAULT_WEIGHT_GRID_COUNT = 10


def linspace_weight_grid(
    *,
    low: float = DEFAULT_WEIGHT_GRID_LOW,
    high: float = DEFAULT_WEIGHT_GRID_HIGH,
    count: int = DEFAULT_WEIGHT_GRID_COUNT,
) -> list[float]:
    if count < 2:
        raise ValueError(f"count must be at least 2, got {count}")
    if high <= low:
        raise ValueError(f"high must exceed low, got low={low}, high={high}")
    step = (high - low) / (count - 1)
    return [low + i * step for i in range(count)]


def format_weight_grid_arg(
    values: list[float] | None = None,
    *,
    low: float = DEFAULT_WEIGHT_GRID_LOW,
    high: float = DEFAULT_WEIGHT_GRID_HIGH,
    count: int = DEFAULT_WEIGHT_GRID_COUNT,
) -> str:
    grid = (
        values
        if values is not None
        else linspace_weight_grid(low=low, high=high, count=count)
    )
    return ",".join(f"{v:.6g}" for v in grid)


DEFAULT_WEIGHT_GRID_VALUES: list[float] = linspace_weight_grid()
DEFAULT_WEIGHT_GRID_ARG: str = format_weight_grid_arg(DEFAULT_WEIGHT_GRID_VALUES)


def describe_weight_search_grid(
    ko_values: list[float],
    split_values: list[float],
    submission_values: list[float],
) -> str:
    lines = [
        "Method-of-victory outcomes (fight_whr/outcome_weights.py OUTCOME_TYPES):",
    ]
    for key in sorted(OUTCOME_TYPES):
        anchor_note = " [anchor, fixed at 1.0 in search]" if key == ANCHOR_OUTCOME else " [tuned in grid]"
        lines.append(f"  {key} = {OUTCOME_TYPES[key]}{anchor_note}")
    lines.append("")
    lines.append(
        f"Weight candidates per tunable outcome "
        f"({DEFAULT_WEIGHT_GRID_LOW}–{DEFAULT_WEIGHT_GRID_HIGH}, "
        f"{DEFAULT_WEIGHT_GRID_COUNT} points by default):"
    )
    lines.append(f"  KO:         {_format_value_list(ko_values)}")
    lines.append(f"  Split:      {_format_value_list(split_values)}")
    lines.append(f"  Submission: {_format_value_list(submission_values)}")
    n = len(ko_values) * len(split_values) * len(submission_values)
    lines.append(f"  Grid size: {len(ko_values)} × {len(split_values)} × {len(submission_values)} = {n} combinations")
    return "\n".join(lines)


def _format_value_list(values: list[float]) -> str:
    return ", ".join(f"{v:.4g}" for v in values)


@dataclass(frozen=True)
class WeightSearchResult:
    weights: dict[int, float]
    train_log_likelihood: float
    holdout_log_loss: float
    holdout_brier: float
    holdout_fights: int


def _gamma_elo_at_time(whr: Base, name: str, time_step: int) -> tuple[float, float]:
    fighter = whr.fighter_by_name(name)
    prior_days = [d for d in fighter.days if d.day <= time_step]
    if not prior_days:
        return whr._gamma_elo_for_matchup(fighter=fighter)
    day = prior_days[-1]
    return day.gamma(), day.elo


def win_probability_at_time(
    whr: Base,
    fighter_a: str,
    fighter_b: str,
    time_step: int,
    handicap: float = 0.0,
) -> tuple[float, float]:
    """Win probability for A and B using ratings as of time_step (before that fight)."""
    a_gamma, a_elo = _gamma_elo_at_time(whr=whr, name=fighter_a, time_step=time_step)
    b_gamma, b_elo = _gamma_elo_at_time(whr=whr, name=fighter_b, time_step=time_step)
    prob_a = a_gamma / (a_gamma + 10 ** ((b_elo - handicap) / 400.0))
    prob_b = b_gamma / (b_gamma + 10 ** ((a_elo + handicap) / 400.0))
    return prob_a, prob_b


def load_rows_into_whr(
    whr: Base, rows: list[FightRow], up_to_time_step: int | None = None
) -> int:
    count = 0
    for row in rows:
        if up_to_time_step is not None and row.time_step > up_to_time_step:
            continue
        extras: dict[str, Any] = {}
        if row.weightclass is not None:
            extras["weightclass"] = row.weightclass
        whr.create_fight(
            row.fighter_a,
            row.fighter_b,
            row.winner,
            row.time_step,
            0,
            row.outcome,
            extras,
        )
        count += 1
    return count


def split_rows_by_time(
    rows: list[FightRow], train_ratio: float = 0.8
) -> tuple[list[FightRow], list[FightRow]]:
    if not 0.0 < train_ratio < 1.0:
        raise ValueError("train_ratio must be between 0 and 1")
    ordered = sorted(rows, key=lambda r: r.time_step)
    cut = int(len(ordered) * train_ratio)
    if cut <= 0 or cut >= len(ordered):
        raise ValueError(
            f"train_ratio {train_ratio} yields empty train or test split "
            f"(rows={len(ordered)}, cut={cut})"
        )
    return ordered[:cut], ordered[cut:]


def evaluate_outcome_weights(
    train_rows: list[FightRow],
    holdout_rows: list[FightRow],
    weights: dict[int, float],
    iterations: int = 30,
) -> WeightSearchResult:
    whr = Base(config={"outcome_weights": dict(weights)})
    load_rows_into_whr(whr=whr, rows=train_rows)
    for _ in range(iterations):
        whr.iterate(1)

    train_ll = whr.log_likelihood()
    log_loss = 0.0
    brier = 0.0
    n = 0
    for row in holdout_rows:
        prob_a, prob_b = win_probability_at_time(
            whr=whr,
            fighter_a=row.fighter_a,
            fighter_b=row.fighter_b,
            time_step=row.time_step,
        )
        p_win = prob_a if row.winner == "A" else prob_b
        p_win = min(max(p_win, 1e-15), 1.0 - 1e-15)
        log_loss -= math.log(p_win)
        brier += (1.0 - p_win) ** 2
        n += 1

    return WeightSearchResult(
        weights=dict(weights),
        train_log_likelihood=train_ll,
        holdout_log_loss=log_loss / n if n else float("inf"),
        holdout_brier=brier / n if n else float("inf"),
        holdout_fights=n,
    )


def grid_search_outcome_weights(
    rows: list[FightRow],
    ko_values: list[float],
    split_values: list[float],
    submission_values: list[float],
    train_ratio: float = 0.8,
    iterations: int = 30,
) -> list[WeightSearchResult]:
    train_rows, holdout_rows = split_rows_by_time(rows=rows, train_ratio=train_ratio)
    results: list[WeightSearchResult] = []
    for ko, split, sub in itertools.product(ko_values, split_values, submission_values):
        weights = build_outcome_weights(ko=ko, split=split, submission=sub)
        assert weights[ANCHOR_OUTCOME] == 1.0
        results.append(
            evaluate_outcome_weights(
                train_rows=train_rows,
                holdout_rows=holdout_rows,
                weights=weights,
                iterations=iterations,
            )
        )
    results.sort(key=lambda r: r.holdout_log_loss)
    return results


def format_weights(weights: dict[int, float]) -> str:
    short = {0: "KO", 1: "Split", 2: "Sub", 3: "UD"}
    parts = [f"{short[k]}={weights[k]:.3f}" for k in sorted(weights)]
    return ", ".join(parts)
