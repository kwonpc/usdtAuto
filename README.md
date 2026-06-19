# KRW-USDT 환율 괴리 기반 자동매매 봇 MVP

업비트 `KRW-USDT` 가격과 USD/KRW 환율의 괴리율을 계산하고, 기본값으로 Paper Trading만 수행하는 FastAPI 기반 MVP입니다.

## 실행

```bash
docker compose up -d
```

대시보드:

```text
http://localhost:8000/
```

상태 API:

```bash
curl http://localhost:8000/status
```

봇은 기본 `STOPPED` 상태입니다. 시작하려면:

```bash
curl -X POST http://localhost:8000/bot/start
```

중지:

```bash
curl -X POST http://localhost:8000/bot/stop
```

최근 거래:

```bash
curl http://localhost:8000/trades
```

## 전략

괴리율은 아래 공식으로 계산합니다.

```text
premium_rate = (upbit_usdt_price / usd_krw_rate - 1) * 100
```

- `premium_rate <= buy_premium_threshold`: USDT 저평가로 보고 매수
- `premium_rate >= sell_premium_threshold`: USDT 고평가로 보고 매도
- 그 외: 대기

## 설정

`config.yml`에서 변경합니다.

```yaml
trade_mode: paper
fx_provider: manual
manual_usd_krw_rate: 1370.0
buy_premium_threshold: -0.3
sell_premium_threshold: 0.3
max_order_amount: 10000000
daily_max_trade_amount: 50000000
daily_max_loss_rate: -1.0
```

`trade_mode: live`는 MVP에서 의도적으로 비활성화되어 있습니다.

## DB

SQLite 테이블:

- `price_snapshot`: 시세, 환율, 괴리율 스냅샷
- `virtual_trade`: 가상매매 체결 내역

## 주의

이 프로젝트는 수익을 보장하지 않으며, MVP 단계에서는 실거래가 구현되어 있지 않습니다. 최소 14일 이상 Paper Trading 결과를 확인한 뒤 실거래 모듈을 별도 검증하는 것을 전제로 합니다.
