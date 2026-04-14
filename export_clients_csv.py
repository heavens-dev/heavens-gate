from __future__ import annotations

import argparse
import csv
import datetime as dt
import sqlite3
from configparser import ConfigParser
from pathlib import Path
from typing import Literal

STATUS_TEXT = {
    0: "created",
    1: "ip_blocked",
    2: "account_blocked",
    3: "time_expired",
    4: "connected",
    5: "disconnected",
}

SUBSCRIPTION_TEXT = {
    "Default": "Classic",
    "Clear": "Clear",
}


CSV_COLUMNS = [
    "user_id",
    "name",
    "registered_at",
    "status_code",
    "status",
    "uses_service_now",
    "has_any_peer",
    "peer_count",
    "subscription_type_raw",
    "subscription_type",
    "subscription_expiry",
    "subscription_active_now",
    "layout",
]

DEFAULT_CONFIG_PATH = "config.conf"
DEFAULT_DELIMITER = ";"
DEFAULT_ENCODING = "utf-8-sig"
LayoutType = Literal["auto", "master", "canary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export_clients_csv",
        description="Export clients info to CSV (master/canary compatible)",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: config.conf)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"clients_dump_{dt.datetime.now():%Y%m%d_%H%M%S}.csv",
        help="Path to output CSV file",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite DB file. If omitted, uses db.path from config",
    )
    parser.add_argument(
        "--layout",
        choices=["auto", "master", "canary"],
        default="auto",
        help="DB layout to use (default: auto)",
    )
    parser.add_argument(
        "--delimiter",
        default=DEFAULT_DELIMITER,
        help="CSV delimiter (default: ';')",
    )
    parser.add_argument(
        "--encoding",
        default=DEFAULT_ENCODING,
        help="Output encoding (default: utf-8-sig)",
    )
    return parser.parse_args()


def _to_iso(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


def _status_to_text(status_value: int) -> str:
    return STATUS_TEXT.get(status_value, f"unknown_status({status_value})")


def _subscription_to_text(subscription_value: str | None) -> str:
    if not subscription_value:
        return ""

    return SUBSCRIPTION_TEXT.get(subscription_value, subscription_value)


def _parse_datetime(value: object) -> dt.datetime | None:
    if value is None:
        return None

    if isinstance(value, dt.datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return dt.datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _load_db_path_from_config(config_path: str) -> str:
    parser = ConfigParser(strict=False)
    if not parser.read(config_path):
        raise FileNotFoundError(f"Config file was not found: {config_path}")

    return parser.get("db", "path", fallback="db.sqlite")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row["name"]) for row in rows}


def _detect_layout(connection: sqlite3.Connection, requested_layout: str) -> str:
    if requested_layout in {"master", "canary"}:
        return requested_layout

    users_columns = _table_columns(connection, "Users") if _table_exists(connection, "Users") else set()

    if "subscription_type" in users_columns or "subscription_expiry" in users_columns:
        return "canary"

    if "expire_time" in users_columns:
        return "master"

    if _table_exists(connection, "Peers"):
        return "canary"

    if _table_exists(connection, "PeersTable"):
        return "master"

    raise RuntimeError("Could not detect DB layout. Use --layout master|canary explicitly.")


def _build_peer_count_map(connection: sqlite3.Connection, peers_table: str) -> dict[str, int]:
    peer_columns = _table_columns(connection, peers_table)
    if "user_id" in peer_columns:
        user_column = "user_id"
    elif "user" in peer_columns:
        user_column = "user"
    else:
        raise RuntimeError(f"Could not find user FK in {peers_table}")

    query = (
        f"SELECT {user_column} AS user_id, COUNT(*) AS peer_count "
        f"FROM {peers_table} GROUP BY {user_column}"
    )
    rows = connection.execute(query).fetchall()
    return {str(row["user_id"]): int(row["peer_count"]) for row in rows}


