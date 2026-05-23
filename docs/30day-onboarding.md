# 30日導入フレーム — PostLift AI

## ユーザー向け導入スケジュール

```
Day 1    : インストール + 初期設定（粗利率、在庫閾値）
Day 2    : 最初のオファーが自動表示開始
Day 3〜7  : AI が提案パターンを学習
Day 7    : 週次レポート通知（acceptance rate / added revenue）
Day 8〜30 : 自動最適化ループが継続動作
Day 30   : 月次サマリー → 有料プランへの転換判断
```

---

## 開発者向け MVP 30日ロードマップ

### Week 1: 基盤構築
- [ ] Shopify Partner アカウント作成
- [ ] FastAPI プロジェクト初期化
- [ ] PostgreSQL スキーマ作成
- [ ] Shopify Webhook 受信テスト

### Week 2: AI Offer Engine
- [ ] 粗利フィルタロジック実装
- [ ] 在庫チェック実装
- [ ] LLM プロンプト設計・テスト
- [ ] 承諾率スコアリング実装

### Week 3: Shopify Extension
- [ ] post-purchase UI コンポーネント作成
- [ ] ワンクリック購入 API 連携
- [ ] テストストアで動作確認

### Week 4: ダッシュボード + 公開準備
- [ ] ダッシュボード画面実装
- [ ] n8n 自動同期ワークフロー構築
- [ ] App Store 審査申請
- [ ] ベータユーザー募集開始

---

## 自動化ループ（毎日回るもの）

```
[CRON: 毎日0時]
  ↓
在庫・価格同期 (n8n → Shopify API → PostgreSQL)
  ↓
承諾率スコア再計算 (PostgreSQL → 集計クエリ)
  ↓
日次サマリー通知 (n8n → LINE/Slack)
  ↓
[次の注文を待機]
  ↓
注文発生 → Webhook → AI Offer Engine → UI 表示
  ↓
承諾/拒否ログ → PostgreSQL → 翌日スコアに反映
```

このループが動き続ける限り、**あなたの作業は「ダッシュボードを月1回見る」だけ**になります。
