# PostLift AI

> Shopify向け AI ポスト購入アップセル最適化アプリ  
> 粗利・在庫・承諾率込みで提案を全自動最適化する SaaS

---

## 🎯 プロダクト概要

| 項目 | 内容 |
|------|------|
| ターゲット | Shopify中堅D2C（月間注文500〜10,000件） |
| 解決する痛み | 購入後の追加収益機会を取り損ねている |
| 提供価値 | 購入完了後にAIが最適なオファーを1クリック提示 |
| 差別化 | 「売上ではなく粗利補正した提案」で既存ツールと差別化 |
| 課金モデル | 月額固定 + 注文数上限（$29 / $79 / $199） |

---

## 📐 市場選定ロジック

### 7軸評価フレーム

| 軸 | 評価基準 | PostLift |
|----|----------|----------|
| 痛みの頻度 | 毎週・毎日発生するか | ✅ 毎注文発生 |
| 金への近さ | 売上・収益に直結するか | ✅ AOV直結 |
| 導入速度 | 小さく試しやすいか | ✅ Shopify App Store経由 |
| 継続性 | 月額課金が自然か | ✅ 効果が続く間は解約しない |
| 競合密度 | 差別化余地があるか | ⚠️ 既存あり、粗利補正で差別化 |
| 実装難易度 | 90日MVPか | ✅ スコープを絞れば可能 |
| 配布導線 | 顧客への到達経路があるか | ✅ App Store + Shopify Partner |

### 候補市場比較

| 候補 | 需要 | 収益性 | 競合 | 実装難易度 | 初速 | 判定 |
|------|------|--------|------|------------|------|------|
| Shopify CVR/AOV改善アプリ | 高 | 高 | 高（細分化可） | 中 | 速 | **採用** |
| 歯科向け患者リコール自動化 | 高 | 高 | 既存専用ソフトあり | 中〜高 | 中 | 後回し |
| 建設見積/現場原価系 | 高 | 高 | 既存ソフト強 | 高 | 遅 | 後回し |
| 汎用SMB AI自動化 | 広い | ばらつく | 大量 | 低〜中 | 速 | 差別化弱 |

---

## 🏗️ アーキテクチャ

```
[Shopify Store]
      |
      | Order webhook (POST /webhooks/order-created)
      ▼
[PostLift API Server]
  ├── Webhook Handler
  ├── Offer Engine (AI)
  │     ├── 商品マージン計算
  │     ├── 在庫チェック
  │     ├── 購入履歴スコアリング
  │     └── LLM (offer copy生成)
  ├── A/B Test Manager
  └── Analytics Aggregator
      |
      ▼
[Shopify Post-Purchase Extension UI]
  └── ワンクリックアップセルカード表示
      |
      ▼
[Shopify Checkout API]
  └── 承諾時に追加注文確定
```

---

## 📊 主要KPI

| KPI | 説明 | 目標 |
|-----|------|------|
| Offer acceptance rate | 提案のうち承諾された割合 | >8% |
| Added revenue per 100 orders | 100注文あたりの追加売上 | 測定・最大化 |
| AOV uplift | 平均注文金額の増加率 | >5% |
| Margin-adjusted uplift | 粗利補正後の増加 | ≥AOV uplift |
| 30日チャーン率 | 30日以内解約率 | <10% |

---

## 💰 課金プラン

| プラン | 月額 | 注文数上限 | 主なターゲット |
|--------|------|------------|----------------|
| Starter | $29 | 500注文/月 | スモールD2C |
| Growth | $79 | 3,000注文/月 | 中堅D2C |
| Scale | $199 | 10,000注文/月 | 成長期D2C |

---

## 🗓️ 30日導入フロー（マーチャント向け）

| Day | アクション |
|-----|------------|
| Day 1 | アプリインストール、Shopify権限認可 |
| Day 2 | 商品マージン・在庫・関連商品ルール設定 |
| Day 3〜30 | AI自動提案 開始 |
| Day 30 | AOV uplift・take rate・accept率レポート |

---

## 📁 ディレクトリ構成（実装予定）

```
postlift-ai/
├── README.md
├── docs/
│   ├── market-analysis.md       # 市場分析詳細
│   ├── product-spec.md          # プロダクト仕様
│   ├── architecture.md          # アーキテクチャ詳細
│   ├── pricing.md               # 課金設計
│   └── mvp-roadmap.md           # MVP ロードマップ
├── src/
│   ├── api/                     # バックエンドAPI
│   │   ├── webhooks/            # Shopify Webhook handlers
│   │   ├── offer-engine/        # AIオファーエンジン
│   │   └── analytics/           # KPI集計
│   ├── extensions/              # Shopify Post-Purchase Extension
│   └── lib/
│       ├── shopify.ts           # Shopify API client
│       └── llm.ts               # LLM API client (OpenAI/Anthropic)
├── tests/
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 🔧 技術スタック（予定）

| レイヤー | 技術 |
|----------|------|
| API Server | Node.js + Hono (or Fastify) |
| Shopify Extension | React (Checkout UI Extension) |
| AI/LLM | OpenAI GPT-4o / Anthropic Claude |
| DB | PostgreSQL (Supabase) |
| キャッシュ | Redis (Upstash) |
| ジョブキュー | BullMQ |
| ホスティング | Railway / Fly.io |
| 監視 | Sentry + Grafana |

---

## 🤖 自動化設計（電気代＋API代のみで回す）

| フロー | 自動化内容 |
|--------|------------|
| オファー生成 | LLM APIが商品データから自動生成 |
| 提案最適化 | 承諾率フィードバックループで自動学習 |
| 失敗オファー抑制 | 成果の低い提案は自動で頻度を下げる |
| KPIレポート | Webhookで収集→自動集計→ダッシュボード反映 |
| 課金管理 | Shopify Billing API で全自動 |

---

## 📄 ドキュメント

- [市場分析](./docs/market-analysis.md)
- [プロダクト仕様](./docs/product-spec.md)
- [アーキテクチャ詳細](./docs/architecture.md)
- [MVPロードマップ](./docs/mvp-roadmap.md)

---

## ライセンス

MIT
