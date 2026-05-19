from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection


def get_connection() -> connection:
    load_dotenv()
    return psycopg2.connect(
        host=os.environ["CLOUD_SQL_HOST"],
        port=os.getenv("CLOUD_SQL_PORT", "5432"),
        database=os.environ["CLOUD_SQL_DATABASE"],
        user=os.environ["CLOUD_SQL_USER"],
        password=os.environ["CLOUD_SQL_PASSWORD"],
    )


def check_connection() -> None:
    try:
        conn = get_connection()
        conn.close()
    except Exception as exc:
        raise ConnectionError(
            "Could not connect to Cloud SQL. Start the Cloud SQL instance, "
            "run the Auth Proxy (CLOUD_SQL_HOST=localhost), then retry."
        ) from exc
