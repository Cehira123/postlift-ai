# Product Spec

PostLift AI is a self-hosted Shopify post-purchase upsell implementation template.

The primary product is source code plus documentation. A buyer can use it as a starting point for their own Shopify app, agency implementation, or internal merchant tool.

## Product Promise

Give developers a working reference implementation for:

- Shopify OAuth.
- Shopify webhook verification.
- Product sync.
- Post-purchase offer lookup.
- Upsell offer scoring.
- Offer response tracking.
- Dashboard metrics.
- PostgreSQL persistence.
- Deployment to a public Python host.

## In Scope

- FastAPI API service.
- PostgreSQL schema and migrations.
- Product, variant, and inventory identifier storage.
- Offer engine using margin, inventory, history, and fit signals.
- Optional AI-generated copy.
- Shopify post-purchase extension scaffold.
- Metrics and A/B result endpoints.
- Privacy webhook handlers.
- Automated tests.
- Self-hosting documentation.

## Out Of Scope

- Managed hosting.
- Legal compliance package.
- Shopify App Store approval guarantee.
- Protected customer data approval guarantee.
- Merchant support desk.
- Payment processing for buyers.
- Revenue uplift guarantee.

## Primary Users

- Shopify developers.
- Shopify agencies.
- Technical merchants.
- Builders studying Shopify app architecture.

## Success Metrics For The Code Product

| Metric | Definition |
| --- | --- |
| Fresh setup success | A buyer can run tests and deploy from the docs. |
| Demo clarity | The product sync and offer lifecycle can be shown without private customer data. |
| Support clarity | Buyers understand what is and is not included. |
| Code confidence | Automated tests pass before delivery. |
| Upgrade potential | Buyers can purchase setup help or customization separately. |

## Key Limitation

Real production use with order history, customer data, or post-purchase extension access may require Shopify approval. This is intentionally documented as a buyer responsibility.
