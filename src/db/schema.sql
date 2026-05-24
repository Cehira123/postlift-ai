-- PostLift AI — データベーススキーマ
-- PostgreSQL 15+

-- ショップ (インストール済み Shopify ストア)
CREATE TABLE IF NOT EXISTS shops (
    id            BIGSERIAL PRIMARY KEY,
    shop_domain   TEXT        NOT NULL UNIQUE,
    access_token  TEXT        NOT NULL,
    active        BOOLEAN     NOT NULL DEFAULT true,
    plan          TEXT        NOT NULL DEFAULT 'free',  -- 'free' | 'growth' | 'scale'
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- アップセルオファー履歴
CREATE TABLE IF NOT EXISTS upsell_offers (
    id              BIGSERIAL PRIMARY KEY,
    shop_domain     TEXT        NOT NULL REFERENCES shops(shop_domain),
    order_id        TEXT        NOT NULL,          -- Shopify Order GID
    product_id      TEXT        NOT NULL,          -- 提案商品
    upsell_price    NUMERIC(12,2) NOT NULL,
    gross_margin    NUMERIC(5,2),                  -- 粗利率 (%)
    stock_qty       INT,
    accepted        BOOLEAN,                       -- NULL=未回答, true=承諾, false=拒否
    ai_score        NUMERIC(5,4),                  -- モデルの信頼スコア 0-1
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at    TIMESTAMPTZ
);

-- 請求
CREATE TABLE IF NOT EXISTS billing (
    id              BIGSERIAL PRIMARY KEY,
    shop_domain     TEXT        NOT NULL REFERENCES shops(shop_domain),
    charge_id       TEXT        NOT NULL UNIQUE,   -- Shopify charge ID
    status          TEXT        NOT NULL DEFAULT 'pending',  -- pending | active | cancelled
    plan            TEXT        NOT NULL,
    price_usd       NUMERIC(8,2) NOT NULL,
    activated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_upsell_offers_shop_domain ON upsell_offers(shop_domain);
CREATE INDEX IF NOT EXISTS idx_upsell_offers_created_at  ON upsell_offers(created_at DESC);
