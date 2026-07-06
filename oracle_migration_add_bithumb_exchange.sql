ALTER TABLE upbit_api_keys ADD (
    exchange VARCHAR2(20) DEFAULT 'upbit' NOT NULL
);

ALTER TABLE trading_bots ADD (
    exchange VARCHAR2(20) DEFAULT 'upbit' NOT NULL
);

ALTER TABLE price_snapshots ADD (
    exchange VARCHAR2(20) DEFAULT 'upbit' NOT NULL
);

ALTER TABLE trades ADD (
    exchange VARCHAR2(20) DEFAULT 'upbit' NOT NULL
);

CREATE INDEX ix_upbit_api_keys_exchange ON upbit_api_keys (exchange);
CREATE INDEX ix_trading_bots_exchange ON trading_bots (exchange);
CREATE INDEX ix_price_snapshots_exchange ON price_snapshots (exchange);
CREATE INDEX ix_trades_exchange ON trades (exchange);
