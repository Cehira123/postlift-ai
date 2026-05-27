# PostLift AI 購入者向けセットアップ手順

このドキュメントは、PostLift AIを購入した人が、自分のShopifyアプリ、自分のサーバー、自分のPostgreSQLで動かすための手順です。

PostLift AIは自己ホスト型のコード商品です。販売者が運営するSaaSではありません。Shopifyアカウント、サーバー、DB、APIキー、法務・プライバシー対応、本番運用は購入者側で管理してください。

## まず全体像

セットアップの流れは次の順番です。

1. 必要なアカウントを用意する
2. ソースコードを受け取る
3. ローカルでテストを動かす
4. PostgreSQLを用意する
5. APIを公開URLにデプロイする
6. データベースの初期化を行う
7. Shopify Partnerでアプリを作る
8. ShopifyアプリのURLとスコープを設定する
9. サーバーに環境変数を設定する
10. Shopify開発ストアにアプリをインストールする
11. 商品同期とテストWebhookで動作確認する
12. 本番利用するかどうかを判断する

いきなり本番ストアに入れず、必ず開発ストアまたは検証用ストアで確認してください。

## 1. 必要なもの

最低限、以下が必要です。

| 必要なもの | 用途 |
| --- | --- |
| GitHubアカウント、またはZIPで受け取ったソースコード | コードの管理 |
| Python 3.11以上 | ローカル実行・テスト |
| PostgreSQL | データ保存 |
| Shopify Partnerアカウント | Shopifyアプリ作成 |
| Shopify開発ストア | インストール・動作確認 |
| Railway、Render、VPSなど | APIを公開するサーバー |
| OpenAI APIキー | 任意。AIコピー生成を使う場合のみ |

## 2. 購入後に最初に読むファイル

購入後は、まず以下を順番に確認してください。

1. `README.md`
2. `docs/buyer-responsibilities.md`
3. `docs/setup-guide-ja.md`
4. `docs/self-hosting.md`
5. `.env.example`

特に `docs/buyer-responsibilities.md` には、購入者側で管理する必要がある内容が書かれています。

## 3. ローカル環境でテストする

まず、ソースコードが壊れていないことをローカルで確認します。

```bash
python -m venv .venv
```

仮想環境を有効化します。

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

依存関係をインストールします。

```bash
pip install -r requirements.txt
```

テストを実行します。

```bash
pytest
```

成功例:

```text
passed
```

この時点ではPostgreSQLやShopify接続が未設定でも、ローカルE2Eテストは動くように作られています。

## 4. `.env` を作る

`.env.example` をコピーして `.env` を作ります。

```bash
cp .env.example .env
```

Windows PowerShellの場合:

```powershell
Copy-Item .env.example .env
```

`.env` には本物の秘密情報を入れます。`.env` はGitHubにコミットしないでください。

## 5. 環境変数の意味

主な環境変数は以下です。

| 変数名 | 必須 | 説明 |
| --- | --- | --- |
| `SHOPIFY_API_KEY` | 必須 | Shopify Partnerで作成したアプリのクライアントID |
| `SHOPIFY_API_SECRET` | 必須 | Shopifyアプリのクライアントシークレット |
| `SHOPIFY_WEBHOOK_SECRET` | 必須 | Shopify Webhookの署名検証に使うシークレット |
| `SHOPIFY_API_VERSION` | 推奨 | Shopify APIバージョン。例: `2026-04` |
| `SHOPIFY_BILLING_TEST` | 推奨 | 開発ストアでは `true` |
| `APP_URL` | 必須 | デプロイ後の公開URL |
| `CORS_ORIGINS` | 推奨 | 許可するURL。通常は `APP_URL` とローカルURL |
| `RUN_SCHEDULER` | 推奨 | 単体サービスなら `true` |
| `DATABASE_URL` | 必須 | PostgreSQL接続URL |
| `OPENAI_API_KEY` | 任意 | AIコピー生成を使う場合のみ |
| `OPENAI_MODEL` | 任意 | 例: `gpt-4o-mini` |

例:

