# Deployment Guide

This guide is the practical setup path for getting PostLift AI onto a public HTTPS URL in the buyer's own hosting account.

PostLift AI is a self-hosted code product. The buyer owns the hosting account, database, Shopify app, access approvals, privacy/legal review, and production operations.

Use Railway first if you want the quickest path. Use Render if you prefer Blueprint-style infrastructure from `render.yaml`.

## Required Values

Prepare these before deploying:

| Variable | Where to get it | Required |
| --- | --- | --- |
| `SHOPIFY_API_KEY` | Shopify Partners app client ID | Yes |
| `SHOPIFY_API_SECRET` | Shopify Partners app client secret | Yes |
| `SHOPIFY_WEBHOOK_SECRET` | Shopify app webhook secret | Yes |
| `APP_URL` | Public HTTPS URL of this API | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key for generated copy | Optional |
| `CORS_ORIGINS` | Public API URL and local dev URLs, comma-separated | Recommended |
| `SHOPIFY_BILLING_TEST` | `true` for dev stores, `false` for production billing | Recommended |
| `RUN_SCHEDULER` | `true` for API service unless scheduler is separated | Recommended |

Never commit real secrets to GitHub. Add them only in the hosting provider dashboard.

## Railway Setup

1. Open [Railway](https://railway.app).
2. Click **New Project**.
3. Choose **Deploy from GitHub repo**.
4. Select `Cehira123/postlift-ai`.
5. Add a PostgreSQL service from **New Service**.
6. Open the API service, then open **Variables**.
7. Add the required variables above.
8. Set `DATABASE_URL` to Railway's PostgreSQL connection variable.
9. Deploy the service.
10. Open the generated public URL and check `/health`.

Expected result after database setup:

```json
{"status":"ok","version":"0.4.0","db":"ok"}
```

If the app is up but the database is not connected, `/health` returns `status: degraded`.

## Railway Database Initialization

After PostgreSQL exists, run the schema once:

```bash
railway run psql "$DATABASE_URL" -f src/db/schema.sql
railway run psql "$DATABASE_URL" -f src/db/migrations/001_variant_inventory_ids.sql
```

If you do not have the Railway CLI yet:

```bash
npm install -g @railway/cli
railway login
```

## Railway Scheduler Service

The API can run the scheduler inside the web process with `RUN_SCHEDULER=true`.

For a cleaner production setup, create a second Railway service from the same repo:

```bash
python -m src.scheduler.daily_report
```

Then set `RUN_SCHEDULER=false` on the API service and keep the same `DATABASE_URL` on the scheduler service.

## Render Setup

1. Open [Render](https://dashboard.render.com).
2. Click **New**.
3. Choose **Blueprint**.
4. Connect `Cehira123/postlift-ai`.
5. Render reads `render.yaml`.
6. Fill every `sync: false` environment variable.
7. Apply the Blueprint.
8. Initialize the database with `src/db/schema.sql` and migrations.
9. Check `/health`.

## Shopify App URLs

After the API is deployed, open Shopify Partners and set:

| Shopify setting | Value |
| --- | --- |
| App URL | `https://your-public-api-url/` |
| Allowed redirection URL | `https://your-public-api-url/auth/callback` |
| Post-purchase extension API URL | `https://your-public-api-url` |

Register these webhook topics when your Shopify app has access to them:

- `orders/paid`
- `app/uninstalled`
- `products/update`
- `inventory_levels/update`
- `customers/update`

Webhook delivery URL pattern:

```text
https://your-public-api-url/webhooks/orders/paid
```

`orders/paid`, customer-related topics, and post-purchase production access may require Shopify protected customer data or extension approval. If those approvals are not available yet, use the automated tests, product sync, and signed webhook simulation to validate the implementation.

## Smoke Test

After deployment, run:

```bash
python scripts/deployment_smoke.py https://your-public-api-url
```

This checks:

- `/health`
- `/metrics/summary`
- `/metrics/trend`
- `/metrics/products`

Use a real Shopify development store for the final buyer-owned E2E test. The smoke test only proves that the public API is reachable and basic routes respond.
