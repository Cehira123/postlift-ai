# PostLift AI Launch Plan

This document explains what should happen next before PostLift AI is treated as a public launch candidate.

## Current State

PostLift AI already has the core product loop in place:

- Shopify OAuth, webhook, offer, product, billing, metrics, and dashboard routes.
- A post-purchase UI extension scaffold.
- PostgreSQL schema and a first migration for Shopify variant and inventory identifiers.
- Tests for the AI offer engine, Shopify Admin API mapping, webhook HMAC validation, and an in-process post-purchase E2E lifecycle.
- Docker, Railway, Render, and GitHub Actions configuration.

The project is ready for real Shopify development-store validation, but it is not yet ready for a public Shopify App Store submission.

## What Codex Can Do Automatically

Codex can safely continue these tasks in the repository:

1. Clean the remaining garbled documentation and make all docs consistent.
2. Add or improve automated tests.
3. Fix backend bugs found by tests or code review.
4. Improve dashboard, settings, and onboarding screens.
5. Add migrations and deployment notes.
6. Commit and push changes to GitHub when you ask for it.

Codex can also run local tests and local browser checks when the app starts correctly in this workspace.

## What You Need To Do In Browser Screens

Some tasks need your own logged-in accounts and cannot be fully automated from code alone:

1. Create or open a Shopify Partners account.
2. Create a Shopify development store.
3. Create a Shopify app and copy the client ID, client secret, and webhook secret.
4. Deploy the API to a public HTTPS URL such as Railway or Render.
5. Add the deployed `APP_URL` to Shopify app settings.
6. Add production environment variables on the hosting service.
7. Install the app into the development store and place a real test order.

These steps are normal. They involve private account screens, payment/test-store screens, and generated secrets.

## Recommended Next Milestone

The next milestone should be: "Development store flow works end to end."

Definition of done:

1. The app installs into a Shopify development store.
2. Shopify redirects through OAuth and stores the shop.
3. Product sync stores Shopify variant IDs and inventory item IDs.
4. An `orders/paid` webhook creates an upsell offer.
5. The post-purchase extension requests `/offers/current` and receives a valid `variant_id`.
6. Accepting or declining the offer records the response.
7. Dashboard metrics show the test data.
8. `pytest` passes after any changes.

Do not start App Store submission work until this milestone is green.

## Practical Order Of Work

### Phase 1: Repository Polish

- Replace remaining garbled docs with clean English or Japanese docs.
- Review security-sensitive OAuth and webhook code.
- Keep CI passing on every push.

### Phase 2: Deployment Setup

- Choose one host first. Railway is the easiest starting point if you want speed.
- Create PostgreSQL on the same host.
- Run `src/db/schema.sql` and migrations.
- Set environment variables from `.env.example`.
- Confirm `/health` returns `{"status":"ok"}` after `DATABASE_URL` is set.

### Phase 3: Shopify Connection

- Create the Shopify app in Shopify Partners.
- Set app URL and callback URL to the deployed HTTPS URL.
- Register required webhook topics.
- Install the app into a development store.
- Sync products and confirm variants are stored.

### Phase 4: Real E2E

- Place a test order.
- Confirm the `orders/paid` webhook creates an offer.
- Open the post-purchase extension flow.
- Accept one offer and decline one offer.
- Confirm metrics and A/B records update.

### Phase 5: Launch Readiness

- Add merchant-facing onboarding.
- Improve billing plan enforcement.
- Add privacy, uninstall, and data-retention documentation.
- Add operational monitoring and alerting.
- Prepare Shopify App Store listing assets only after the development-store flow is stable.

## Most Important Next Code Improvements

1. Persist and verify OAuth `state` to harden Shopify install security.
2. Replace placeholder extension API URL handling with environment-driven configuration.
3. Add a real product sync integration test using recorded or mocked Shopify Admin API responses.
4. Add dashboard empty, loading, and error states.
5. Add a deployment smoke-test command that checks health, metrics fallback, and webhook validation.

## Simple Rule

For now, every development session should end with:

```bash
pytest
git status
```

If tests pass and the intended files are changed, commit and push to GitHub.
