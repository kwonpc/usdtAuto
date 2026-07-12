from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings

KST = timezone(timedelta(hours=9), name="KST")


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def kst_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).astimezone(KST).isoformat()


def kst_day_start_utc(value: datetime | None = None) -> datetime:
    base = _as_utc(value or utc_now()).astimezone(KST)
    return datetime.combine(base.date(), time.min, tzinfo=KST).astimezone(timezone.utc)


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    path = Path(database_url.removeprefix("sqlite:///"))
    path.parent.mkdir(parents=True, exist_ok=True)


def _oracle_connect_args(settings: Settings) -> dict[str, str]:
    if not settings.oracle_wallet_dir:
        return {}

    wallet_dir = str(Path(settings.oracle_wallet_dir).expanduser())
    connect_args = {
        "config_dir": wallet_dir,
        "wallet_location": wallet_dir,
    }
    if settings.oracle_wallet_password:
        connect_args["wallet_password"] = settings.oracle_wallet_password
    return connect_args


class Database:
    def __init__(self, settings: Settings):
        _ensure_sqlite_parent(settings.database_url)
        if settings.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        elif settings.database_url.startswith("oracle"):
            connect_args = _oracle_connect_args(settings)
        else:
            connect_args = {}
        self.engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=Session)

    def init(self) -> None:
        from app import db_models  # noqa: F401

        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        db = self.session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.database.session() as db:
        yield db
