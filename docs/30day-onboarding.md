# 30-Day Buyer Onboarding

This onboarding plan is for a buyer who purchased the self-hosted PostLift AI code product.

It is not a public SaaS onboarding plan. The buyer owns their Shopify app, hosting, approvals, data policy, and production operation.

## Week 1: Local Understanding

- Read `README.md`.
- Read `docs/buyer-responsibilities.md`.
- Create a local `.env` from `.env.example`.
- Install dependencies.
- Run `pytest`.
- Open the FastAPI docs locally at `/docs`.

Success condition: the buyer understands the app shape and local tests pass.

## Week 2: Buyer-Owned Deployment

- Create PostgreSQL.
- Deploy the API to the buyer's host.
- Set required environment variables.
- Run schema and migrations.
- Confirm `/health` returns `status: ok`.
- Run `scripts/deployment_smoke.py` against the public API URL.

Success condition: the public API and database are connected.

## Week 3: Shopify Development Store

- Create or open a Shopify Partner app.
- Set the app URL and callback URL.
- Install the app into a development store.
- Sync products.
- Confirm products, variants, and inventory identifiers are stored.
- Trigger a signed webhook simulation.

Success condition: product sync works and a test offer can be created.

## Week 4: Production Decision

- Decide whether to request Shopify protected customer data access.
- Decide whether to request post-purchase extension production access.
- Review privacy policy, terms, and data retention.
- Set monitoring and backup expectations.
- Decide whether to keep the project internal, ship for one merchant, or customize for a client.

Success condition: the buyer has a clear go/no-go decision for their own production use.

## Buyer Reminder

The code product gives a technical head start. It does not replace the buyer's own Shopify approval process, legal review, hosting operations, or merchant support.
