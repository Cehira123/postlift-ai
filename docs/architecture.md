# システムアーキテクチャ — PostLift AI

## 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                     Shopify Store                        │
│  Order Completed → post-purchase extension UI           │
└────────────────────────┬────────────────────────────────┘
                         │ Webhook (order/created)
┌────────────────────────▼────────────────────────────────┐
│                   PostLift API (FastAPI)                  │
│  /api/offer  →  Offer Engine  →  Response JSON           │
└───────────┬──────────────────────────────┬──────────────┘
            │                              │
┌───────────▼──────────┐     ┌─────────────▼─────────────┐
│   AI Offer Engine    │     │     Database (PostgreSQL)   │
│  - LLM (OpenAI API)  │     │  - orders                  │
│  - Margin filter     │     │  - products (margin, stock) │
│  - Stock check       │     │  - offers (accept/reject)  │
│  - Acceptance score  │     │  - merchants               │
└──────────────────────┘     └────────────────────────────┘
```

---

## 技術スタック

| レイヤー | 技術 | 理由 |
|---|---|---|
| Shopify Extension | Shopify UI Extensions (React) | 公式サポート・審査通過率 |
| Backend API | Python + FastAPI | LLM 連携が容易、非同期対応 |
| AI | OpenAI GPT-4o-mini | コスト効率、JSON mode |
| DB | PostgreSQL | リレーショナルデータ管理 |
| Workflow | n8n | ノーコードで自動化ループ構築 |
| Infra | Docker + VPS (Hetzner) | 低コスト、電気代含めて月3,000円以下 |

---

## AI Offer Engine 詳細

### 入力
```json
{
  "order": {
    "items": [{"product_id": "xxx", "variant_id": "yyy", "price": 3000}],
    "total_price": 3000,
    "customer_id": "zzz"
  },
  "merchant": {
    "shop_id": "aaa",
    "margin_threshold": 0.30
  }
}
```

### 処理フロー
```
1. 購入商品から関連商品候補を取得（Shopify Admin API）
2. 粗利率 < margin_threshold の商品を除外
3. 在庫 <= 在庫閾値の商品を除外
4. 過去30日の承諾率スコアで並べ替え
5. Top 1商品を選択
6. LLM にオファーコピーを生成させる
7. JSON レスポンスで返す
```

### LLM プロンプト（コピー生成）
```
You are a conversion copywriter for an e-commerce store.
Generate a one-click upsell offer message in Japanese.
Product: {product_name}
Buyer just purchased: {purchased_items}
Requirements:
- Max 35 characters
- Include why this pairs well
- No hard sell language
- Output: JSON {"copy": "...", "cta": "..."}
```

---

## DB スキーマ（主要テーブル）

```sql
-- 商品マスタ（粗利・在庫管理）
CREATE TABLE products (
  id            VARCHAR PRIMARY KEY,
  shop_id       VARCHAR NOT NULL,
  title         VARCHAR,
  margin_rate   DECIMAL(5,4),  -- 0.0000〜1.0000
  stock_qty     INT,
  updated_at    TIMESTAMP
);

-- オファー結果ログ
CREATE TABLE offer_events (
  id            SERIAL PRIMARY KEY,
  shop_id       VARCHAR NOT NULL,
  order_id      VARCHAR,
  offered_product_id VARCHAR,
  accepted      BOOLEAN,
  added_revenue DECIMAL(10,2),
  created_at    TIMESTAMP DEFAULT NOW()
);

-- マーチャント設定
CREATE TABLE merchants (
  shop_id          VARCHAR PRIMARY KEY,
  margin_threshold DECIMAL(5,4) DEFAULT 0.30,
  stock_threshold  INT DEFAULT 5,
  plan             VARCHAR DEFAULT 'starter',
  created_at       TIMESTAMP DEFAULT NOW()
);
```

---

## n8n ワークフロー（全自動ループ）

```
[毎日0時 CRON]
    │
    ▼
[Shopify Admin API] → 在庫・価格を同期
    │
    ▼
[PostgreSQL] → products テーブルを更新
    │
    ▼
[集計クエリ] → 過去7日の承諾率を計算
    │
    ▼
[PostgreSQL] → offer_score テーブルを更新
    │
    ▼
[Slack/LINE Notify] → 日次サマリーを通知（任意）
```

---

## コスト見積もり

| 項目 | 月額 |
|---|---|
| VPS (Hetzner CX22) | ¥600〜900 |
| 電気代（自宅 PC 補助） | ¥0〜500 |
| OpenAI API | 1リクエスト≒$0.001、100注文/日 × 30日 = $3〜10 |
| PostgreSQL (同VPS) | 込み |
| n8n (セルフホスト) | 込み |
| **合計** | **月1,500〜3,000円程度** |

収益分岐点：Starter プラン ($29) × 2ユーザー = $58/月 → コスト回収完了
