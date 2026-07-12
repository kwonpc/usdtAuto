# USDT Auto Trading Bot

업비트/빗썸 `KRW-USDT` 시장을 대상으로 사용자별 매매봇을 관리하는 FastAPI 기반 MVP입니다. 기본값은 Paper Trading이며, 실주문 실행은 아직 비활성화되어 있습니다.

## 주요 기능

- 가입 / 로그인
- JWT Bearer 인증
- 사용자별 기본 매매봇 생성
- 사용자별 거래소 API 키 암호화 저장
- 사용자별 매매 설정관리
- 사용자별 거래내역 조회
- 기준가 로스컷, 일일 거래금액 제한, 일일 손실률 제한
- 모바일 대시보드 탭 메뉴
- 전략 선택
  - `premium_rebalance`: 거래소 USDT 가격과 USD/KRW 환율 괴리율 기반
  - `base_price_gap`: 기준가격과 기준차이가격 기반
- SQLAlchemy 기반 DB 계층
- SQLite 개발 실행, Oracle Cloud ATP/ADB 전자지갑 연결 지원
- Docker / Docker Compose 구성 및 배포 helper 스크립트
- `logs/app.log` 파일 로그 저장 및 회전

## 실행

```bash
docker compose up -d
```

대시보드:

```text
http://localhost:8000/
```

모바일 화면에서는 `현황`, `설정`, `거래내역`, `API/리스크`, `수동매도` 탭으로 나뉘어 표시됩니다. PC 화면에서는 같은 버튼이 해당 영역으로 스크롤 이동합니다.

## 배포 스크립트

서버에서는 아래 스크립트로 실행을 관리합니다. `docker compose`가 있으면 우선 사용하고, 없으면 구버전 `docker-compose`로 fallback합니다.

```bash
./deploy.sh
./start.sh
./stop.sh
```

- `deploy.sh`: `git pull` 후 `config_bak.yml`을 `config.yml`로 복사하고 컨테이너를 재빌드/기동합니다.
- `start.sh`: 기존 이미지/설정으로 컨테이너를 기동합니다.
- `stop.sh`: 컨테이너를 종료합니다.

서버에는 민감정보가 들어간 `config_bak.yml`을 별도로 만들어두고, Git에는 올리지 않습니다. Ubuntu 20.04 minimal + 구버전 Docker Compose 기준 전체 명령은 `DEPLOY_UBUNTU_20_04.md`를 참고합니다.

## 로그

앱 로그는 컨테이너 stdout과 함께 `logs/app.log`에도 저장됩니다. Docker Compose 실행 시 `./logs:/app/logs`로 마운트되므로 컨테이너를 재시작해도 서버의 `logs/` 폴더에 남습니다.

```bash
docker-compose logs -f
tail -f logs/app.log
```

기본값은 10MB 단위로 최대 5개 백업 파일까지 회전 저장합니다. 필요하면 `config.yml` 또는 환경변수로 아래 값을 조정합니다.

```yaml
log_dir: logs
log_level: INFO
log_max_bytes: 10485760
log_backup_count: 5
```

## 로컬 개발 실행

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 인증 API 예시

가입:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"login_id":"demo","password":"password1234"}'
```

로그인:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login_id":"demo","password":"password1234"}'
```

보호 API 호출:

```bash
curl http://localhost:8000/status \
  -H "Authorization: Bearer $TOKEN"
```

## 매매 설정

대시보드의 매매 설정관리에서 변경하거나 아래 API를 사용합니다.

```json
{
  "exchange": "upbit",
  "market": "KRW-USDT",
  "trade_mode": "paper",
  "strategy_type": "base_price_gap",
  "base_price": 1500,
  "price_gap": 3,
  "max_order_amount": 10000000,
  "base_loss_cut_price": 1480,
  "daily_max_trade_amount": 50000000,
  "daily_max_loss_rate": -2.5,
  "manual_usd_krw_rate": 1370
}
```

`base_price_gap` 전략:

- 보유 USDT가 없고 `현재가 <= 기준가격 - 기준차이가격`이면 매수
- 보유 USDT가 있고 `현재가 >= 평균매수가 + 기준차이가격`이면 매도
- 보유 USDT가 있고 `base_loss_cut_price`가 설정되어 있으며 `현재가 <= base_loss_cut_price`이면 가상 전량 매도 후 `PAUSED_BY_RISK`로 전환

`premium_rebalance` 전략:

```text
premium_rate = (exchange_usdt_price / usd_krw_rate - 1) * 100
```

- `premium_rate <= buy_premium_threshold`: 매수
- `premium_rate >= sell_premium_threshold`: 매도

리스크 제한:

- `base_loss_cut_price`: 기준가 전략 로스컷 기준가입니다. 비어 있으면 사용하지 않습니다.
- `daily_max_trade_amount`: 당일 누적 거래금액이 제한값 이상이면 `PAUSED_BY_RISK`로 전환합니다.
- `daily_max_loss_rate`: 총자산 기준 당일 손실률이 제한값 이하이면 `PAUSED_BY_RISK`로 전환합니다. 예를 들어 `-2.5`는 하루 손실 -2.5% 제한입니다.

