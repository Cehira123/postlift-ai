# デプロイガイド

## 必要な環境変数

| 変数名 | 説明 | 必須 |
|---|---|---|
| `SHOPIFY_API_KEY` | Shopify Partners アプリの API キー | ✅ |
| `SHOPIFY_API_SECRET` | Shopify Partners アプリの API シークレット | ✅ |
| `SHOPIFY_WEBHOOK_SECRET` | Webhook HMAC 検証用シークレット | ✅ |
| `SHOPIFY_BILLING_TEST` | `true` でテスト課金 / `false` で本番 | ✅ |
| `APP_URL` | デプロイ先のアプリ URL | ✅ |
| `OPENAI_API_KEY` | OpenAI API キー | ✅ |
| `DATABASE_URL` | PostgreSQL 接続文字列 | ✅ |

---

## Render へのデプロイ

### 初回セットアップ

1. [Render Dashboard](https://dashboard.render.com) にログイン
2. **New → Blueprint** を選択
3. `Cehira123/postlift-ai` リポジトリを連携
4. `render.yaml` を自動設識しので、環境変数 (`sync: false` の項目) を入力
5. **Apply** ボタンを押すと API + DB + Scheduler が自動起動

### GitHub Secrets の設定 (自動デプロイ用)

```
GitHub リポジトリ → Settings → Secrets and variables → Actions → New repository secret

RENDER_DEPLOY_HOOK_URL  =  Render Dashboard → Service → Settings → Deploy Hook
```

### DB 初期化

Render の PostgreSQL 起動後、Shell より実行:

```bash
psql $DATABASE_URL -f src/db/schema.sql
```

---

## Railway へのデプロイ

### 初回セットアップ

1. [Railway Dashboard](https://railway.app) にログイン
2. **New Project → Deploy from GitHub repo** を選択
3. `Cehira123/postlift-ai` を選択
4. **Add PostgreSQL** プラグインを追加
5. `DATABASE_URL` 等の環境変数を Variables タブで設定

### Scheduler サービスの追加

```
Railway Dashboard → + New Service → GitHub Repo (同じリポ) →
Start Command: python -m src.scheduler.daily_report
```

### GitHub Secrets の設定

```
RAILWAY_TOKEN  =  Railway Dashboard → Account Settings → Tokens → New Token
```

### DB 初期化

```bash
npm install -g @railway/cli
railway login
railway run psql $DATABASE_URL -f src/db/schema.sql
```

---

## 共通: Shopify Webhook 登録

デプロイ完了後、Shopify Partners で Webhook を登録:

```
https://{your-app-url}/webhooks/orders/paid
  Topic: orders/paid
  Format: JSON
```