def _collect_rows_canary(
    connection: sqlite3.Connection,
    now: dt.datetime,
) -> list[dict[str, str | int | bool]]:
    peer_count_map = _build_peer_count_map(connection, "Peers")
    rows: list[dict[str, str | int | bool]] = []

    query = (
        "SELECT user_id, name, registered_at, status, subscription_type, subscription_expiry "
        "FROM Users ORDER BY registered_at"
    )

    for user in connection.execute(query).fetchall():
        user_id = str(user["user_id"])
        status_code = int(user["status"])
        subscription_expiry = _parse_datetime(user["subscription_expiry"])
        peer_count = peer_count_map.get(user_id, 0)
        uses_service_now = status_code == 4
        has_any_peer = peer_count > 0
        subscription_raw = (user["subscription_type"] or "").strip()

        has_subscription = bool(subscription_raw)
        subscription_active_now = False
        if has_subscription and subscription_expiry is not None:
            subscription_active_now = subscription_expiry >= now

        rows.append(
            {
                "user_id": user_id,
                "name": user["name"] or "",
                "registered_at": _to_iso(_parse_datetime(user["registered_at"])),
                "status_code": status_code,
                "status": _status_to_text(status_code),
                "uses_service_now": uses_service_now,
                "has_any_peer": has_any_peer,
                "peer_count": peer_count,
                "subscription_type_raw": subscription_raw,
                "subscription_type": _subscription_to_text(subscription_raw),
                "subscription_expiry": _to_iso(subscription_expiry),
                "subscription_active_now": subscription_active_now,
                "layout": "canary",
            }
        )

    return rows


def _collect_rows_master(
    connection: sqlite3.Connection,
    now: dt.datetime,
) -> list[dict[str, str | int | bool]]:
    peer_count_map = _build_peer_count_map(connection, "PeersTable")
    rows: list[dict[str, str | int | bool]] = []

    query = (
        "SELECT user_id, name, registered_at, status, expire_time "
        "FROM Users ORDER BY registered_at"
    )

    for user in connection.execute(query).fetchall():
        user_id = str(user["user_id"])
        status_code = int(user["status"])
        expire_time = _parse_datetime(user["expire_time"])
        peer_count = peer_count_map.get(user_id, 0)
        uses_service_now = status_code == 4
        has_any_peer = peer_count > 0

        subscription_active_now = False
        if expire_time is not None:
            subscription_active_now = expire_time >= now

        rows.append(
            {
                "user_id": user_id,
                "name": user["name"] or "",
                "registered_at": _to_iso(_parse_datetime(user["registered_at"])),
                "status_code": status_code,
                "status": _status_to_text(status_code),
                "uses_service_now": uses_service_now,
                "has_any_peer": has_any_peer,
                "peer_count": peer_count,
                "subscription_type_raw": "",
                "subscription_type": "",
                "subscription_expiry": _to_iso(expire_time),
                "subscription_active_now": subscription_active_now,
                "layout": "master",
            }
        )

    return rows


def collect_rows(
    connection: sqlite3.Connection,
    now: dt.datetime,
    layout: str,
) -> tuple[list[dict[str, str | int | bool]], str]:
    resolved_layout = _detect_layout(connection, layout)

    if resolved_layout == "canary":
        return _collect_rows_canary(connection, now), resolved_layout

    if resolved_layout == "master":
        return _collect_rows_master(connection, now), resolved_layout

    raise RuntimeError(f"Unsupported layout: {resolved_layout}")


def write_csv(
    rows: list[dict[str, str | int | bool]],
    output_path: Path,
    delimiter: str,
    encoding: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding=encoding) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def export_clients_dump(
    output_path: str | Path,
    config_path: str = DEFAULT_CONFIG_PATH,
    db_path: str | None = None,
    layout: LayoutType = "auto",
    delimiter: str = DEFAULT_DELIMITER,
    encoding: str = DEFAULT_ENCODING,
    now: dt.datetime | None = None,
) -> tuple[int, str, Path]:
    resolved_output_path = Path(output_path).expanduser()
    resolved_db_path = db_path or _load_db_path_from_config(config_path)

    connection = sqlite3.connect(resolved_db_path)
    connection.row_factory = sqlite3.Row

    try:
        export_time = now or dt.datetime.now()
        rows, resolved_layout = collect_rows(connection, export_time, layout)
        write_csv(rows, resolved_output_path, delimiter, encoding)
        return len(rows), resolved_layout, resolved_output_path.resolve()
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    clients_count, resolved_layout, resolved_output_path = export_clients_dump(
        output_path=args.output,
        config_path=args.config,
        db_path=args.db,
        layout=args.layout,
        delimiter=args.delimiter,
        encoding=args.encoding,
    )

    print(
        f"Exported {clients_count} clients from {resolved_layout} layout "
        f"to {resolved_output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
