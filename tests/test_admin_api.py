from src.shopify.admin_api import extract_product_rows


def test_extract_product_rows_uses_variant_ids_for_post_purchase():
    rows = extract_product_rows(
        "demo.myshopify.com",
        [
            {
                "id": 100,
                "title": "Coffee",
                "variants": [
                    {
                        "id": 200,
                        "inventory_item_id": 300,
                        "title": "Dark roast",
                        "price": "25.00",
                        "cost": "10.00",
                        "inventory_quantity": 7,
                    }
                ],
            }
        ],
    )

    assert rows == [
        {
            "shop_domain": "demo.myshopify.com",
            "product_id": "200",
            "inventory_item_id": "300",
            "title": "Coffee - Dark roast",
            "price": 25.0,
            "gross_margin": 60.0,
            "stock_qty": 7,
        }
    ]
