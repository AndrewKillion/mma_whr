#!/usr/bin/env python3
import argparse
import json

from _repo_path import ensure_repo_on_path

ensure_repo_on_path()

from fight_whr.data.mma_insights_loader import fetch_fights
from fight_whr.fit_outcome_weights import (
    evaluate_outcome_weights,
    format_weights,
    grid_search_outcome_weights,
)
from fight_whr.outcome_weights import (
    DEFAULT_OUTCOME_WEIGHTS,
    NEUTRAL_OUTCOME_WEIGHTS,
    PRIOR_GUESS_OUTCOME_WEIGHTS,
    build_outcome_weights,
)


def _parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search outcome weights with unanimous decision (3) fixed at 1.0. "
            "Scores held-out fights by log loss using ratings before each fight."
        ),
    )
    parser.add_argument("--source", default="local", choices=["auto", "postgres", "gcs", "local"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument(
        "--ko",
        default="0.8,1.0,1.2,1.4",
        help="Comma-separated KO weights to try (rescaled vs UD=1)",
    )
    parser.add_argument(
        "--split",
        default="0.3,0.5,0.7,1.0",
        help="Comma-separated split-decision weights to try",
    )
    parser.add_argument(
        "--submission",
        default="0.9,1.0,1.1,1.2",
        help="Comma-separated submission weights to try",
    )
    parser.add_argument(
        "--baseline",
        choices=["neutral", "prior_guess", "none"],
        default="neutral",
        help="Also score this fixed weight set (default: all 1.0)",
    )
    parser.add_argument("--top", type=int, default=10, help="How many grid results to print")
    args = parser.parse_args()

    print("Loading fights...")
    rows = fetch_fights(source=args.source, limit=args.limit)
    print(f"Loaded {len(rows)} fights")

    ko_values = _parse_float_list(args.ko)
    split_values = _parse_float_list(args.split)
    sub_values = _parse_float_list(args.submission)
    n_grid = len(ko_values) * len(split_values) * len(sub_values)
    print(
        f"Grid: {n_grid} combos (UD anchor=1.0), "
        f"train_ratio={args.train_ratio}, iterations={args.iterations}"
    )

    baselines: dict[str, dict[int, float]] = {}
    if args.baseline == "neutral":
        baselines["neutral"] = dict(NEUTRAL_OUTCOME_WEIGHTS)
    elif args.baseline == "prior_guess":
        baselines["prior_guess"] = dict(PRIOR_GUESS_OUTCOME_WEIGHTS)

    from fight_whr.fit_outcome_weights import split_rows_by_time

    train_rows, holdout_rows = split_rows_by_time(rows=rows, train_ratio=args.train_ratio)
    print(f"Train fights: {len(train_rows)}, holdout: {len(holdout_rows)}")

    for name, weights in baselines.items():
        result = evaluate_outcome_weights(
            train_rows=train_rows,
            holdout_rows=holdout_rows,
            weights=weights,
            iterations=args.iterations,
        )
        print(
            f"\nBaseline [{name}]: {format_weights(result.weights)} "
            f"| holdout log_loss={result.holdout_log_loss:.5f} "
            f"brier={result.holdout_brier:.5f}"
        )

    results = grid_search_outcome_weights(
        rows=rows,
        ko_values=ko_values,
        split_values=split_values,
        submission_values=sub_values,
        train_ratio=args.train_ratio,
        iterations=args.iterations,
    )

    print(f"\nTop {args.top} by holdout log loss (lower is better):")
    for i, result in enumerate(results[: args.top], 1):
        print(
            f"  {i}. {format_weights(result.weights)} "
            f"| log_loss={result.holdout_log_loss:.5f} "
            f"brier={result.holdout_brier:.5f} "
            f"| train_ll={result.train_log_likelihood:.1f}"
        )

    best = results[0]
    print(f"\nBest: {format_weights(best.weights)}")
    print("JSON for --outcome-weights:")
    print(json.dumps({str(k): v for k, v in sorted(best.weights.items())}, indent=2))


if __name__ == "__main__":
    main()
