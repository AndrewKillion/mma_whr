from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel

from fight_whr.data.db import check_connection, get_connection
from fight_whr.data.gcs_fights import fetch_raw_fight_rows
from fight_whr.data.local_snapshot import (
    SQL_PATH,
    resolve_local_fights_path,
    save_local_snapshot,
)

Source = Literal["auto", "postgres", "gcs", "local"]

METHOD_PATTERN = re.compile(
    r"KO|TKO|Submission|Unanimous|Majority|Split|Doctor",
    re.IGNORECASE,
)

CANDIDATE_TABLES = [
    ("raw", "ufc_fight_data"),
    ("raw", "fight_data_total_ufcstats"),
    ("public", "fight_data_total_ufcstats"),
]


class FightRow(BaseModel):
    fighter_a: str
    fighter_b: str
    date: date
    winner: str
    outcome: int
    time_step: int
    weightclass: str | None = None


def normalize_method(method: str | None) -> str | None:
    if method is None or (isinstance(method, float) and pd.isna(method)):
        return None
    m = str(method).strip()
    if not m or not METHOD_PATTERN.search(m):
        return None
    upper = m.upper()
    if re.search(r"KO|TKO|DOCTOR", upper):
        return "KO"
    if "SUBMISSION" in upper:
        return "Submission"
    if "SPLIT" in upper or "MAJORITY" in upper:
        return "Split"
    if "UNANIMOUS" in upper:
        return "Unanimous"
    return None


def method_to_outcome(method: str) -> int:
    if method == "KO":
        return 0
    if method == "Split":
        return 1
    if method == "Submission":
        return 2
    return 3


def _method_column(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for name in ("method", "mov"):
        if name in lower:
            return lower[name]
    return None


def _weightclass_column(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for name in ("weightclass", "weight_class"):
        if name in lower:
            return lower[name]
    return None


def _normalize_weightclass(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def _rows_from_dataframe(df: pd.DataFrame) -> list[FightRow]:
    method_col = _method_column(list(df.columns))
    if method_col is None:
        raise ValueError("No method/mov column in fight data")

    df = df.copy()
    df["fighter_a"] = df["fighter_a"].astype(str).str.strip()
    df["fighter_b"] = df["fighter_b"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["winner"] = df["winner"].astype(str).str.strip().str.upper()
    df["method_norm"] = df[method_col].map(normalize_method)
    df = df.dropna(subset=["date", "fighter_a", "fighter_b", "method_norm"])
    df = df[df["winner"].isin(["A", "B"])]

    if df.empty:
        return []

    min_date = df["date"].min()
    df["time_step"] = (df["date"] - min_date).dt.days.astype(int)
    df["outcome"] = df["method_norm"].map(method_to_outcome)

    wc_col = _weightclass_column(list(df.columns))
    rows: list[FightRow] = []
    for rec in df.sort_values("time_step").to_dict(orient="records"):
        wc = _normalize_weightclass(rec[wc_col]) if wc_col else None
        rows.append(
            FightRow(
                fighter_a=rec["fighter_a"],
                fighter_b=rec["fighter_b"],
                date=rec["date"].date(),
                winner=rec["winner"],
                outcome=int(rec["outcome"]),
                time_step=int(rec["time_step"]),
                weightclass=wc,
            )
        )
    return rows


def _load_sql_file(name: str) -> str:
    path = Path(__file__).resolve().parent / "sql" / name
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text()


def _find_fight_table(conn) -> tuple[str, str] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND (
                table_name = 'ufc_fight_data'
                OR table_name ILIKE '%fight%total%'
                OR table_name = 'fight_data_total_ufcstats'
              )
            ORDER BY table_schema, table_name
            """
        )
        found = {(s, t) for s, t in cur.fetchall()}

    for candidate in CANDIDATE_TABLES:
        if candidate in found:
            return candidate
    return next(iter(found), None) if found else None


def fetch_fight_dataframe_from_postgres(limit: int | None = None) -> pd.DataFrame:
    check_connection()
    conn = get_connection()
    try:
        table = _find_fight_table(conn)
        if table is None:
            raise LookupError("No fight table found in Cloud SQL")
        schema, name = table

        if table == ("raw", "ufc_fight_data"):
            sql = _load_sql_file("ufc_fight_data.sql")
        else:
            method_col = "method"
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (schema, name),
                )
                col_names = [r[0] for r in cur.fetchall()]
                cols = {c.lower() for c in col_names}
                if "mov" in cols and "method" not in cols:
                    method_col = "mov"
            date_col = "fight_date" if "fight_date" in cols else "date"
            wc_col = _weightclass_column(col_names)
            wc_select = f", {wc_col} AS weightclass" if wc_col else ""
            sql = f"""
                SELECT fighter_a, fighter_b, {date_col} AS date, winner, {method_col} AS method{wc_select}
                FROM {schema}.{name}
                WHERE {date_col} IS NOT NULL
                ORDER BY {date_col}
            """

        if limit is not None:
            sql = sql.rstrip().rstrip(";") + f" LIMIT {int(limit)}"
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def fetch_fights_from_postgres(limit: int | None = None) -> list[FightRow]:
    return _rows_from_dataframe(fetch_fight_dataframe_from_postgres(limit=limit))


def export_local_fight_snapshot(
    path: str | Path | None = None, limit: int | None = None
) -> Path:
    df = fetch_fight_dataframe_from_postgres(limit=limit)
    return save_local_snapshot(df=df, path=resolve_local_fights_path(path))


def fetch_fights_from_local(
    limit: int | None = None, path: str | Path | None = None
) -> list[FightRow]:
    snapshot = resolve_local_fights_path(path)
    if not snapshot.is_file():
        raise FileNotFoundError(
            f"Local fight snapshot not found: {snapshot}\n"
            "Run: python scripts/export_fights_snapshot.py\n"
            f"SQL query is stored at: {SQL_PATH}"
        )
    df = pd.read_parquet(snapshot)
    if limit is not None:
        df = df.head(int(limit))
    return _rows_from_dataframe(df)


def fetch_fights_from_gcs(limit: int | None = None) -> list[FightRow]:
    raw = fetch_raw_fight_rows()
    df = pd.DataFrame(raw)
    if limit is not None:
        df = df.head(limit)
    return _rows_from_dataframe(df)


def fetch_fights(
    source: Source = "auto",
    limit: int | None = None,
    local_path: str | Path | None = None,
) -> list[FightRow]:
    if source == "local":
        return fetch_fights_from_local(limit=limit, path=local_path)
    if source == "gcs":
        return fetch_fights_from_gcs(limit=limit)
    if source == "postgres":
        return fetch_fights_from_postgres(limit=limit)

    try:
        return fetch_fights_from_postgres(limit=limit)
    except Exception:
        return fetch_fights_from_gcs(limit=limit)
