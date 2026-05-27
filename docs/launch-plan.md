# Code Product Readiness Plan

PostLift AI is now positioned as a self-hosted code product. The goal is to sell the implementation, docs, and testable deployment flow, while the buyer owns hosting, Shopify approvals, legal obligations, merchant support, and production operations.

## Current State

The repository already includes the core product loop:

- Shopify OAuth, webhook, offer, product, metrics, and dashboard routes.
- Shopify post-purchase UI extension scaffold.
- PostgreSQL schema and migration files.
- Product sync from Shopify Admin API.
- Offer ranking and fallback/generated copy.
- Tests for scoring, Admin API mapping, webhook HMAC validation, and E2E offer lifecycle.
- Docker, Railway, Render, and GitHub Actions configuration.

This is suitable for packaging as a technical starter kit or implementation template. It should not be marketed as a fully operated SaaS unless a separate business, compliance, support, and hosting operation is created.

## Productization Definition Of Done

The code product is ready to sell when:

1. A buyer can read the README and understand that this is self-hosted source code.
2. A buyer can follow the self-hosting guide without asking where each credential goes.
3. The test suite passes from a fresh checkout.
4. The deployment smoke test works against a public API URL.
5. The buyer-responsibility document clearly explains what is outside the sale.
6. Shopify protected-data and post-purchase access requirements are disclosed.
7. Demo screenshots or a short demo video show product sync, offer creation, and metrics.

## Selling Scope

The sale should include:

- Source code.
- Database schema and migrations.
- Deployment instructions.
- Shopify app configuration instructions.
- Test and smoke-test commands.
- A concise architecture explanation.
- A clear support boundary.

The sale should not promise:

- Shopify App Store approval.
- Legal compliance for the buyer's jurisdiction.
- Live merchant support.
- Hosting, database, email, OpenAI, or Shopify costs.
- Revenue uplift guarantees.
- Access to protected Shopify customer data without Shopify approval.

## Practical Next Steps

### Phase 1: Documentation Packaging

- Keep README focused on self-hosted code-product use.
- Maintain [self-hosting.md](self-hosting.md) as the main setup path.
- Maintain [buyer-responsibilities.md](buyer-responsibilities.md) as the boundary document.
- Maintain [code-product-packaging.md](code-product-packaging.md) for sales tiers and deliverables.

### Phase 2: Demo Proof

- Record or capture the flow:
  - API health check.
  - Product sync.
  - Signed webhook offer creation.
  - `/offers/current` response.
  - Accept/decline tracking.
  - Metrics update.
- Avoid showing secrets, database URLs, access tokens, or real customer information.

### Phase 3: Buyer Experience

- Add a `docs/troubleshooting.md` file if repeated setup issues appear.
- Add a sample `.env.local.example` for local-only testing if needed.
- Keep test commands short and repeatable.
- Keep deployment docs provider-neutral where possible.

### Phase 4: Optional Hardening

These are useful if the product is sold at a higher price:

- Persist and verify OAuth `state`.
- Add dashboard empty, loading, and error states.
- Add a recorded Shopify Admin API integration test.
- Add clearer extension deployment instructions.
- Add log redaction for secrets and access tokens.
- Add backup/restore notes for PostgreSQL.

## Session Rule

Every development session should end with:

```bash
pytest
git status
```

If the intended files changed and tests pass, commit and push to GitHub.
