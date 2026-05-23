# PostLift AI 🚀

> AI-powered post-purchase upsell optimization for Shopify — margin-aware, inventory-aware, self-learning.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built for Shopify](https://img.shields.io/badge/Platform-Shopify-96bf48)](https://shopify.dev)

---

## 概要

PostLift AI は、Shopify の注文完了ページに **AI が選んだポスト購入ワンクリックアップセル** を表示するアプリです。

- 粗利率・在庫・過去の承諾率を加味して提案を最適化
- オファー文面も LLM が自動生成
- 失敗したオファーは自動で頻度を下げる
- 導入コスト: $0（電気代 + API 費用のみ）

---

## ビジネスモデル

| Tier | 価格 | 対象 |
|------|------|------|
| Starter | $29/月 | 〜500注文/月 |
| Growth | $79/月 | 〜2,000注文/月 |
| Scale | $199/月 | 無制限 |

---

## KPI

- **Offer acceptance rate** — 提案承諾率
- **Added revenue per 100 orders** — 100注文あたり追加売上
- **AOV uplift** — 平均注文単価の向上率
- **Margin-adjusted uplift** — 粗利補正後の改善率（差別化ポイント）

---

## アーキテクチャ

```
Shopify Order → Webhook → PostLift API
                               │
                    ┌──────────▼──────────┐
                    │  AI Offer Engine     │
                    │  (LLM + Rules)       │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │ Offer Selection Logic            │
              │ - 粗利率フィルタ                  │
              │ - 在庫チェック                    │
              │ - 承諾率履歴                      │
              │ - 商品相性スコア                  │
              └────────────────┬────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Post-Purchase UI   │
                    │  (Shopify Extension) │
                    └─────────────────────┘
```

---

## ディレクトリ構成

```
postlift-ai/
├── README.md
├── docs/
│   ├── market-analysis.md       # 市場分析・競合比較
│   ├── product-spec.md          # 製品要件定義
│   ├── architecture.md          # システム設計
│   ├── business-model.md        # 収益モデル
│   └── 30day-onboarding.md     # 30日導入フレーム
├── src/
│   ├── api/                     # Backend API
│   ├── ai/                      # AI Offer Engine
│   ├── shopify/                 # Shopify Extension
│   └── db/                      # DB スキーマ
├── infra/
│   ├── n8n/                     # ワークフロー定義
│   └── docker-compose.yml
└── .github/
    └── workflows/
        └── ci.yml
```

---

## クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/Cehira123/postlift-ai.git
cd postlift-ai

# 2. 環境変数を設定
cp .env.example .env
# .env に SHOPIFY_API_KEY, OPENAI_API_KEY 等を入力

# 3. 起動
docker-compose up -d
```

---

## ライセンス

MIT License — © 2026 Cehira123