```env
SHOPIFY_API_KEY=自分のShopifyクライアントID
SHOPIFY_API_SECRET=自分のShopifyクライアントシークレット
SHOPIFY_WEBHOOK_SECRET=自分のWebhookシークレット
SHOPIFY_API_VERSION=2026-04
SHOPIFY_BILLING_TEST=true

APP_URL=https://your-api.example.com
CORS_ORIGINS=https://your-api.example.com,http://localhost:5000
RUN_SCHEDULER=true

DATABASE_URL=postgresql://user:password@host:5432/database
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

## 6. PostgreSQLを用意する

PostLift AIはPostgreSQLを使います。

Railwayを使う場合は、プロジェクト内でPostgreSQLサービスを追加してください。RenderやSupabaseなどを使う場合も、PostgreSQLの接続URLを取得してください。

必要なのは `DATABASE_URL` です。

注意:

- DB接続URLは秘密情報です。
- スクリーンショットや公開ページに載せないでください。
- 販売者に送る必要もありません。

## 7. APIをデプロイする

Railway、Render、Docker対応サーバーなどにAPIをデプロイします。

デプロイ先には、先ほどの環境変数をすべて設定します。

最低限必要:

```text
APP_URL
DATABASE_URL
SHOPIFY_API_KEY
SHOPIFY_API_SECRET
SHOPIFY_WEBHOOK_SECRET
SHOPIFY_API_VERSION
SHOPIFY_BILLING_TEST
CORS_ORIGINS
RUN_SCHEDULER
```

デプロイ後、以下をブラウザで開きます。

```text
https://your-api.example.com/health
```

成功例:

```json
{"status":"ok","version":"0.4.0","db":"ok"}
```

もし `db` が `error` または `status` が `degraded` の場合は、`DATABASE_URL` が正しく設定されていない可能性が高いです。

## 8. データベースを初期化する

デプロイ後、PostgreSQLにテーブルを作成します。

ローカルまたはデプロイ環境で、`DATABASE_URL` が設定された状態で実行します。

```bash
python scripts/apply_sql.py src/db/schema.sql
python scripts/apply_sql.py src/db/migrations/001_variant_inventory_ids.sql
```

成功すると、必要なテーブルと追加カラムが作成されます。

この作業は基本的に最初の1回だけです。すでに適用済みの場合、同じSQLを再実行するとエラーになる可能性があります。

## 9. Shopify Partnerでアプリを作る

Shopify Partner管理画面を開き、自分のアプリを作成します。

設定する主な内容:

| Shopify側の項目 | 入れる値 |
| --- | --- |
| アプリURL | `https://your-api.example.com` |
| リダイレクトURL | `https://your-api.example.com/auth/callback` |
| Webhooks APIバージョン | `.env` の `SHOPIFY_API_VERSION` と同じ |

アプリ作成後、以下を取得します。

- クライアントID
- クライアントシークレット
- Webhookシークレット

それぞれ、サーバー側の環境変数に入れます。

## 10. Shopifyスコープを設定する

検証用の基本スコープ:

```text
read_products,read_inventory,read_orders,write_draft_orders
```

顧客スコア機能まで使う場合:

```text
read_customers
```

ただし、顧客情報や注文履歴を本番で扱う場合、Shopifyの追加承認が必要になることがあります。

最初は、検証に必要な最小スコープから始めることをおすすめします。

## 11. Shopify開発ストアにインストールする

Shopify Partner画面から、開発ストアにアプリをインストールします。

成功すると、Shopify管理画面のアプリ一覧にPostLift AIが表示されます。

もしインストール中にエラーが出る場合は、以下を確認してください。

- `APP_URL` が正しい
- リダイレクトURLが `/auth/callback` になっている
- `SHOPIFY_API_KEY` が正しい
- `SHOPIFY_API_SECRET` が正しい
- デプロイ先のAPIが起動している
- `/health` が `ok` になっている

## 12. 商品同期を確認する

アプリをインストールしたら、商品同期APIを実行します。

例:

```text
POST /products/sync?shop_domain=your-store.myshopify.com
```

成功すると、Shopifyの商品・バリアント情報がPostgreSQLに保存されます。

確認ポイント:

- 商品数が0ではない
- variant IDが保存されている
- inventory item IDが保存されている
- 価格が保存されている

## 13. オファー生成をテストする

アップセル候補を出すには、商品に粗利率や在庫が必要です。

候補が出ない場合は、以下を確認してください。

- 商品同期が完了している
- 商品の在庫が0ではない
- 粗利率がしきい値以上になっている
- 注文済み商品と別の商品が候補にある

テストでは、署名付きWebhookを使って `orders/paid` 相当のイベントを送ることで、オファー作成を確認できます。

