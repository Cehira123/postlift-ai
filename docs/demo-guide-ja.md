# PostLift AI デモ手順書

このドキュメントは、PostLift AIが実際に動くことを購入者・検討者に見せるためのデモ手順です。

PostLift AIは自己ホスト型のコード商品です。このデモは、Shopify App Store公開や本番ストアでの売上保証を示すものではありません。API、テスト、商品同期、オファー生成、メトリクス更新の技術的な動作を確認するためのものです。

## デモで見せるゴール

デモでは、以下を確認します。

1. ローカルでテストが通る
2. APIサーバーが起動する
3. `/health` が応答する
4. `/docs` と `/openapi.json` が表示できる
5. 公開URLのスモークテストが通る
6. Shopify開発ストアの商品同期ができる
7. テスト注文または署名付きWebhookでオファーを作成できる
8. `/offers/current` でオファーを取得できる
9. オファー承諾/拒否を記録できる
10. メトリクスに反映される

## まず実行済み確認の状態

このリポジトリでは、以下を確認済みです。

```text
pytest: 13 passed
deployment_smoke.py: /health and metrics endpoints returned 200
local uvicorn startup: OK
local /health: 200
local /docs: 200
local /openapi.json: 200
```

ローカルでDB未設定の場合、`/health` は次のように `degraded` になります。

```json
{"status":"degraded","version":"0.4.0","db":"error: DATABASE_URL is not configured"}
```

これは正常な挙動です。DB接続なしでもAPI自体が起動していることを確認できます。DBを設定した公開環境では、次のように `ok` になります。

```json
{"status":"ok","version":"0.4.0","db":"ok"}
```

## デモA: ローカルテストを見せる

### 1. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### 2. テストを実行

```bash
pytest
```

成功例:

```text
13 passed
```

ここで確認できること:

- オファーエンジンが動く
- Shopify Admin APIの商品マッピングが壊れていない
- Shopify WebhookのHMAC署名検証が動く
- Privacy/GDPR系WebhookのHMAC署名検証が動く
- 購入後オファー作成から承諾記録までのE2Eが動く

## デモB: ローカルAPI起動を見せる

### 1. APIを起動

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 5010
```

Pythonから起動する場合:

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 5010
```

成功すると、以下のような表示になります。

```text
Uvicorn running on http://127.0.0.1:5010
```

### 2. ヘルスチェック

別のターミナルで実行します。

```bash
curl http://127.0.0.1:5010/health
```

DB未設定のローカルでは、次のような結果でもOKです。

```json
{"status":"degraded","version":"0.4.0","db":"error: DATABASE_URL is not configured"}
```

APIが起動していて、DBだけ未設定という意味です。

### 3. APIドキュメントを開く

ブラウザで開きます。

```text
http://127.0.0.1:5010/docs
```

または:

```bash
curl -I http://127.0.0.1:5010/docs
```

成功例:

```text
HTTP/1.1 200 OK
```

### 4. OpenAPI JSONを確認

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5010/openapi.json
```

成功例:

```text
200
```

## デモC: 公開URLのスモークテスト

デプロイ済みのAPIに対して、基本エンドポイントが応答するか確認します。

```bash
python scripts/deployment_smoke.py https://your-api.example.com
```

成功例:

```text
ok   200 https://your-api.example.com/health
ok   200 https://your-api.example.com/metrics/summary?shop_domain=smoke-test.myshopify.com
ok   200 https://your-api.example.com/metrics/trend?shop_domain=smoke-test.myshopify.com
ok   200 https://your-api.example.com/metrics/products?shop_domain=smoke-test.myshopify.com
```

ここで確認できること:

- 公開URLからAPIにアクセスできる
- `/health` が応答する
- メトリクス系エンドポイントが落ちていない
- DB接続済み環境なら `db: ok` になる

## デモD: Shopify開発ストア連携

このデモは、購入者または販売者のShopify開発ストアで行います。

### 1. Shopifyアプリ設定を確認

Shopify Partnerで以下を設定します。

| 項目 | 値 |
| --- | --- |
| アプリURL | `https://your-api.example.com` |
| リダイレクトURL | `https://your-api.example.com/auth/callback` |
| Webhooks APIバージョン | `.env` の `SHOPIFY_API_VERSION` と同じ |

推奨スコープ:

```text
read_products,read_inventory,read_orders,write_draft_orders
```

顧客スコア機能まで見せる場合のみ:

```text
read_customers
```

### 2. 開発ストアにアプリをインストール

Shopify Partner画面から、開発ストアへアプリをインストールします。

成功確認:

