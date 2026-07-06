from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import UpbitApiKey, User
from app.dependencies import current_user
from app.schemas import ApiKeyCreateRequest, BotSettingsRequest, LoginRequest, ManualSellRequest, RegisterRequest
from app.security import create_access_token, encrypt_secret, hash_password, verify_password

router = APIRouter()


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/auth/register")
def register(request: Request, payload: RegisterRequest, db: DbSession):
    exists = db.scalar(select(User).where(User.login_id == payload.login_id))
    if exists is not None:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Login ID already exists")

    user = User(login_id=payload.login_id, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    request.app.state.bot_manager.ensure_default_bot(db, user.id)
    token = create_access_token(request.app.state.settings, str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
def login(request: Request, payload: LoginRequest, db: DbSession):
    user = db.scalar(select(User).where(User.login_id == payload.login_id))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid login ID or password")
    token = create_access_token(request.app.state.settings, str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "login_id": user.login_id}


@router.get("/status")
def status(request: Request, user: CurrentUser, db: DbSession):
    return request.app.state.bot_manager.status_payload(db, user.id)


@router.get("/trades")
def trades(request: Request, user: CurrentUser, db: DbSession, limit: int = Query(default=50, ge=1, le=500)):
    bot = request.app.state.bot_manager.get_user_bot(db, user.id)
    return [
        {
            "id": trade.id,
            "bot_id": trade.bot_id,
            "exchange": trade.exchange,
            "side": trade.side,
            "price": trade.price,
            "volume": trade.volume,
            "fee": trade.fee,
            "profit": trade.profit,
            "profit_rate": trade.profit_rate,
            "total_asset_krw": trade.total_asset_krw,
            "trade_mode": trade.trade_mode,
            "status": trade.status,
            "created_at": trade.created_at.isoformat(),
        }
        for trade in request.app.state.bot_manager.recent_trades(db, user.id, bot.id, limit)
    ]


@router.post("/bot/start")
def start_bot(request: Request, user: CurrentUser, db: DbSession):
    request.app.state.bot_manager.start(db, user.id)
    return request.app.state.bot_manager.status_payload(db, user.id)


@router.post("/bot/stop")
def stop_bot(request: Request, user: CurrentUser, db: DbSession):
    request.app.state.bot_manager.stop(db, user.id)
    return request.app.state.bot_manager.status_payload(db, user.id)


@router.post("/bot/manual-sell")
def manual_sell(request: Request, payload: ManualSellRequest, user: CurrentUser, db: DbSession):
    try:
        trade = request.app.state.bot_manager.manual_sell(db, user.id, price=payload.price, volume=payload.volume)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": trade.id,
        "exchange": trade.exchange,
        "side": trade.side,
        "price": trade.price,
        "volume": trade.volume,
        "fee": trade.fee,
        "profit": trade.profit,
        "profit_rate": trade.profit_rate,
        "total_asset_krw": trade.total_asset_krw,
        "created_at": trade.created_at.isoformat(),
    }


@router.get("/bot/settings")
def get_bot_settings(request: Request, user: CurrentUser, db: DbSession):
    bot = request.app.state.bot_manager.get_user_bot(db, user.id)
    setting = bot.settings
    return {
        "botId": bot.id,
        "exchange": bot.exchange,
        "market": bot.market,
        "trade_mode": bot.trade_mode,
        "strategy_type": bot.strategy_type,
        "api_key_id": bot.api_key_id,
        "buy_premium_threshold": setting.buy_premium_threshold,
        "sell_premium_threshold": setting.sell_premium_threshold,
        "neutral_band": setting.neutral_band,
        "base_price": setting.base_price,
        "price_gap": setting.price_gap,
        "round_trip_fee_rate": setting.round_trip_fee_rate,
        "max_order_amount": setting.max_order_amount,
        "daily_max_trade_amount": setting.daily_max_trade_amount,
        "daily_max_loss_rate": setting.daily_max_loss_rate,
        "fx_provider": setting.fx_provider,
        "manual_usd_krw_rate": setting.manual_usd_krw_rate,
        "fx_rate_max_stale_seconds": setting.fx_rate_max_stale_seconds,
    }


@router.put("/bot/settings")
def update_bot_settings(request: Request, payload: BotSettingsRequest, user: CurrentUser, db: DbSession):
    if payload.base_price is not None:
        payload.strategy_type = "base_price_gap"
    try:
        request.app.state.bot_manager.update_settings(db, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return request.app.state.bot_manager.status_payload(db, user.id)


@router.get("/api-keys")
def list_api_keys(user: CurrentUser, db: DbSession):
    keys = db.scalars(select(UpbitApiKey).where(UpbitApiKey.user_id == user.id).order_by(UpbitApiKey.id.desc())).all()
    return [
        {
            "id": key.id,
            "exchange": key.exchange,
            "name": key.name,
            "is_active": key.is_active,
            "created_at": key.created_at.isoformat(),
        }
        for key in keys
    ]


@router.post("/api-keys")
def create_api_key(request: Request, payload: ApiKeyCreateRequest, user: CurrentUser, db: DbSession):
    key = UpbitApiKey(
        user_id=user.id,
        exchange=payload.exchange,
        name=payload.name,
        access_key_encrypted=encrypt_secret(request.app.state.settings, payload.access_key),
        secret_key_encrypted=encrypt_secret(request.app.state.settings, payload.secret_key),
    )
    db.add(key)
    db.flush()
    return {"id": key.id, "name": key.name, "is_active": key.is_active, "created_at": key.created_at.isoformat()}
