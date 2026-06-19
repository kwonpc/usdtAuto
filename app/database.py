import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.config import Settings


def _db_path(settings: Settings) -> Path:
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported in this MVP")
    return Path(settings.database_url.removeprefix("sqlite:///"))


class Database:
    def __init__(self, settings: Settings):
        self.path = _db_path(settings)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS price_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    trade_price REAL NOT NULL,
                    bid_price REAL NOT NULL,
                    ask_price REAL NOT NULL,
                    usd_krw_rate REAL NOT NULL,
                    premium_rate REAL NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS virtual_trade (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL NOT NULL,
                    fee REAL NOT NULL,
                    profit REAL NOT NULL,
                    profit_rate REAL NOT NULL,
                    total_asset_krw REAL NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
