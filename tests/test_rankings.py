from __future__ import annotations

from datetime import date

from fight_whr import Base
from fight_whr.data.mma_insights_loader import FightRow
from fight_whr.rankings import rankings_dataframe


def _row(
    *,
    a: str,
    b: str,
    d: date,
    step: int,
    winner: str = "A",
    wc: str | None = None,
) -> FightRow:
    return FightRow(
        fighter_a=a,
        fighter_b=b,
        date=d,
        winner=winner,
        outcome=3,
        time_step=step,
        weightclass=wc,
    )


def test_rankings_dataframe_columns_and_last_bout_metadata() -> None:
    rows = [
        _row(a="alice", b="bob", d=date(2020, 1, 1), step=0, wc="Lightweight"),
        _row(a="alice", b="carl", d=date(2021, 6, 1), step=100, wc="Welterweight"),
    ]
    whr = Base()
    for row in rows:
        extras = {"weightclass": row.weightclass} if row.weightclass else {}
        whr.create_fight(
            row.fighter_a,
            row.fighter_b,
            row.winner,
            row.time_step,
            0,
            row.outcome,
            extras,
        )
    whr.iterate(2)

    df = rankings_dataframe(whr=whr, fight_rows=rows)
    assert list(df.columns) == [
        "fighter_name",
        "current_score",
        "current_weightclass",
        "last_fight_date",
    ]
    alice = df.loc[df["fighter_name"] == "alice"].iloc[0]
    assert alice["current_weightclass"] == "Welterweight"
    assert alice["last_fight_date"] == date(2021, 6, 1)
