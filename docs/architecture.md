# アーキテクチャ詳細：PostLift AI

## 全体構成

```
[Shopify Store]
  │
  │ 1. Order webhook
  ▼
[Webhook Handler]
  │
  │ 2. 注文データ取得・検証
  ▼
[Offer Engine]
  ├── Product Service    ... Admin API で商品・粗利・在庫取得
  ├── Customer Service   ... 購入履歴スコアリング
  ├── Scoring Service    ... 多軸スコア計算
  └── LLM Service        ... オファーコピー生成
  │
  │ 3. オファー候補（スコア付き）
  ▼
[Redis Cache]             ... TTL付きでオファー候補をキャッシュ
  │
  │ 4. Extension が取得
  ▼
[Post-Purchase Extension] ... Shopify Checkout UI Extension
  │
  │ 5a. 承諾 → Checkout API
  │ 5b. 拒否 → Analytics 記録
  ▼
[Analytics Service]
  └── PostgreSQL (KPI集計・フィードバックループ)
```

## 技術スタック

| レイヤー | 採用技術 | 理由 |
|----------|----------|------|
| API Server | Node.js + Hono | 軽量・型安全・Edgeデプロイ対応 |
| Shopify Extension | React (Checkout UI Ext.) | Shopify公式 |
| LLM | Claude Haiku (Anthropic) | コスト・速度バランス |
| DB | PostgreSQL (Supabase) | 無料枠あり、RLS対応 |
| Cache | Redis (Upstash) | サーバーレス・従量課金 |
| Queue | BullMQ | バックグラウンドジョブ |
| Hosting | Railway | デプロイ簡単・低コスト |
| 監視 | Sentry | エラートラッキング |

## データモデル（主要テーブル）

```sql
-- テナント（インストール済みストア）
CREATE TABLE shops (
  id UUID PRIMARY KEY,
  shopify_domain TEXT UNIQUE NOT NULL,
  access_token TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'starter',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 表示されたオファー
CREATE TABLE offer_impressions (
  id UUID PRIMARY KEY,
  shop_id UUID REFERENCES shops(id),
  order_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  offer_copy JSONB NOT NULL,      -- {headline, subcopy, cta}
  score FLOAT NOT NULL,
  margin_rate FLOAT,
  shown_at TIMESTAMPTZ DEFAULT NOW()
);

-- 承諾/拒否
CREATE TABLE offer_results (
  id UUID PRIMARY KEY,
  impression_id UUID REFERENCES offer_impressions(id),
  accepted BOOLEAN NOT NULL,
  added_revenue FLOAT,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- KPIスナップショット（日次集計）
CREATE TABLE kpi_snapshots (
  id UUID PRIMARY KEY,
  shop_id UUID REFERENCES shops(id),
  date DATE NOT NULL,
  impressions INT,
  acceptances INT,
  added_revenue FLOAT,
  avg_aov_uplift FLOAT,
  margin_adjusted_uplift FLOAT
);
```

## 自動化フロー（全自動化の設計）

```
Webhook受信
  → Offer Engineが自動スコアリング
  → LLM APIがコピー自動生成
  → Redisにキャッシュ
  → Extension が自動表示
  → 結果をDBに自動記録
  → 日次バッチがKPI集計・低acceptオファーを自動抑制
  → ダッシュボードに自動反映
  → Shopify Billing APIで課金も自動
```

人手が不要なのは、すべてイベントドリブン（注文発生 → 全部自動）で回るためです。

## コスト試算（月間）

| 項目 | 費用（概算） |
|------|-------------|
| サーバー (Railway) | ~$10 |
| DB (Supabase) | 無料〜$25 |
| Redis (Upstash) | ~$0〜$10 |
| LLM API (Haiku, 1万回/月) | ~$3〜$10 |
| Sentry | 無料枠 |
| **合計** | **~$20〜$55/月** |

→ $29プランの顧客が2〜3人いれば黒字化。
