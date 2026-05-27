# Code Product Roadmap

This roadmap tracks the source-code product, not a hosted SaaS launch.

## Phase 1: Saleable Starter Kit

- [x] FastAPI backend.
- [x] PostgreSQL schema.
- [x] Shopify OAuth route.
- [x] Shopify webhook validation.
- [x] Product sync.
- [x] Offer ranking.
- [x] Metrics endpoints.
- [x] Basic dashboard templates.
- [x] Automated tests.
- [x] Deployment smoke test.
- [x] Self-hosting documentation.
- [x] Buyer responsibility documentation.

## Phase 2: Better Buyer Experience

- [ ] Add a troubleshooting guide.
- [ ] Add a demo screenshot set.
- [ ] Add a short demo script for product sync and offer creation.
- [ ] Add a one-page sales description.
- [ ] Add a fresh-install checklist.
- [ ] Add a known-limitations section.

## Phase 3: Higher-Value Package

- [ ] Persist and verify OAuth `state`.
- [ ] Improve dashboard empty, loading, and error states.
- [ ] Add recorded Shopify Admin API integration tests.
- [ ] Add extension deployment screenshots.
- [ ] Add PostgreSQL backup and restore notes.
- [ ] Add log redaction for secrets and tokens.

## Phase 4: Optional Managed Business

Only consider this phase if the owner intentionally chooses to run a real SaaS later.

- Merchant support workflow.
- Hosted billing workflow.
- Uptime monitoring and incident response.
- Privacy/legal review.
- Shopify App Store submission assets.
- Public production data-access approvals.

Until that decision is made, keep the project positioned as a self-hosted code product.
