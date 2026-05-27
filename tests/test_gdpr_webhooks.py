import base64
import hashlib
import hmac

from src.api import gdpr


def _shopify_hmac(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_gdpr_verify_accepts_shopify_signature(monkeypatch):
    body = b'{"shop_domain":"test.myshopify.com"}'
    secret = "privacy-secret"
    monkeypatch.setattr(gdpr, "SHOPIFY_WEBHOOK_SECRET", secret)

    assert gdpr._verify(body, _shopify_hmac(secret, body))


def test_gdpr_verify_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(gdpr, "SHOPIFY_WEBHOOK_SECRET", "privacy-secret")

    assert not gdpr._verify(b'{"shop_domain":"test.myshopify.com"}', "invalid")


def test_gdpr_verify_rejects_missing_secret(monkeypatch):
    monkeypatch.setattr(gdpr, "SHOPIFY_WEBHOOK_SECRET", "")

    assert not gdpr._verify(b'{"shop_domain":"test.myshopify.com"}', "anything")
