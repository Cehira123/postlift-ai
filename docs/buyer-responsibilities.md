# Buyer Responsibilities

PostLift AI is sold as self-hosted source code. The buyer is responsible for turning it into their own production system.

This document is practical product guidance, not legal advice.

## Buyer Owns

- Shopify Partner account and Shopify app configuration.
- Shopify development store or merchant store access.
- Shopify protected customer data and post-purchase access requests.
- Hosting account, database, backups, and monitoring.
- Environment variables and secret management.
- Production incident response.
- Merchant or client support.
- Privacy policy, terms, data-processing agreements, and regional compliance.
- Payment processing, taxes, refunds, and customer contracts.

## Seller Provides

- Source code.
- Documentation.
- Database schema and migrations.
- Test commands.
- Deployment examples.
- A technical reference flow for product sync, offer creation, and metrics.

## Seller Does Not Provide By Default

- Managed hosting.
- Guaranteed uptime.
- Legal review.
- Shopify App Store approval.
- Protected customer data approval.
- Merchant support desk.
- Revenue guarantees.
- Ongoing maintenance unless separately agreed.

## Shopify Data Access

Some real Shopify flows may require additional Shopify approval, especially:

- Reading all historical orders.
- Customer-related webhooks or protected customer data.
- Post-purchase extension access in production.

If a buyer cannot or does not want to request these approvals, they can still study, modify, and test the implementation with local tests, product sync, development-store installs, and signed webhook simulations.

## Suggested Buyer Checklist

Before production use, the buyer should confirm:

- Their app URLs and callback URLs are correct.
- Webhook HMAC verification passes.
- Database migrations have run.
- Secrets are not committed to source control.
- Logs do not expose access tokens, customer data, or database URLs.
- Data retention and deletion behavior matches their own policy.
- Required Shopify access approvals are complete.
- Their privacy policy explains what data is processed and why.

## Suggested Sales Wording

Use wording like:

> This is a self-hosted source-code product. You receive the implementation, setup guide, and test flow. You are responsible for your own Shopify account, hosting, compliance, approvals, and production operation.

Avoid wording like:

> Fully compliant, guaranteed approved, zero-risk Shopify SaaS.
