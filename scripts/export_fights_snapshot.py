#!/usr/bin/env python3
import argparse
from pathlib import Path

from _repo_path import ensure_repo_on_path

ensure_repo_on_path()

from fight_whr.data.local_snapshot import DEFAULT_LOCAL_FIGHTS_PATH
from fight_whr.data.mma_insights_loader import SQL_PATH, export_local_fight_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Cloud SQL fight rows to a local parquet snapshot for offline use",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output parquet path (default: {DEFAULT_LOCAL_FIGHTS_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max fights to export (oldest first by fight_date; default: all)",
    )
    args = parser.parse_args()

    out = export_local_fight_snapshot(path=args.output, limit=args.limit)
    print(f"SQL query: {SQL_PATH}")
    print(f"Saved {out}")
    print(f"Metadata: {out.with_suffix('.meta.json')}")
    print("Offline load: python scripts/load_and_iterate.py --source local")


if __name__ == "__main__":
    main()
