CREATE INDEX ix_price_snapshots_bot_latest
    ON price_snapshots (user_id, bot_id, id);
