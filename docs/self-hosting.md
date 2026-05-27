# Self-Hosting Guide

This guide is for buyers who want to deploy PostLift AI in their own account.

## 1. Prepare Accounts

You need:

- A GitHub account or source-code archive.
- A hosting provider that can run Python web services.
- PostgreSQL.
- A Shopify Partner account.
- A Shopify development store or merchant store.
- Optional: an OpenAI API key for generated copy.

## 2. Configure Environment Variables

Set these on the host:

| Variable | Required | Notes |
| --- | --- | --- |
| `APP_URL` | Yes | Public HTTPS URL of the deployed API. |
| `DATABASE_URL` | Yes | PostgreSQL connection string. |
| `SHOPIFY_API_KEY` | Yes | Shopify app client ID. |
| `SHOPIFY_API_SECRET` | Yes | Shopify app client secret. |
| `SHOPIFY_WEBHOOK_SECRET` | Yes | Shopify webhook signing secret. |
| `SHOPIFY_API_VERSION` | Recommended | Match the version selected in Shopify Partners. |
| `SHOPIFY_BILLING_TEST` | Recommended | Use `true` for development stores. |
| `OPENAI_API_KEY` | Optional | Enables generated copy. |
| `CORS_ORIGINS` | Recommended | Include the public API URL and local development URLs. |
| `RUN_SCHEDULER` | Recommended | Use `true` for a single-service deployment. |

Never put real secrets in GitHub, screenshots, tickets, or public support messages.

## 3. Initialize The Database

Run the schema once:

```bash
python scripts/apply_sql.py src/db/schema.sql
python scripts/apply_sql.py src/db/migrations/001_variant_inventory_ids.sql
```

The script reads `DATABASE_URL` from the environment.

## 4. Deploy The API

Deploy with Docker, Railway, Render, or another Python-compatible host.

After deployment, open:

```text
https://your-public-api-url/health
```

Expected result:

```json
{"status":"ok","version":"0.4.0","db":"ok"}
```

If the response says `degraded`, the database is not connected correctly.

## 5. Configure Shopify App

In Shopify Partners, set:

| Setting | Value |
| --- | --- |
| App URL | `https://your-public-api-url/` |
| Allowed redirection URL | `https://your-public-api-url/auth/callback` |
| Webhooks API version | Match `SHOPIFY_API_VERSION`. |

Recommended scopes for the current implementation:

```text
read_orders,read_products,read_inventory,read_customers,write_draft_orders
```

Some scopes, webhook topics, and post-purchase access may require Shopify approval. The buyer owns that process.

## 6. Install And Test

1. Install the app into a Shopify development store.
2. Confirm OAuth returns to the embedded app.
3. Sync products.
4. Set at least one product margin high enough for offer eligibility.
5. Trigger a signed test webhook or use a development-store order flow.
6. Confirm `/offers/current` returns an offer.
7. Accept or decline the offer.
8. Confirm metrics update.

## 7. Run Automated Checks

```bash
pytest
python scripts/deployment_smoke.py https://your-public-api-url
```

The deployment smoke test checks health and metrics endpoints. It does not prove Shopify approval or real customer-data access.
