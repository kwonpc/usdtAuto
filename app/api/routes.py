from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/status")
def status(request: Request):
    return request.app.state.bot.status_payload()


@router.get("/trades")
def trades(request: Request, limit: int = Query(default=50, ge=1, le=500)):
    return request.app.state.bot.recent_trades(limit)


@router.post("/bot/start")
def start_bot(request: Request):
    request.app.state.bot.start()
    return request.app.state.bot.status_payload()


@router.post("/bot/stop")
def stop_bot(request: Request):
    request.app.state.bot.stop()
    return request.app.state.bot.status_payload()
