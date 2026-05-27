# Shopify Settings For Code Product Mode

Use this guide when PostLift AI is being sold as source code instead of operated as a public Shopify SaaS.

## Recommended Position

Keep the Shopify app as a development/testing app unless you intentionally decide to operate a real SaaS.

For a code product sale, the buyer should create their own Shopify app and enter their own credentials. Do not ship your private Shopify client secret, webhook secret, access tokens, database URL, or Railway environment values to buyers.

## What To Keep

It is fine to keep your current development setup for demos:

- Development store install.
- App URL pointing to your Railway demo API.
- Redirect URL pointing to `/auth/callback`.
- Product sync for demo products.
- Signed webhook simulation for offer creation.
- Public API smoke test.

## What To Avoid For Now

Do not continue deeper into production approval work unless you want to become the SaaS operator:

- Shopify App Store public listing submission.
- Protected customer data approval for broad production use.
- Production post-purchase extension approval.
- Real merchant billing.
- Real customer-data processing.

Pending requests can be left alone for testing. If Shopify provides a withdraw/cancel option and you no longer want the access, you can withdraw them. If there is no simple option, just do not proceed with production submission.

## Minimal Buyer-Facing Scopes

For demo and source-code evaluation, keep scopes as narrow as the tested flow allows:

```text
read_products,read_inventory,read_orders,write_draft_orders
```

Use customer-related scopes only if the buyer intentionally enables customer scoring and accepts the related approval/compliance work.

## Buyer Handoff Rule

Before selling or handing over the code:

1. Remove all real secrets from screenshots and docs.
2. Tell the buyer to create their own Shopify app.
3. Tell the buyer to create their own database.
4. Tell the buyer to run migrations.
5. Tell the buyer to run `pytest`.
6. Tell the buyer to run the deployment smoke test.
7. Point the buyer to `docs/buyer-responsibilities.md`.

## Your Current Shopify Setup

Your current Shopify configuration is useful as a demo environment. Treat it as proof that the implementation works, not as the production system buyers will use.
