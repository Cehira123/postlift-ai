# Code Product Packaging

This file describes how to package PostLift AI as a saleable source-code product.

## Core Deliverables

- Source code repository or downloadable archive.
- README that clearly says the product is self-hosted.
- Setup guide.
- Japanese buyer setup guide.
- Deployment guide.
- Buyer responsibilities document.
- Test checklist.
- Japanese demo runbook.
- Example `.env.example`.
- Demo screenshots or short demo video.

## Recommended Folder Highlights

Tell buyers to start here:

- `README.md`
- `docs/self-hosting.md`
- `docs/setup-guide-ja.md`
- `docs/demo-guide-ja.md`
- `docs/deploy.md`
- `docs/buyer-responsibilities.md`
- `docs/architecture.md`
- `tests/test_e2e.py`

## Sales Page Claims To Use

Good claims:

- Self-hosted Shopify upsell implementation template.
- Includes OAuth, webhooks, product sync, offer ranking, metrics, and tests.
- Designed for developers and agencies.
- Deployable to common Python hosting providers.
- Clear buyer-owned compliance and hosting boundary.

Avoid claims:

- Guaranteed Shopify App Store approval.
- No compliance work needed.
- Guaranteed revenue increase.
- Fully managed SaaS.
- Works with all Shopify stores without access approvals.

## Support Tiers

| Tier | Support Boundary |
| --- | --- |
| Code only | Buyer receives source and docs. No private setup support. |
| Code plus limited support | Buyer can ask setup questions for a fixed period. |
| Setup assist | Seller helps deploy into buyer-owned accounts once. |
| Custom implementation | Separate project contract and custom scope. |

## Pre-Sale Checklist

- `pytest` passes.
- README reflects self-hosted positioning.
- Secrets are not committed.
- Demo flow can be shown without private customer data.
- Buyer responsibilities are linked from the README.
- Deployment guide includes database initialization.

## Post-Sale Checklist

Send buyers to:

1. `README.md`
2. `docs/self-hosting.md`
3. `docs/setup-guide-ja.md`
4. `docs/demo-guide-ja.md`
5. `docs/buyer-responsibilities.md`
6. `docs/deploy.md`

Keep support answers focused on code and setup. Do not make legal, tax, or Shopify approval promises.
