-- PostLift AI — データベーススキーマ v3
-- PostgreSQL 15+

-- ショップ（インストール済み Shopify ストア）
CREATE TABLE IF NOT EXISTS shops (
    id            BIGSERIAL    PRIMARY KEY,
    shop_domain   TEXT         NOT NULL UNIQUE,
    access_token  TEXT         NOT NULL,
    active        BOOLEAN      NOT NULL DEFAULT true,
    plan          TEXT         NOT NULL DEFAULT 'free',
    owner_email   TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- マーチャント設定（粗利閾値・在庫閾値など）
CREATE TABLE IF NOT EXISTS merchants (
    id                BIGSERIAL    PRIMARY KEY,
    shop_domain       TEXT         NOT NULL UNIQUE REFERENCES shops(shop_domain),
    margin_threshold  NUMERIC(5,4) NOT NULL DEFAULT 0.30,
    stock_threshold   INT          NOT NULL DEFAULT 5,
    plan              TEXT         NOT NULL DEFAULT 'starter',
    trial_ends_at     TIMESTAMPTZ,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_merchants_shop_domain ON merchants(shop_domain);

-- 商品マスタ（粗利・在庫管理）
CREATE TABLE IF NOT EXISTS products (
    id            BIGSERIAL     PRIMARY KEY,
    shop_domain   TEXT          NOT NULL,
    product_id    TEXT          NOT NULL,
    title         TEXT          NOT NULL,
    price         NUMERIC(12,2) NOT NULL,
    gross_margin  NUMERIC(5,2)  NOT NULL DEFAULT 0,
    stock_qty     INT           NOT NULL DEFAULT 0,
    accept_rate   NUMERIC(5,4),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(shop_domain, product_id)
);
CREATE INDEX IF NOT EXISTS idx_products_shop_domain ON products(shop_domain);

-- アップセルオファー履歴
CREATE TABLE IF NOT EXISTS upsell_offers (
    id              BIGSERIAL     PRIMARY KEY,
    id_str          TEXT          UNIQUE,
    shop_domain     TEXT          NOT NULL REFERENCES shops(shop_domain),
    order_id        TEXT          NOT NULL,
    product_id      TEXT          NOT NULL,
    upsell_price    NUMERIC(12,2) NOT NULL,
    gross_margin    NUMERIC(5,2),
    stock_qty       INT,
    accepted        BOOLEAN,
    ai_score        NUMERIC(5,4),
    ab_variant      TEXT,
    customer_id     TEXT,
    copy_text       TEXT,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    responded_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_upsell_offers_shop_domain ON upsell_offers(shop_domain);
CREATE INDEX IF NOT EXISTS idx_upsell_offers_created_at  ON upsell_offers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upsell_offers_order_id    ON upsell_offers(order_id);
CREATE INDEX IF NOT EXISTS idx_upsell_offers_expires_at  ON upsell_offers(expires_at)
    WHERE accepted IS NULL;

-- 請求
CREATE TABLE IF NOT EXISTS billing (
    id              BIGSERIAL     PRIMARY KEY,
    shop_domain     TEXT          NOT NULL REFERENCES shops(shop_domain),
    charge_id       TEXT          NOT NULL UNIQUE,
    status          TEXT          NOT NULL DEFAULT 'pending',
    plan            TEXT          NOT NULL,
    price_usd       NUMERIC(8,2)  NOT NULL,
    activated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 日次 KPI スナップショット
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id              BIGSERIAL     PRIMARY KEY,
    shop_domain     TEXT          NOT NULL REFERENCES shops(shop_domain),
    snapshot_date   DATE          NOT NULL,
    total_offers    INT           NOT NULL DEFAULT 0,
    accepted_offers INT           NOT NULL DEFAULT 0,
    accept_rate_pct NUMERIC(5,2),
    extra_revenue   NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(shop_domain, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_shop_date ON kpi_snapshots(shop_domain, snapshot_date DESC);

-- A/B テスト実験
CREATE TABLE IF NOT EXISTS ab_experiments (
    id              BIGSERIAL    PRIMARY KEY,
    shop_domain     TEXT         NOT NULL REFERENCES shops(shop_domain),
    experiment_name TEXT         NOT NULL,
    variant         TEXT         NOT NULL CHECK (variant IN ('A','B')),
    offer_id        TEXT         REFERENCES upsell_offers(id_str),
    converted       BOOLEAN,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ab_experiments_shop ON ab_experiments(shop_domain, experiment_name);

-- 顧客 RFM スコア
CREATE TABLE IF NOT EXISTS customer_scores (
    id              BIGSERIAL     PRIMARY KEY,
    shop_domain     TEXT          NOT NULL,
    customer_id     TEXT          NOT NULL,
    recency_days    INT,
    frequency       INT           NOT NULL DEFAULT 1,
    monetary        NUMERIC(12,2) NOT NULL DEFAULT 0,
    rfm_score       NUMERIC(5,4),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(shop_domain, customer_id)
);
CREATE INDEX IF NOT EXISTS idx_customer_scores_shop ON customer_scores(shop_domain);

-- Webhook 登録管理
CREATE TABLE IF NOT EXISTS webhook_registrations (
    id              BIGSERIAL    PRIMARY KEY,
    shop_domain     TEXT         NOT NULL REFERENCES shops(shop_domain),
    topic           TEXT         NOT NULL,
    shopify_id      BIGINT,
    address         TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(shop_domain, topic)
);
CREATE INDEX IF NOT EXISTS idx_webhook_reg_shop ON webhook_registrations(shop_domain);
