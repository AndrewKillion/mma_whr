#!/usr/bin/env python3
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from _repo_path import ensure_repo_on_path

ensure_repo_on_path()

from fight_whr.data.db import check_connection

REPO_ROOT = Path(__file__).resolve().parents[1]
PID_FILE = REPO_ROOT / ".cloud-sql-proxy.pid"


def _gcloud(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gcloud", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _proxy_binary() -> str:
    configured = os.getenv("CLOUD_SQL_PROXY_PATH")
    if configured and os.path.isfile(configured):
        return configured
    for candidate in (
        "cloud-sql-proxy",
        os.path.expanduser("~/google-cloud-sdk/bin/cloud-sql-proxy"),
    ):
        found = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if found:
            return found
    raise RuntimeError(
        "cloud-sql-proxy not found. Install it or set CLOUD_SQL_PROXY_PATH in .env"
    )


def _connection_name(instance: str, project: str) -> str:
    explicit = os.getenv("CLOUD_SQL_CONNECTION_NAME")
    if explicit:
        return explicit
    result = _gcloud(
        "sql",
        "instances",
        "describe",
        instance,
        "--format=value(connectionName)",
        "--project",
        project,
    )
    name = (result.stdout or "").strip()
    if not name:
        raise RuntimeError(f"Could not resolve connection name for instance '{instance}'")
    return name


def _proxy_running() -> bool:
    if not PID_FILE.exists():
        return False
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return False


def wake_instance(instance: str, project: str) -> None:
    state = _gcloud(
        "sql",
        "instances",
        "describe",
        instance,
        "--format=value(state)",
        "--project",
        project,
    )
    current = (state.stdout or "").strip()
    if current == "RUNNABLE":
        print(f"Cloud SQL instance '{instance}' is already running")
        return

    print(f"Starting Cloud SQL instance '{instance}' (was {current or 'unknown'})...")
    _gcloud(
        "sql",
        "instances",
        "patch",
        instance,
        "--activation-policy=ALWAYS",
        "--project",
        project,
    )

    for _ in range(60):
        state = _gcloud(
            "sql",
            "instances",
            "describe",
            instance,
            "--format=value(state)",
            "--project",
            project,
        )
        current = (state.stdout or "").strip()
        if current == "RUNNABLE":
            print(f"Cloud SQL instance '{instance}' is RUNNABLE")
            return
        time.sleep(5)

    raise RuntimeError(
        f"Instance '{instance}' did not reach RUNNABLE within 5 minutes (state={current})"
    )


def start_proxy(connection_name: str, host: str, port: int) -> None:
    if _proxy_running() and _port_open(host, port):
        print(f"Cloud SQL Auth Proxy already running (pid {PID_FILE.read_text().strip()})")
        return

    binary = _proxy_binary()
    print(f"Starting Cloud SQL Auth Proxy on {host}:{port}...")
    proc = subprocess.Popen(
        [binary, connection_name, f"--port={port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))

    for _ in range(30):
        if proc.poll() is not None:
            err = (proc.stderr.read() if proc.stderr else b"").decode()
            PID_FILE.unlink(missing_ok=True)
            raise RuntimeError(f"cloud-sql-proxy exited immediately: {err}")
        if _port_open(host, port):
            print(f"Cloud SQL Auth Proxy running (pid {proc.pid})")
            return
        time.sleep(1)

    proc.terminate()
    PID_FILE.unlink(missing_ok=True)
    raise RuntimeError("cloud-sql-proxy did not open the port within 30 seconds")


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    host = os.getenv("CLOUD_SQL_HOST", "localhost")
    port = int(os.getenv("CLOUD_SQL_PORT", "5432"))
    instance = os.getenv("CLOUD_SQL_INSTANCE")
    project = os.getenv("CLOUD_SQL_PROJECT", "mma-insights")

    try:
        check_connection()
        print("Cloud SQL connection OK")
        return
    except ConnectionError:
        pass

    if instance:
        try:
            wake_instance(instance=instance, project=project)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
    else:
        print("CLOUD_SQL_INSTANCE not set; skipping instance wake-up", file=sys.stderr)

    if not _port_open(host, port):
        if not instance:
            print(
                "Cannot start proxy without CLOUD_SQL_INSTANCE or CLOUD_SQL_CONNECTION_NAME",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            connection_name = _connection_name(instance=instance, project=project)
            start_proxy(connection_name=connection_name, host=host, port=port)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)

    try:
        check_connection()
        print("Cloud SQL connection OK")
    except ConnectionError as exc:
        cause = exc.__cause__
        detail = f" ({cause})" if cause else ""
        print(f"Could not connect to Cloud SQL{detail}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
