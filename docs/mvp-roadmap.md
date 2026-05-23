# MVP ロードマップ：PostLift AI

## Phase 0：環境構築（Day 1〜7）

- [ ] Shopify Partnersアカウント作成
- [ ] 開発用ストア作成
- [ ] Shopify CLI セットアップ
- [ ] Railway / Supabase / Upstash プロジェクト作成
- [ ] GitHub Actions CI設定
- [ ] Anthropic APIキー取得

## Phase 1：コアMVP（Day 8〜30）

### Week 2
- [ ] Shopify OAuth認証フロー実装
- [ ] `orders/paid` Webhook受信・検証
- [ ] Admin APIで商品・在庫・価格取得

### Week 3
- [ ] スコアリングロジック実装（v1：関連性＋在庫のみ）
- [ ] LLMオファーコピー生成（Anthropic Haiku）
- [ ] Redisキャッシュ層実装

### Week 4
- [ ] Shopify Post-Purchase Extension UI実装
- [ ] ワンクリック承諾→Checkout API連携
- [ ] 結果記録（impressions / results テーブル）

## Phase 2：課金＋ダッシュボード（Day 31〜60）

- [ ] Shopify Billing API連携（3プラン）
- [ ] KPIダッシュボード（accept rate / AOV uplift / added revenue）
- [ ] 日次KPIスナップショットバッチ
- [ ] 低accept rateオファーの自動抑制ロジック
- [ ] 初期ベータテスター募集（Shopify Partnersフォーラム、X）

## Phase 3：最適化＋成長（Day 61〜90）

- [ ] 粗利補正スコアリング（v2）
- [ ] 顧客履歴スコアリング
- [ ] A/Bテストフレームワーク
- [ ] App Store申請準備（スクリーンショット、説明文）
- [ ] Shopify App Store公開

## 収益目標

| 月 | 目標MRR | 必要顧客数（$79プラン想定） |
|----|---------|-----------------------------|
| 3ヶ月 | $500 | 7社 |
| 6ヶ月 | $2,000 | 25社 |
| 12ヶ月 | $10,000 | 127社 |

## 獲得チャネル（初期）

1. Shopify App Store（オーガニック）
2. Shopify Partnersフォーラム
3. X（PostLift AIの進捗発信）
4. Reddit r/shopify
5. ProductHunt ローンチ
