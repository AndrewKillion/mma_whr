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

FIGHT_TABLE_SCHEMA = "staging"
FIGHT_TABLE_NAME = "stg_ufc_data__fight_data_dim"
FIGHT_TABLE = (FIGHT_TABLE_SCHEMA, FIGHT_TABLE_NAME)
FIGHT_SQL_FILE = "stg_ufc_data__fight_data_dim.sql"

# Standard codes from staging.stg_ufc_data__fight_data_dim._method
STANDARD_METHOD_CODES: dict[str, str] = {
    "TKO": "KO",
    "KO": "KO",
    "SUB": "Submission",
    "U_D": "Unanimous",
    "D_U": "Unanimous",
    "S_D": "Split",
    "D_S": "Split",
}

METHOD_PATTERN = re.compile(
    r"KO|TKO|Submission|Unanimous|Majority|Split|Doctor|SUB|U_D|D_U|S_D|D_S",
    re.IGNORECASE,
)


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
    text = str(method).strip()
    if not text:
        return None
    code = text.upper().replace(" ", "_").replace("-", "_")
    if code == "OTH":
        return None
    mapped = STANDARD_METHOD_CODES.get(code)
    if mapped is not None:
        return mapped
    if not METHOD_PATTERN.search(text):
        return None
    upper = text.upper()
    if re.search(r"KO|TKO|DOCTOR", upper):
        return "KO"
    if "SUB" in upper or "SUBMISSION" in upper:
        return "Submission"
    if "SPLIT" in upper or "MAJORITY" in upper or code in ("S_D", "D_S"):
        return "Split"
    if "UNANIMOUS" in upper or code in ("U_D", "D_U"):
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
    for name in ("method", "mov", "_method"):
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
        raise ValueError("No method/_method/mov column in fight data")

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


def _assert_fight_table_exists(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            """,
            (FIGHT_TABLE_SCHEMA, FIGHT_TABLE_NAME),
        )
        if cur.fetchone() is None:
            raise LookupError(
                f"Fight view not found: {FIGHT_TABLE_SCHEMA}.{FIGHT_TABLE_NAME}. "
                "Check CLOUD_SQL_USER can read staging."
            )


def fetch_fight_dataframe_from_postgres(limit: int | None = None) -> pd.DataFrame:
    check_connection()
    conn = get_connection()
    try:
        _assert_fight_table_exists(conn)
        sql = _load_sql_file(FIGHT_SQL_FILE)
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
