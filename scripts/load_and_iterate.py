#!/usr/bin/env python3
import argparse

from fight_whr import Base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="auto", choices=["auto", "postgres", "gcs"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=50)
    args = parser.parse_args()

    whr = Base()
    n = whr.load_fights_from_mma_insights(source=args.source, limit=args.limit)
    print(f"Loaded {n} fights")
    whr.iterate(args.iterations)
    for name, elo in whr.get_ordered_ratings(current=True)[:20]:
        print(f"{name}: {round(elo)}")


if __name__ == "__main__":
    main()
