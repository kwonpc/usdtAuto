from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    api_keys: Mapped[list["UpbitApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bots: Mapped[list["TradingBot"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UpbitApiKey(Base):
    __tablename__ = "upbit_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="upbit", nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    access_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="api_keys")
    bots: Mapped[list["TradingBot"]] = relationship(back_populates="api_key")


class TradingBot(Base):
    __tablename__ = "trading_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("upbit_api_keys.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="upbit", nullable=False)
    market: Mapped[str] = mapped_column(String(30), default="KRW-USDT", nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(20), default="paper", nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(50), default="premium_rebalance", nullable=False)
    bot_status: Mapped[str] = mapped_column(String(30), default="STOPPED", nullable=False)
    last_signal: Mapped[str] = mapped_column(String(20), default="HOLD", nullable=False)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="bots")
    api_key: Mapped[UpbitApiKey | None] = relationship(back_populates="bots")
    settings: Mapped["BotSetting"] = relationship(back_populates="bot", cascade="all, delete-orphan", uselist=False)
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="bot", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="bot", cascade="all, delete-orphan")


class BotSetting(Base):
    __tablename__ = "bot_settings"
    __table_args__ = (UniqueConstraint("bot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("trading_bots.id"), index=True, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, default=100_000_000, nullable=False)
    buy_premium_threshold: Mapped[float] = mapped_column(Float, default=-0.3, nullable=False)
    sell_premium_threshold: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    neutral_band: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    base_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_gap: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    round_trip_fee_rate: Mapped[float] = mapped_column(Float, default=0.001, nullable=False)
    max_order_amount: Mapped[float] = mapped_column(Float, default=10_000_000, nullable=False)
    daily_max_trade_amount: Mapped[float] = mapped_column(Float, default=50_000_000, nullable=False)
    daily_max_loss_rate: Mapped[float] = mapped_column(Float, default=-1.0, nullable=False)
    base_loss_cut_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fx_provider: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    manual_usd_krw_rate: Mapped[float] = mapped_column(Float, default=1370.0, nullable=False)
    fx_rate_max_stale_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    bot: Mapped[TradingBot] = relationship(back_populates="settings")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    bot_id: Mapped[int] = mapped_column(ForeignKey("trading_bots.id"), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="upbit", nullable=False)
    market: Mapped[str] = mapped_column(String(30), nullable=False)
    trade_price: Mapped[float] = mapped_column(Float, nullable=False)
    bid_price: Mapped[float] = mapped_column(Float, nullable=False)
    ask_price: Mapped[float] = mapped_column(Float, nullable=False)
    usd_krw_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    premium_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    bot: Mapped[TradingBot] = relationship(back_populates="snapshots")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    bot_id: Mapped[int] = mapped_column(ForeignKey("trading_bots.id"), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="upbit", nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    profit_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_asset_krw: Mapped[float] = mapped_column(Float, nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(20), default="paper", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="FILLED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    bot: Mapped[TradingBot] = relationship(back_populates="trades")
