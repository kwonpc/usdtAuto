# KRW-USDT 환율 괴리 기반 자동매매 봇 (MVP)

## 1. 프로젝트 개요

### 목적

업비트 KRW-USDT 시장에서 USDT 가격과 실제 USD/KRW 환율의 괴리를 활용하여 자동매매를 수행하는 시스템을 구축한다.

초기 버전(MVP)의 목적은 다음과 같다.

* 환율 기반 자동매매 전략 검증
* 가상매매(Paper Trading)
* 실시간 상태 확인
* 수익성 검증

실거래는 MVP 검증 이후 적용한다.

---

## 2. 기술 스택

### 필수

* Python 3.12+
* FastAPI
* SQLite
* APScheduler
* Docker
* Upbit Open API

### 선택

* Telegram Bot
* Redis
* PostgreSQL

---

## 3. 핵심 전략

### 전략명

PremiumRebalanceStrategy

### 개념

USDT는 USD 스테이블코인이므로 업비트 KRW-USDT 가격과 실제 USD/KRW 환율의 괴리를 계산한다.

괴리율 계산식

PremiumRate = ((UpbitUSDTPrice / USDKRWRate) - 1) * 100

예시

* 업비트 USDT 가격: 1,380원
* USD/KRW 환율: 1,370원

괴리율 = 0.73%

### 매수 조건

* PremiumRate <= -0.3%

의미:

* USDT 저평가
* 매수 시그널 발생

### 매도 조건

* PremiumRate >= 0.3%

의미:

* USDT 고평가
* 매도 시그널 발생

### 중립 구간

* -0.1% ~ +0.1%

의미:

* 거래하지 않음

---

## 4. 환율 데이터 수집

### 목적

실시간 USD/KRW 환율 조회

### 인터페이스

```python
class FxRateProvider:
    def get_usd_krw_rate(self) -> float:
        pass
```

### 구현체

* ManualFxRateProvider
* ApiFxRateProvider

### 요구사항

* 환율 조회 실패 시 마지막 정상값 사용
* 일정 시간 이상 갱신 실패 시 거래 중단

---

## 5. 시세 수집

### 업비트 수집 데이터

* 현재가
* 매수호가
* 매도호가

### 대상 마켓

KRW-USDT

### 수집 주기

기본:

* 10초

설정 가능해야 함

---

## 6. 데이터베이스

### price_snapshot

```sql
CREATE TABLE price_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT,
    trade_price REAL,
    bid_price REAL,
    ask_price REAL,
    usd_krw_rate REAL,
    premium_rate REAL,
    created_at DATETIME
);
```

### virtual_trade

```sql
CREATE TABLE virtual_trade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    side TEXT,
    price REAL,
    volume REAL,
    fee REAL,
    profit REAL,
    profit_rate REAL,
    total_asset_krw REAL,
    created_at DATETIME
);
```

---

## 7. 가상매매(Paper Trading)

### 초기 자산

* KRW: 100,000,000
* USDT: 0

### 동작 순서

1. 업비트 가격 조회
2. USD/KRW 환율 조회
3. 괴리율 계산
4. 매수 조건 확인
5. 매도 조건 확인
6. 가상 체결
7. 자산 계산
8. DB 저장

---

## 8. 수수료

설정값

```yaml
round_trip_fee_rate: 0.001
```

의미

* 왕복 수수료 0.10%

가상매매 손익 계산 시 반드시 반영

---

## 9. 상태 API

### GET /status

응답 예시

```json
{
  "botStatus": "RUNNING",
  "upbitUsdtPrice": 1380.0,
  "usdKrwRate": 1370.0,
  "premiumRate": 0.73,
  "krwBalance": 50000000,
  "usdtBalance": 36500,
  "avgBuyPrice": 1360.0,
  "totalAssetKrw": 100500000,
  "todayTradeCount": 2,
  "todayProfit": 500000,
  "lastSignal": "SELL",
  "lastSignalAt": "2025-06-19T10:00:00"
}
```

### GET /trades

최근 거래 내역 조회

### POST /bot/start

봇 시작

### POST /bot/stop

봇 중지

---

## 10. 설정 파일

```yaml
market: KRW-USDT

trade_mode: paper

initial_balance: 100000000

poll_interval_seconds: 10

fx_provider: manual
manual_usd_krw_rate: 1370.0

buy_premium_threshold: -0.3
sell_premium_threshold: 0.3

neutral_band: 0.1

round_trip_fee_rate: 0.001

max_order_amount: 10000000

daily_max_trade_amount: 50000000

daily_max_loss_rate: -1.0

fx_rate_max_stale_seconds: 300
```

---

## 11. 봇 상태

```python
STOPPED
RUNNING
PAUSED_BY_RISK
ERROR
```

---

## 12. 거래 상태

```python
SIGNAL_CREATED

BUY_EXECUTED
SELL_EXECUTED

ORDER_PLACED

PARTIALLY_FILLED
FILLED

CANCELLED
FAILED
```

---

## 13. 리스크 관리

### 필수

* 기본 모드는 paper
* 실거래는 live 모드일 때만 허용
* 하루 최대 거래금액 제한
* 하루 최대 손실률 제한
* 환율 데이터 이상 시 거래 중단
* API 장애 시 거래 중단
* 예외 발생 시 ERROR 상태 전환

---

## 14. 실거래 확장 (2차)

trade_mode=live 인 경우만 활성화

### 기능

* 업비트 주문
* 주문 조회
* 주문 취소
* 잔고 조회

### 주문 방식

* 지정가 주문
* 시장가 주문 사용 금지

---

## 15. 프로젝트 구조

```text
trading-bot/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│
│   ├── exchange/
│   │    └── upbit.py
│
│   ├── fx/
│   │    ├── provider.py
│   │    ├── manual_provider.py
│   │    └── api_provider.py
│
│   ├── strategy/
│   │    └── premium_rebalance_strategy.py
│
│   ├── service/
│   │    ├── bot_service.py
│   │    ├── paper_trade_service.py
│   │    └── live_trade_service.py
│
│   └── api/
│        └── routes.py
│
├── config.yml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 16. 개발 우선순위

1. 프로젝트 생성
2. 업비트 시세 조회
3. 환율 조회
4. 괴리율 계산
5. SQLite 저장
6. 가상매매 구현
7. 상태 API 구현
8. Docker 환경 구성
9. 실거래 인터페이스 작성
10. 실거래 적용

---

## 17. 검증 단계

실거래 전 최소 14일간 Paper Trading 수행

검증 항목

* 시그널 발생 횟수
* 누적 수익률
* 최대 손실률
* 거래 성공률
* 거래 빈도
* 전략 안정성

Paper Trading 검증 완료 후 실거래 적용 여부를 결정한다.
