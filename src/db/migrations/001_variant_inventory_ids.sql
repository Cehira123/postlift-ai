-- Store Shopify variant and inventory IDs for post-purchase add_variant support.

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS inventory_item_id TEXT;

CREATE INDEX IF NOT EXISTS idx_products_inventory_item
    ON products(shop_domain, inventory_item_id);
