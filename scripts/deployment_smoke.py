"""Smoke-test a deployed PostLift AI API."""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urljoin

import httpx


def build_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def check(client: httpx.Client, base_url: str, path: str, params: dict[str, str] | None = None) -> bool:
    url = build_url(base_url, path)
    response = client.get(url, params=params)
    ok = response.status_code == 200
    status = "ok" if ok else "fail"
    print(f"{status:4} {response.status_code} {response.url}")
    if not ok:
        print(response.text[:500])
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a deployed PostLift AI API.")
    parser.add_argument("base_url", help="Public API base URL, for example https://postlift-api.example.com")
    parser.add_argument("--shop", default="smoke-test.myshopify.com", help="Shop domain used for metrics checks.")
    args = parser.parse_args()

    checks = [
        ("/health", None),
        ("/metrics/summary", {"shop_domain": args.shop}),
        ("/metrics/trend", {"shop_domain": args.shop}),
        ("/metrics/products", {"shop_domain": args.shop}),
    ]

    with httpx.Client(timeout=15.0) as client:
        results = [check(client, args.base_url, path, params) for path, params in checks]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
