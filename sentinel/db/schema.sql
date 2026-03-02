-- SENTINEL TimescaleDB Schema
-- LiQUiD SOUND | CTO: Captain Urahara
-- Run via: psql $TIMESCALEDB_URL -f schema.sql
-- Or automatically via docker-compose (mounted to initdb.d)

-- ─────────────────────────────────────────────
-- Extension
-- ─────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy text search on token names

-- ─────────────────────────────────────────────
-- Token Events (main time-series table)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS token_events (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    mint            TEXT            NOT NULL,   -- Solana mint address
    name            TEXT,
    symbol          TEXT,
    score           FLOAT,                      -- SENTINEL composite score 0–100
    volume_sol      FLOAT,
    holders         INTEGER,
    market_cap_usd  FLOAT,
    liquidity_usd   FLOAT,
    social_score    FLOAT,                      -- NOVA social velocity score
    risk_flags      TEXT[],                     -- ['low_liquidity', 'no_socials', ...]
    source          TEXT DEFAULT 'pumpportal',  -- data source
    raw_data        JSONB                        -- full raw event payload
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable(
    'token_events',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_token_events_mint
    ON token_events (mint, time DESC);

CREATE INDEX IF NOT EXISTS idx_token_events_score
    ON token_events (score DESC, time DESC);

CREATE INDEX IF NOT EXISTS idx_token_events_symbol
    ON token_events USING gin (symbol gin_trgm_ops);

-- ─────────────────────────────────────────────
-- Alerts (delivery tracking)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    mint            TEXT            NOT NULL,
    symbol          TEXT,
    alert_type      TEXT,           -- 'high_score', 'rug_risk', 'social_spike'
    score           FLOAT,
    channel         TEXT,           -- 'slack', 'discord', 'telegram'
    channel_id      TEXT,
    message_id      TEXT,
    delivered_at    TIMESTAMPTZ,
    approved_by     TEXT,           -- 'YORUICHI' when manually approved
    dismissed       BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable(
    'alerts',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_alerts_mint
    ON alerts (mint, time DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_type
    ON alerts (alert_type, time DESC);

-- ─────────────────────────────────────────────
-- NOVA Social Scans (social velocity log)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nova_scans (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    platform        TEXT,           -- 'twitter', 'reddit', 'tiktok'
    scan_type       TEXT,           -- 'full', 'targeted'
    keywords        TEXT[],
    results_count   INTEGER,
    scan_duration_s FLOAT,
    raw_data        JSONB
);

SELECT create_hypertable(
    'nova_scans',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ─────────────────────────────────────────────
-- Continuous Aggregates (pre-computed rollups)
-- ─────────────────────────────────────────────

-- Hourly token stats
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_token_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    COUNT(*)                    AS event_count,
    AVG(score)                  AS avg_score,
    MAX(score)                  AS max_score,
    AVG(volume_sol)             AS avg_volume_sol,
    AVG(social_score)           AS avg_social_score
FROM token_events
GROUP BY bucket, symbol
WITH NO DATA;

-- Refresh policy: keep hourly stats updated
SELECT add_continuous_aggregate_policy(
    'hourly_token_stats',
    start_offset  => INTERVAL '3 hours',
    end_offset    => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ─────────────────────────────────────────────
-- Retention Policies
-- ─────────────────────────────────────────────

-- Raw token events: keep 90 days
SELECT add_retention_policy(
    'token_events',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Alerts: keep 1 year
SELECT add_retention_policy(
    'alerts',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- NOVA scans: keep 30 days
SELECT add_retention_policy(
    'nova_scans',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ─────────────────────────────────────────────
-- Useful Views
-- ─────────────────────────────────────────────

-- Top tokens in last 24h by score
CREATE OR REPLACE VIEW top_tokens_24h AS
SELECT
    symbol,
    name,
    MAX(score)          AS peak_score,
    MAX(social_score)   AS peak_social,
    COUNT(*)            AS event_count,
    MAX(market_cap_usd) AS latest_mcap,
    MIN(time)           AS first_seen,
    MAX(time)           AS last_seen
FROM token_events
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY symbol, name
ORDER BY peak_score DESC
LIMIT 50;

-- Undelivered high-score alerts
CREATE OR REPLACE VIEW pending_alerts AS
SELECT *
FROM alerts
WHERE delivered_at IS NULL
  AND dismissed = FALSE
  AND time > NOW() - INTERVAL '1 hour'
ORDER BY score DESC, time DESC;
