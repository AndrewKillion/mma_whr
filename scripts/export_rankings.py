#!/usr/bin/env python3
import argparse
from pathlib import Path

from _repo_path import ensure_repo_on_path

ensure_repo_on_path()

from fight_whr.outcome_weights import load_outcome_weights_from_json
from fight_whr.rankings import load_and_fit_whr, rankings_dataframe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run WHR on fight data and export rankings as a DataFrame (CSV/parquet).",
    )
    parser.add_argument(
        "--source",
        default="local",
        choices=["auto", "postgres", "gcs", "local"],
    )
    parser.add_argument("--local-fights", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument(
        "--outcome-weights",
        metavar="PATH",
        help="JSON file with outcome keys 0-3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/whr_rankings.parquet"),
        help="Output path (.parquet or .csv)",
    )
    args = parser.parse_args()

    config: dict = {}
    if args.outcome_weights:
        config["outcome_weights"] = load_outcome_weights_from_json(args.outcome_weights)

    print("Loading fights and running WHR...")
    whr, fight_rows = load_and_fit_whr(
        source=args.source,
        limit=args.limit,
        local_path=args.local_fights,
        config=config if config else None,
        iterations=args.iterations,
    )
    df = rankings_dataframe(whr=whr, fight_rows=fight_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.output.suffix.lower()
    if suffix == ".csv":
        df.to_csv(args.output, index=False)
    elif suffix in (".parquet", ".pq"):
        df.to_parquet(args.output, index=False)
    else:
        raise ValueError("Output must end with .csv or .parquet")

    print(f"Saved {len(df)} fighters to {args.output}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
