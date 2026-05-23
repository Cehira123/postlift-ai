-- PostLift AI — Database Schema

CREATE TABLE IF NOT EXISTS merchants (
  shop_id          VARCHAR(255) PRIMARY KEY,
  shop_domain      VARCHAR(255) NOT NULL,
  margin_threshold DECIMAL(5,4) DEFAULT 0.30,
  stock_threshold  INT DEFAULT 5,
  plan             VARCHAR(50) DEFAULT 'starter',
  created_at       TIMESTAMP DEFAULT NOW(),
  updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  id           VARCHAR(255),
  shop_id      VARCHAR(255) REFERENCES merchants(shop_id),
  title        VARCHAR(500),
  variant_id   VARCHAR(255),
  price        DECIMAL(10,2),
  cost         DECIMAL(10,2),
  margin_rate  DECIMAL(5,4) GENERATED ALWAYS AS (
    CASE WHEN price > 0 THEN (price - cost) / price ELSE 0 END
  ) STORED,
  stock_qty    INT DEFAULT 0,
  updated_at   TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (id, shop_id)
);

CREATE TABLE IF NOT EXISTS offer_events (
  id                   SERIAL PRIMARY KEY,
  shop_id              VARCHAR(255) REFERENCES merchants(shop_id),
  order_id             VARCHAR(255),
  offered_product_id   VARCHAR(255),
  offer_copy           TEXT,
  accepted             BOOLEAN DEFAULT FALSE,
  added_revenue        DECIMAL(10,2) DEFAULT 0,
  created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_offer_events_shop_id ON offer_events(shop_id);
CREATE INDEX IF NOT EXISTS idx_offer_events_created_at ON offer_events(created_at);
CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id);