## 14. オファー取得を確認する

オファーが作成されたら、以下のようなエンドポイントで取得できます。

```text
GET /offers/current?order_id=ORDER_ID&shop_domain=your-store.myshopify.com
```

成功すると、アップセル対象のvariant ID、価格、コピー文などが返ります。

## 15. 承諾・拒否の記録を確認する

購入者がオファーを承諾または拒否した場合、以下のAPIで記録します。

```text
POST /webhooks/upsell/respond
```

送信例:

```json
{
  "offer_id": "作成されたoffer_id",
  "accepted": true
}
```

成功すると、メトリクスやA/Bテスト結果に反映されます。

## 16. スモークテストを実行する

公開URLが基本的に動いているか確認します。

```bash
python scripts/deployment_smoke.py https://your-api.example.com
```

成功例:

```text
ok 200 https://your-api.example.com/health
ok 200 https://your-api.example.com/metrics/summary?shop_domain=smoke-test.myshopify.com
ok 200 https://your-api.example.com/metrics/trend?shop_domain=smoke-test.myshopify.com
ok 200 https://your-api.example.com/metrics/products?shop_domain=smoke-test.myshopify.com
```

これはAPIが公開URLから応答していることを確認するテストです。Shopifyの本番承認や顧客データアクセスを保証するものではありません。

## 17. よくあるトラブル

### `/health` が `degraded` になる

原因候補:

- `DATABASE_URL` が未設定
- DB接続URLが間違っている
- DBサービスが起動していない
- デプロイ先からDBへ接続できない

まず `DATABASE_URL` を確認してください。

### Shopifyインストール後にリダイレクトエラーになる

原因候補:

- Shopify側のリダイレクトURLが間違っている
- `APP_URL` が古いURLのまま
- `SHOPIFY_API_KEY` または `SHOPIFY_API_SECRET` が違う
- デプロイ先が落ちている

Shopify側:

```text
https://your-api.example.com/auth/callback
```

サーバー側:

```text
APP_URL=https://your-api.example.com
```

この2つが一致しているか確認してください。

### Webhookが401になる

原因候補:

- `SHOPIFY_WEBHOOK_SECRET` が違う
- 署名なしでWebhookを送っている
- Shopify側のWebhookシークレットとサーバー側の値が一致していない

WebhookはHMAC署名検証を行います。手動テストする場合も署名付きで送る必要があります。

### オファーが作られない

原因候補:

- 商品同期ができていない
- 候補商品の在庫が0
- 粗利率が低い
- 注文に含まれる商品しかDBにない
- `shop_domain` が間違っている

まず商品一覧と粗利率を確認してください。

### OpenAI APIキーがなくても動くか

動きます。

`OPENAI_API_KEY` が未設定の場合、AI生成コピーではなくフォールバック文言が使われます。

## 18. 本番利用前のチェックリスト

本番利用する前に、最低限以下を確認してください。

- [ ] `pytest` が成功している
- [ ] `/health` が `ok` になっている
- [ ] DBのバックアップ方針がある
- [ ] ShopifyアプリのURLが本番URLになっている
- [ ] 秘密情報がGitHubに入っていない
- [ ] ログにアクセストークンやDB URLが出ていない
- [ ] 必要なShopify承認を取得している
- [ ] プライバシーポリシーや利用規約を用意している
- [ ] 顧客データや注文データを扱う責任範囲を理解している
- [ ] 障害時に誰が対応するか決まっている

## 19. 販売者へ共有してはいけないもの

以下は秘密情報です。サポートを受ける場合でも、そのまま送らないでください。

- `SHOPIFY_API_SECRET`
- `SHOPIFY_WEBHOOK_SECRET`
- Shopify access token
- `DATABASE_URL`
- `OPENAI_API_KEY`
- 顧客情報
- 注文情報

エラー相談をする場合は、秘密情報を伏せたログやスクリーンショットを使ってください。

## 20. 最後に

PostLift AIは、Shopify向けポスト購入アップセル機能を作るためのコードベースです。

購入者はこのコードを土台として、自分のShopifyアプリ、自分のサーバー、自分のDBで動かします。

公開SaaSとして運営する場合は、Shopify審査、顧客データ管理、法務、サポート、監視、課金などの実務が追加で必要です。まずは開発ストアで検証し、必要な範囲を理解してから本番利用に進んでください。