- Shopify管理画面のアプリ一覧に表示される
- アプリ画面が開く
- API側のログにOAuth関連のアクセスが出る

### 3. 商品同期を実行

商品同期APIを実行します。

```text
POST /products/sync?shop_domain=your-store.myshopify.com
```

成功例:

```json
{"status":"ok","synced":26,"total_fetched":17}
```

数字はストアの商品数によって変わります。

確認すること:

- `synced` が0より大きい
- 商品タイトルがDBまたはAPIから確認できる
- variant IDが保存されている
- inventory item IDが保存されている

## デモE: オファー作成

オファーを作るには、候補商品が必要です。

確認する条件:

- 商品同期が完了している
- 候補商品の在庫がある
- 粗利率がしきい値以上
- 注文に含まれていない別商品がある

必要に応じて、デモ用に1商品の粗利率を高めに設定します。

例:

```text
PUT /products/{variant_id}/margin?shop_domain=your-store.myshopify.com
```

デモ用の粗利率例:

```json
{"gross_margin":60}
```

## デモF: 署名付きWebhookでテスト注文相当を送る

実際のShopify本番注文を使わず、署名付きWebhookで `orders/paid` 相当のテストを行えます。

送信先:

```text
POST /webhooks/orders/paid
```

必要なヘッダー:

```text
X-Shopify-Hmac-Sha256: 署名
X-Shopify-Shop-Domain: your-store.myshopify.com
Content-Type: application/json
```

送信するJSON例:

```json
{
  "id": "demo-order-100",
  "line_items": [
    {
      "product_id": "already-bought",
      "title": "Demo purchased item"
    }
  ]
}
```

成功例:

```json
{"status":"queued","offer_id":"生成されたoffer_id"}
```

ここで `offer_id` が返れば、オファー作成は成功です。

## デモG: 現在のオファーを取得する

```text
GET /offers/current?order_id=demo-order-100&shop_domain=your-store.myshopify.com
```

成功例:

```json
{
  "variant_id": "1234567890",
  "title": "Demo upsell product",
  "price": 29.99,
  "copy_text": "Add this to your order today."
}
```

確認すること:

- `variant_id` が返る
- `title` が返る
- `price` が返る
- `copy_text` が返る

## デモH: 承諾/拒否を記録する

承諾した例:

```text
POST /webhooks/upsell/respond
```

```json
{
  "offer_id": "生成されたoffer_id",
  "accepted": true
}
```

成功例:

```json
{"offer_id":"生成されたoffer_id","accepted":true,"status":"recorded"}
```

拒否を見せたい場合は、`accepted` を `false` にします。

## デモI: メトリクスを確認する

```text
GET /metrics/summary?shop_domain=your-store.myshopify.com
```

成功例:

```json
{
  "total_offers": 1,
  "accepted_offers": 1,
  "accept_rate_pct": 100.0,
  "extra_revenue": 29.99
}
```

確認すること:

- `total_offers` が増える
- 承諾した場合 `accepted_offers` が増える
- `accept_rate_pct` が変わる
- `extra_revenue` が更新される

## デモで使う説明文

見込み客には、次のように説明すると誤解が少ないです。

> このデモでは、Shopify商品同期、署名付きWebhookによるオファー作成、現在のオファー取得、承諾記録、メトリクス更新までを確認しています。これは自己ホスト型コード商品の動作デモであり、Shopify App Store審査や本番顧客データ利用の承認を保証するものではありません。

## デモで見せない方がいいもの

画面共有やスクリーンショットでは、以下を隠してください。

- `SHOPIFY_API_SECRET`
- `SHOPIFY_WEBHOOK_SECRET`
- Shopify access token
- `DATABASE_URL`
- `OPENAI_API_KEY`
- 顧客情報
- 注文者情報
- 実在顧客のメールアドレス

## デモ前チェックリスト

- [ ] `pytest` が通っている
- [ ] 公開URLの `/health` が確認できる
- [ ] 商品同期済み
- [ ] 候補商品の粗利率と在庫がある
- [ ] 署名付きWebhookを送れる
- [ ] `/offers/current` が返る
- [ ] `/webhooks/upsell/respond` が成功する
- [ ] `/metrics/summary` が更新される
- [ ] 秘密情報が画面に出ていない

## デモ後に伝えること

最後に、必ず次を伝えてください。

- 購入者は自分のShopifyアプリを作る必要がある
- 購入者は自分のDBとサーバーを用意する必要がある
- 本番利用時はShopify承認やプライバシー対応が必要になる場合がある
- この商品は自己ホスト型のコードベースであり、運営代行SaaSではない
