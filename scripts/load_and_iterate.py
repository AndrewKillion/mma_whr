#!/usr/bin/env python3
import argparse

from _repo_path import ensure_repo_on_path

ensure_repo_on_path()

from fight_whr import Base
from fight_whr.outcome_weights import load_outcome_weights_from_json


def _fighters_with_bouts(whr: Base) -> dict[str, object]:
    return {name: f for name, f in whr.fighters.items() if len(f.days) > 0}


def _resolve_fighter_name(fighters: dict[str, object], query: str) -> str | list[str] | None:
    if query in fighters:
        return query
    lower_map = {name.lower(): name for name in fighters}
    if query.lower() in lower_map:
        return lower_map[query.lower()]
    partial = sorted(name for name in fighters if query.lower() in name.lower())
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        return partial
    return None


def _require_fighter_name(fighters: dict[str, object], query: str) -> str | None:
    resolved = _resolve_fighter_name(fighters=fighters, query=query)
    if resolved is None:
        print(f"No fighter with fights matching '{query}'")
        return None
    if isinstance(resolved, list):
        print(f"Multiple matches for '{query}':")
        for name in resolved[:25]:
            print(f"  {name}")
        if len(resolved) > 25:
            print(f"  ... and {len(resolved) - 25} more")
        print("Use the exact name from the list.")
        return None
    return resolved


def _print_matchup(
    whr: Base, name1_query: str, name2_query: str, handicap: float
) -> None:
    fighters = _fighters_with_bouts(whr)
    name1 = _require_fighter_name(fighters=fighters, query=name1_query)
    name2 = _require_fighter_name(fighters=fighters, query=name2_query)
    if name1 is None or name2 is None:
        return
    elo1, _ = whr.ratings_for_fighter(name1, current=True)
    elo2, _ = whr.ratings_for_fighter(name2, current=True)
    print(f"\nHypothetical matchup: {name1} vs {name2}")
    print(f"  {name1} Elo: {elo1}")
    print(f"  {name2} Elo: {elo2}")
    if handicap != 0:
        print(f"  Handicap (Elo, favors {name1}): {handicap}")
    prob1, prob2 = whr.probability_future_match(name1, name2, handicap=handicap)
    print(f"  Model win probability: {name1} {prob1 * 100:.2f}% | {name2} {prob2 * 100:.2f}%")


def _print_fighter_lookup(whr: Base, query: str) -> None:
    name = _require_fighter_name(fighters=_fighters_with_bouts(whr), query=query)
    if name is None:
        return
    ratings = whr.get_ordered_ratings(current=True)
    rank = next((i for i, (n, _) in enumerate(ratings, 1) if n == name), None)
    elo, uncertainty = whr.ratings_for_fighter(name, current=True)
    print(f"\n{name}")
    print(f"  Elo: {elo}")
    print(f"  Uncertainty: {uncertainty}")
    if rank is not None:
        print(f"  Rank: {rank} / {len(ratings)}")
    history = whr.ratings_for_fighter(name, current=False)
    if isinstance(history, list) and len(history) > 0:
        print("  Recent fight days (time_step, elo, uncertainty):")
        for day, day_elo, day_unc in history[-5:]:
            print(f"    {day}: {day_elo}, {day_unc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load fights from mma-insights and run Newton WHR",
    )
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "postgres", "gcs", "local"],
        help="auto=postgres then gcs; local=parquet snapshot (no network)",
    )
    parser.add_argument(
        "--local-fights",
        type=str,
        default=None,
        help="Parquet path for --source local (default: data/local/ufc_fights.parquet)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max fights to load (default: all fights in the database)",
    )
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument(
        "--outcome-weights",
        metavar="PATH",
        help="JSON file with outcome keys 0-3 (overrides defaults)",
    )
    parser.add_argument(
        "--fighter",
        action="append",
        metavar="NAME",
        help="Look up a fighter after fitting (repeatable; partial name match)",
    )
    parser.add_argument(
        "--matchup",
        action="append",
        nargs=2,
        metavar=("FIGHTER_A", "FIGHTER_B"),
        help="Predict a hypothetical fight (repeatable; partial name match)",
    )
    parser.add_argument(
        "--handicap",
        type=float,
        default=0.0,
        help="Elo handicap for --matchup (positive favors first named fighter)",
    )
    args = parser.parse_args()

    config: dict = {}
    if args.outcome_weights:
        config["outcome_weights"] = load_outcome_weights_from_json(args.outcome_weights)
    whr = Base(config=config if config else None)
    print(f"Outcome weights: {whr.config['outcome_weights']}")
    if args.limit is None:
        print("Loading all fights (no limit)...")
    else:
        print(f"Loading up to {args.limit} fights (oldest first by fight_date)...")
    n = whr.load_fights_from_mma_insights(
        source=args.source,
        limit=args.limit,
        local_path=args.local_fights,
    )
    print(f"Loaded {n} fights")
    whr.iterate(args.iterations)
    print("\nTop 20:")
    for name, elo in whr.get_ordered_ratings(current=True)[:20]:
        print(f"  {name}: {round(elo)}")
    if args.fighter:
        for query in args.fighter:
            _print_fighter_lookup(whr=whr, query=query)
    if args.matchup:
        for name1, name2 in args.matchup:
            _print_matchup(
                whr=whr,
                name1_query=name1,
                name2_query=name2,
                handicap=args.handicap,
            )


if __name__ == "__main__":
    main()