## 체결 수량 처리 정책

현재 Paper Trading은 주문이 전량 체결된 것으로 가정합니다. 실거래 모듈을 붙일 때는 주문금액 기준이 아니라 거래소에서 확인한 실제 체결수량 기준으로 포지션을 관리해야 합니다.

- 매수 주문이 일부만 체결되면 `trades.volume`에는 실제 매수된 USDT 수량만 저장합니다.
- 이후 매도는 최초 주문금액이 아니라 현재 보유 중인 USDT 수량만 대상으로 냅니다.
- 매도 주문도 일부만 체결되면 체결된 수량만 `SELL` 거래로 저장하고, 남은 USDT는 계속 보유수량으로 유지합니다.
- 남은 수량은 다음 매도 신호에서 다시 매도 대상이 됩니다.
- 실거래 주문 상태는 `ORDER_PLACED`, `PARTIALLY_FILLED`, `FILLED`, `CANCELLED`, `FAILED` 같은 상태로 추적할 예정입니다.

예시:

```text
1회 주문금액: 10,000,000원
매수 주문 실제 체결: 6,000,000원 상당 USDT

=> 보유수량은 6,000,000원 상당 USDT만 반영
=> 이후 매도 신호 발생 시 10,000,000원어치가 아니라 보유 중인 USDT만 매도
=> 매도도 50%만 체결되면 나머지 50% USDT는 계속 보유
```

## 봇 오류 처리 정책

RUNNING 상태의 봇은 주기적으로 시세/환율 조회, 전략 판단, 가상 체결을 수행합니다.

- 거래소 시세 API 실패, 환율 API 실패, 외부 네트워크 timeout 같은 일시 실패는 `ERROR`로 멈추지 않습니다.
- 일시 실패는 `last_error`에 기록하고 봇 상태는 `RUNNING`으로 유지하여 다음 tick에서 재시도합니다.
- DB 저장 실패, 계산 로직 예외, 예상하지 못한 내부 오류는 `ERROR`로 전환합니다.
- 기준가 로스컷, 일일 거래금액 초과, 일일 손실률 초과는 `PAUSED_BY_RISK`로 전환합니다.

실거래 주문 실행은 아직 구현되어 있지 않습니다. `trade_mode=live`로 시작하면 봇은 `ERROR`가 되고 주문은 전송하지 않습니다.

## DB

현재 기본 설정은 SQLite입니다.

```yaml
database_url: sqlite:///./data/trading_bot.db
```

Oracle Cloud Free Tier DB로 전환할 때는 `DATABASE_URL` 환경변수 또는 `config.yml`의 `database_url`을 SQLAlchemy Oracle URL로 지정합니다.

```text
oracle+oracledb://USER:PASSWORD@HOST:1521/?service_name=SERVICE
```

전자지갑(mTLS)이 필요한 Autonomous Database는 TNS alias와 wallet 디렉터리를 함께 지정합니다.

```yaml
database_url: oracle+oracledb://USER:PASSWORD@DB_TNS_ALIAS
oracle_wallet_dir: ./wallet
oracle_wallet_password: WALLET_PASSWORD
```

서버 배포 시에는 wallet 압축을 풀어 `./wallet` 같은 경로에 두고, `config_bak.yml`에 위 값을 넣어둡니다. `config.yml`, `config_bak.yml`, wallet 파일은 민감정보이므로 Git에 올리지 않습니다.

주요 테이블:

- `users`
- `upbit_api_keys`
- `trading_bots`
- `bot_settings`
- `price_snapshots`
- `trades`

DB migration files:

- `oracle_migration_add_bithumb_exchange.sql`: 빗썸/거래소 구분 컬럼 추가
- `oracle_migration_add_risk_controls.sql`: 기준가 로스컷용 `bot_settings.base_loss_cut_price` 컬럼 추가

기존 Oracle DB에 빗썸/거래소 구분 컬럼만 추가하려면 `oracle_migration_add_bithumb_exchange.sql`을 적용합니다.
기존 Oracle DB에 기준가 로스컷 컬럼만 추가하려면 `oracle_migration_add_risk_controls.sql`을 적용합니다.

### 테이블 컬럼

#### `users`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | 사용자 ID |
| `login_id` | `String(100)` | Unique, Index | 로그인 아이디 |
| `password_hash` | `String(255)` |  | 비밀번호 해시 |
| `created_at` | `DateTime` |  | 생성 시각 |

#### `upbit_api_keys`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | API 키 ID |
| `user_id` | `Integer` | FK, Index | `users.id` |
| `exchange` | `String(20)` | Index | `upbit` 또는 `bithumb` |
| `name` | `String(100)` |  | 사용자가 지정한 키 이름 |
| `access_key_encrypted` | `Text` |  | 암호화된 거래소 Access Key |
| `secret_key_encrypted` | `Text` |  | 암호화된 거래소 Secret Key |
| `is_active` | `Boolean` |  | 사용 여부 |
| `created_at` | `DateTime` |  | 생성 시각 |

