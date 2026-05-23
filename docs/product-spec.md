# プロダクト仕様：PostLift AI

## 1. コア機能定義

### MVP スコープ（90日）

| 機能 | 説明 | 優先度 |
|------|------|--------|
| ポスト購入UI | Shopify注文完了後ページにオファーカード表示 | P0 |
| AIオファー生成 | 購入商品・粗利率・在庫・購入履歴でオファー選定 | P0 |
| オファーコピー生成 | LLMで自動生成（商品名・割引・緊急性） | P0 |
| ワンクリック承諾 | 再入力なしで追加注文確定 | P0 |
| 基本ダッシュボード | accept rate / AOV uplift / added revenue 表示 | P0 |
| 課金管理 | Shopify Billing API連携 | P0 |
| 失敗オファー自動抑制 | 低accept rateのオファーを頻度自動削減 | P1 |
| A/Bテスト | オファーパターン間の比較 | P1 |
| 粗利補正最適化 | 粗利率込みのスコアリング | P1 |

### P0外（後回し）

- 多言語対応
- 複数オファー同時表示
- 外部レビューツール連携

---

## 2. オファーエンジン仕様

### 入力パラメータ

```typescript
interface OfferInput {
  orderId: string;
  purchasedProductIds: string[];
  totalPrice: number;
  customerId?: string;          // 既存顧客ならhistoryを参照
  shopDomain: string;
}
```

### スコアリングロジック

```
Offer Score = 
  関連スコア (商品相性)          × 0.30
  + マージンスコア (粗利率)      × 0.25
  + 在庫スコア (在庫日数)        × 0.15
  + 過去acceptスコア (類似顧客)  × 0.20
  + 緊急性スコア (在庫残り)      × 0.10
```

### LLMへのプロンプト構造

```
System: ECストアのポスト購入オファーコピーライター
Context: 購入商品={商品名}、提案商品={商品名}、割引={X%}、在庫残={N個}
Task: 25文字以内の見出し + 40文字以内のサブコピー + CTAボタン文言
Constraint: 緊急性は自然に、押しつけがましくなく
```

---

## 3. Shopify Extension 仕様

### 使用するShopify API

| API | 用途 |
|-----|------|
| Post-Purchase Extension | 注文確認後UIの差し込み |
| Checkout API | 追加注文の確定 |
| Admin API (GraphQL) | 商品・在庫・粗利情報の取得 |
| Webhooks (orders/paid) | 注文確定トリガー |
| Billing API | サブスクリプション課金 |

### UI仕様

```
┌─────────────────────────────┐
│ 🎉 ご購入ありがとうございます │
│                             │
│ ┌─────────────────────────┐ │
│ │ [商品画像]              │ │
│ │ {商品名} - {割引}OFF    │ │
│ │ {サブコピー}            │ │
│ │                         │ │
│ │ [今すぐ追加する] [不要]  │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

---

## 4. ダッシュボードKPI定義

| KPI | 計算式 | 目標値（目安） |
|-----|--------|----------------|
| Offer acceptance rate | 承諾数 / 表示数 | > 8% |
| Added revenue / 100 orders | Σ承諾金額 / (総注文数/100) | 最大化 |
| AOV uplift | (全注文平均 - 非提示平均) / 非提示平均 | > 5% |
| Margin-adjusted uplift | AOV uplift × 平均粗利率補正 | ≥ AOV uplift |
| 30日チャーン率 | 30日内解約数 / インストール数 | < 10% |
