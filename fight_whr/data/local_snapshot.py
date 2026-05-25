from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_FIGHTS_PATH = REPO_ROOT / "data" / "local" / "ufc_fights.parquet"
SQL_PATH = Path(__file__).resolve().parent / "sql" / "stg_ufc_data__fight_data_dim.sql"


def resolve_local_fights_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    env = os.getenv("MMA_WHR_LOCAL_FIGHTS_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_LOCAL_FIGHTS_PATH


def save_local_snapshot(df: pd.DataFrame, path: Path | None = None) -> Path:
    out = resolve_local_fights_path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    meta = {
        "path": str(out),
        "rows": len(df),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "sql": str(SQL_PATH.relative_to(REPO_ROOT)),
    }
    meta_path = out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return out
