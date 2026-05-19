from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account


def _storage_client() -> storage.Client:
    load_dotenv()
    key_json = os.getenv("GCS_SERVICE_ACCOUNT_KEY")
    if key_json:
        info = json.loads(key_json)
        creds = service_account.Credentials.from_service_account_info(info)
        return storage.Client(credentials=creds, project=info.get("project_id"))
    return storage.Client()


def fetch_raw_fight_rows() -> list[dict[str, Any]]:
    load_dotenv()
    bucket_name = os.environ["GCS_BUCKET_NAME"]
    folder = os.getenv("GCS_FOLDER", "bronze/ufc-stats").strip("/")
    blob_name = f"{folder}/ufc_fight_data_totals.json"
    client = _storage_client()
    blob = client.bucket(bucket_name).blob(blob_name)
    data = json.loads(blob.download_as_text())
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in {blob_name}")
    return data