#### `trading_bots`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | 매매봇 ID |
| `user_id` | `Integer` | FK, Index | `users.id` |
| `api_key_id` | `Integer` | FK, Nullable | `upbit_api_keys.id` |
| `name` | `String(100)` |  | 봇 이름 |
| `exchange` | `String(20)` | Index | 거래소, `upbit` 또는 `bithumb` |
| `market` | `String(30)` |  | 거래 마켓, 기본 `KRW-USDT` |
| `trade_mode` | `String(20)` |  | `paper` 또는 `live` |
| `strategy_type` | `String(50)` |  | `premium_rebalance` 또는 `base_price_gap` |
| `bot_status` | `String(30)` |  | `STOPPED`, `RUNNING`, `PAUSED_BY_RISK`, `ERROR` |
| `last_signal` | `String(20)` |  | 최근 신호, `BUY`, `SELL`, `HOLD` |
| `last_signal_at` | `DateTime` | Nullable | 최근 신호 시각 |
| `last_error` | `Text` | Nullable | 최근 오류 메시지 |
| `created_at` | `DateTime` |  | 생성 시각 |

#### `bot_settings`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | 설정 ID |
| `bot_id` | `Integer` | FK, Unique, Index | `trading_bots.id` |
| `initial_balance` | `Float` |  | 가상매매 초기 KRW 잔고 |
| `buy_premium_threshold` | `Float` |  | 환율괴리 전략 매수 기준 괴리율 |
| `sell_premium_threshold` | `Float` |  | 환율괴리 전략 매도 기준 괴리율 |
| `neutral_band` | `Float` |  | 중립 구간 |
| `base_price` | `Float` | Nullable | 기준가격 전략의 기준가격 |
| `price_gap` | `Float` |  | 기준차이가격 |
| `round_trip_fee_rate` | `Float` |  | 왕복 수수료율 |
| `max_order_amount` | `Float` |  | 1회 최대 주문금액 |
| `base_loss_cut_price` | `Float` | Nullable | 기준가 전략 로스컷 기준가. 비어 있으면 미사용 |
| `daily_max_trade_amount` | `Float` |  | 일일 최대 거래금액 |
| `daily_max_loss_rate` | `Float` |  | 일일 최대 손실률 |
| `fx_provider` | `String(20)` |  | `manual` 또는 `api` |
| `manual_usd_krw_rate` | `Float` |  | 수동 USD/KRW 환율 |
| `fx_rate_max_stale_seconds` | `Integer` |  | 환율 데이터 최대 허용 지연시간 |
| `updated_at` | `DateTime` |  | 수정 시각 |

#### `price_snapshots`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | 시세 스냅샷 ID |
| `user_id` | `Integer` | FK, Index | `users.id` |
| `bot_id` | `Integer` | FK, Index | `trading_bots.id` |
| `exchange` | `String(20)` | Index | 거래소, `upbit` 또는 `bithumb` |
| `market` | `String(30)` |  | 거래 마켓 |
| `trade_price` | `Float` |  | 현재가 |
| `bid_price` | `Float` |  | 최우선 매수호가 |
| `ask_price` | `Float` |  | 최우선 매도호가 |
| `usd_krw_rate` | `Float` | Nullable | USD/KRW 환율 |
| `premium_rate` | `Float` | Nullable | 환율 괴리율 |
| `created_at` | `DateTime` |  | 생성 시각 |

#### `trades`

| 컬럼 | 타입 | 키 | 설명 |
| --- | --- | --- | --- |
| `id` | `Integer` | PK | 거래 ID |
| `user_id` | `Integer` | FK, Index | `users.id` |
| `bot_id` | `Integer` | FK, Index | `trading_bots.id` |
| `exchange` | `String(20)` | Index | 거래소, `upbit` 또는 `bithumb` |
| `side` | `String(20)` |  | `BUY` 또는 `SELL` |
| `price` | `Float` |  | 체결 가격 |
| `volume` | `Float` |  | 체결 수량 |
| `fee` | `Float` |  | 수수료 |
| `profit` | `Float` |  | 실현 손익 |
| `profit_rate` | `Float` |  | 실현 손익률 |
| `total_asset_krw` | `Float` |  | 체결 후 총자산 평가액 |
| `trade_mode` | `String(20)` |  | `paper` 또는 `live` |
| `status` | `String(30)` |  | 거래 상태 |
| `created_at` | `DateTime` |  | 생성 시각 |

## 보안 메모

- 운영 배포 전 `jwt_secret_key`와 `encryption_key`를 반드시 변경하세요.
- 거래소 Secret Key는 암호화 저장되며 API 응답에는 노출하지 않습니다.
- `trade_mode=live`는 현재 실주문 미구현 상태라 ERROR로 전환됩니다.

## Oracle Cloud VM 배포 메모

Micro VM에서는 앱을 가볍게 유지하는 것이 중요합니다. 우선은 단일 FastAPI 프로세스와 APScheduler로 운영할 수 있지만, 실거래 적용 전에는 웹 API와 매매 워커를 분리하는 구조를 권장합니다.
