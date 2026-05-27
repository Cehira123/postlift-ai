# PostLift AI

Self-hosted Shopify post-purchase upsell implementation template.

PostLift AI is packaged as a code product, not as a hosted SaaS and not as a ready-submitted Shopify App Store listing. A buyer can deploy the API to their own hosting account, connect their own Shopify app, run their own database, and adapt the implementation for their own merchant or client project.

## What This Code Product Includes

- FastAPI backend for Shopify OAuth, webhooks, offers, products, metrics, and dashboard pages.
- Shopify post-purchase UI extension scaffold.
- PostgreSQL schema for shops, products, offers, KPI snapshots, A/B tests, and customer scores.
- Product sync from Shopify Admin API.
- Offer ranking based on margin, inventory, acceptance history, and customer fit.
- Optional OpenAI-generated upsell copy when `OPENAI_API_KEY` is configured.
- Daily KPI snapshot and low-performing offer suppression jobs.
- Docker, Railway, Render, and GitHub Actions configuration.
- Tests for offer scoring, Shopify Admin API product mapping, webhook HMAC validation, and the post-purchase offer lifecycle.

## What This Product Is Not

- It is not a managed SaaS operated by this repository owner.
- It is not legal, privacy, tax, billing, or Shopify compliance advice.
- It is not a guarantee of Shopify App Store approval.
- It does not include ongoing merchant support, hosting fees, database fees, or paid API usage.
- It does not remove the buyer's responsibility for Shopify protected customer data approvals when they use restricted webhooks or customer data.

For buyer-side responsibility boundaries, see [docs/buyer-responsibilities.md](docs/buyer-responsibilities.md).
For the recommended Shopify setup while selling this as source code, see [docs/shopify-settings-for-code-product.md](docs/shopify-settings-for-code-product.md).
For a Japanese buyer-facing sales page draft, see [docs/sales-page-ja.md](docs/sales-page-ja.md).
For a detailed Japanese buyer setup guide, see [docs/setup-guide-ja.md](docs/setup-guide-ja.md).
For a Japanese demo runbook, see [docs/demo-guide-ja.md](docs/demo-guide-ja.md).

## Verified Development Flow

The current implementation has been validated against a Shopify development-store style flow:

1. API deploys successfully to a public HTTPS host.
2. `/health` returns `status: ok` when PostgreSQL is configured.
3. Shopify app installation redirects through OAuth.
4. Product sync stores Shopify products, variants, and inventory identifiers.
5. A signed `orders/paid` webhook can create an upsell offer.
6. `/offers/current` returns an offer payload for the post-purchase extension.
7. Accept/decline tracking updates metrics and A/B test records.
8. Automated tests cover the main local lifecycle.

Real merchant production use still requires the buyer to configure and approve their own Shopify app and data-access settings.

## Architecture

```text
Buyer-owned Shopify app
        |
        v
Shopify webhook or test event
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

For local development without PostgreSQL, `/health` returns `degraded` and the docs remain available at `/docs`. Metrics endpoints return empty fallback data when no database is configured, while write paths still require `DATABASE_URL`.

## Required Environment Variables

| Variable | Purpose |
| --- | --- |
| `APP_URL` | Public HTTPS URL for Shopify callbacks and webhook registration. |
| `DATABASE_URL` | PostgreSQL connection string. |
| `SHOPIFY_API_KEY` | Buyer-owned Shopify app client ID. |
| `SHOPIFY_API_SECRET` | Buyer-owned Shopify app client secret. |
| `SHOPIFY_WEBHOOK_SECRET` | Secret used to verify Shopify webhook HMAC signatures. |
| `OPENAI_API_KEY` | Optional. Enables generated upsell copy. Without it, deterministic fallback copy is used. |
| `CORS_ORIGINS` | Comma-separated allowed browser origins. |
| `RUN_SCHEDULER` | Set to `false` to disable daily background jobs. |

## Testing

```bash
pytest
```

The E2E test runs in-process with a fake database, so it is safe to run locally without PostgreSQL:

```bash
pytest tests/test_e2e.py
```

For public deployment validation:

```bash
python scripts/deployment_smoke.py https://your-public-api-url
```

## Deployment

1. Create a PostgreSQL database.
2. Run `src/db/schema.sql`.
3. Run migrations in `src/db/migrations`.
4. Set every required environment variable on the hosting platform.
5. Configure Shopify app URLs to point to `APP_URL`.
6. Install the app into a development store.
7. Sync products and run the test webhook flow.

Detailed setup steps are in [docs/self-hosting.md](docs/self-hosting.md) and [docs/deploy.md](docs/deploy.md).

## Shopify Data-Access Note

Some real Shopify topics, especially order history, customer-related data, and post-purchase extension access, may require Shopify approvals. A buyer can still evaluate the code with local tests, signed webhook simulation, product sync, and a development-store install. Production use is the buyer's responsibility.

## Suggested Code Product Packaging

Recommended deliverables for selling this as a code product:

- Private repository or downloadable source archive.
- Setup guide and environment-variable checklist.
- Railway/Render deployment guide.
- Test checklist with expected outputs.
- Buyer-responsibility and data-access notes.
- Shopify settings guidance for code-product mode.
- Japanese buyer-facing sales page draft.
- Detailed Japanese buyer setup guide.
- Japanese demo runbook.
- Optional paid setup or customization service.

See [docs/code-product-packaging.md](docs/code-product-packaging.md) for package structure and pricing ideas.

## License

MIT License. Copyright 2026 Cehira123.
