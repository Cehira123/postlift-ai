# 製品要件定義書 — PostLift AI

## プロダクトビジョン

> 「Shopify ストアオーナーが、粗利を削らずに AOV を上げられる AI アシスタント」

---

## MVP スコープ（30日で作るもの）

### In Scope

- 注文完了後ページにワンクリックアップセル UI を表示
- AI が提案候補を選定・優先順位付け
- オファー文面を LLM で自動生成
- 提案条件：購入商品、粗利率、在庫、過去承諾率
- 失敗オファーの自動頻度低減
- ダッシュボード（AOV uplift / acceptance rate / added revenue）

### Out of Scope（MVP 後）

- A/B テスト機能
- メール・SMS フォローアップ
- マルチ言語対応
- Shopify Plus カスタマイズ

---

## ユーザーストーリー

```
As a Shopify ストアオーナー,
I want 購入完了直後に AI が関連商品を提案してほしい
So that 粗利を維持しながら AOV を上げられる
```

```
As a ストアオーナー,
I want ダッシュボードで AOV uplift を確認したい
So that 導入効果を数値で確認できる
```

---

## 画面定義

### 1. インストール後セットアップ画面
- 商品粗利率の入力 or Shopify Cost フィールド自動取得
- 在庫閾値の設定（在庫N個以下は提案から除外）
- オファー除外商品リスト

### 2. ポスト購入 UI（Shopify Extension）
- 提案商品画像 + 名称 + 価格
- ワンクリック追加ボタン
- AI 生成のオファーコピー（20〜40文字）
- タイマー（任意、緊迫感演出）

### 3. ダッシュボード
- 当月 AOV uplift（%）
- Offer acceptance rate（%）
- Added revenue per 100 orders（円/USD）
- Margin-adjusted uplift（差別化 KPI）
- 提案ランキング（承諾率順）

---

## 主要 KPI

| KPI | 定義 | 目標（30日） |
|---|---|---|
| Offer acceptance rate | 提案承諾数 / 提案表示数 | 8〜15% |
| AOV uplift | (after AOV - before AOV) / before AOV | +5〜15% |
| Margin-adjusted uplift | 粗利補正後の AOV uplift | before AOV uplift と差を見る |
| MRR | 課金ユーザー × 月額 | 3ヶ月で $1,000 |

---

## 差別化ポイント

```
既存競合: 売上最大化（粗利無視）
PostLift AI: 粗利補正後の利益最大化
```

粗利率の低い商品をアップセルしても、ストアオーナーの手残りは変わらないか悪化する。
PostLift AI は粗利を加味した「本当に意味のある AOV 向上」を提供する。
