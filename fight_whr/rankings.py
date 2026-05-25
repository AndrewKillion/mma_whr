from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from fight_whr import Base
from fight_whr.data.mma_insights_loader import FightRow, fetch_fights


def _last_fight_metadata(
    fight_rows: list[FightRow],
) -> tuple[dict[str, date], dict[str, str | None]]:
    last_date: dict[str, date] = {}
    last_weightclass: dict[str, str | None] = {}
    for row in fight_rows:
        for name in (row.fighter_a, row.fighter_b):
            prev = last_date.get(name)
            if prev is None or row.date > prev:
                last_date[name] = row.date
                last_weightclass[name] = row.weightclass
            elif row.date == prev and row.weightclass is not None:
                last_weightclass[name] = row.weightclass
    return last_date, last_weightclass


def load_and_fit_whr(
    *,
    source: str = "auto",
    limit: int | None = None,
    local_path: str | None = None,
    config: dict[str, Any] | None = None,
    iterations: int = 50,
) -> tuple[Base, list[FightRow]]:
    whr = Base(config=config)
    rows = fetch_fights(source=source, limit=limit, local_path=local_path)
    for row in rows:
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
    whr.iterate(iterations)
    return whr, rows


def rankings_dataframe(
    whr: Base,
    fight_rows: list[FightRow],
) -> pd.DataFrame:
    """One row per rated fighter: name, Elo, latest bout weight class, last fight date."""
    last_date, last_weightclass = _last_fight_metadata(fight_rows=fight_rows)
    records: list[dict[str, Any]] = []
    for name, fighter in whr.fighters.items():
        if len(fighter.days) == 0:
            continue
        records.append(
            {
                "fighter_name": name,
                "current_score": float(fighter.days[-1].elo),
                "current_weightclass": last_weightclass.get(name),
                "last_fight_date": last_date.get(name),
            }
        )
    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("current_score", ascending=False, ignore_index=True)
