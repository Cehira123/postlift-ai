# PostLift AI

AI-powered post-purchase upsell optimization for Shopify.

PostLift AI selects the best one-click post-purchase offer after an order is paid. It ranks products using gross margin, inventory, historical acceptance rate, and customer fit, then generates short conversion copy with an OpenAI model when an API key is configured.

## What It Includes

- FastAPI backend for Shopify OAuth, webhooks, offers, products, billing, metrics, and dashboard pages.
- Shopify post-purchase UI extension scaffold.
- PostgreSQL schema for shops, products, offers, billing, KPI snapshots, A/B tests, and customer scores.
- Daily KPI snapshot and low-performing offer suppression jobs.
- Docker, Railway, Render, and GitHub Actions configuration.
- Unit tests for scoring and webhook signature validation.

## Architecture

```text
Shopify orders/paid webhook
        |
        v
PostLift API -> Product and customer scoring -> Offer persistence
        |                                           |
        v                                           v
Shopify post-purchase extension <-------- /offers/current
        |
        v
/webhooks/upsell/respond -> acceptance metrics and A/B result
```

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.api.main:app --reload --port 5000
```

For local development without PostgreSQL, `/health` returns `degraded` and the docs remain available at `/docs`. Database-backed endpoints require `DATABASE_URL`.

## Required Environment Variables

| Variable | Purpose |
| --- | --- |
| `APP_URL` | Public HTTPS URL for Shopify callbacks and webhook registration. |
| `DATABASE_URL` | PostgreSQL connection string. |
| `SHOPIFY_API_KEY` | Shopify app client ID. |
| `SHOPIFY_API_SECRET` | Shopify app client secret. |
| `SHOPIFY_WEBHOOK_SECRET` | Secret used to verify webhook HMAC signatures. |
| `OPENAI_API_KEY` | Optional. Enables generated upsell copy. Without it, deterministic fallback copy is used. |
| `CORS_ORIGINS` | Comma-separated allowed browser origins. |
| `RUN_SCHEDULER` | Set to `false` to disable daily background jobs. |

## Testing

```bash
pytest
```

The database smoke test is opt-in:

```bash
RUN_E2E=1 DATABASE_URL=postgresql://... pytest tests/test_e2e.py
```

## Deployment Checklist

1. Create a PostgreSQL database and run `src/db/schema.sql`.
2. Set every required environment variable on the hosting platform.
3. Configure Shopify app URLs to point to `APP_URL`.
4. Register webhook topics for `orders/paid`, `app/uninstalled`, product updates, inventory updates, and customer updates.
5. Deploy the API and confirm `/health` returns `status: ok`.
6. Build and deploy the Shopify extension.
7. Run a test order in a Shopify development store and confirm offer creation and acceptance tracking.

## Pricing Model

| Plan | Price | Suggested Limit |
| --- | ---: | --- |
| Starter | $29/month | Up to 500 offers/month |
| Growth | $79/month | Up to 5,000 offers/month |
| Scale | $199/month | Higher-volume merchants |

## License

MIT License. Copyright 2026 Cehira123.
