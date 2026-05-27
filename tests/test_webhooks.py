import base64
import hashlib
import hmac

from src.api import shopify_webhook


def _shopify_hmac(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_verify_hmac_accepts_shopify_signature(monkeypatch):
    body = b'{"id":123}'
    secret = "test-secret"
    monkeypatch.setattr(shopify_webhook, "SHOPIFY_WEBHOOK_SECRET", secret)

    assert shopify_webhook._verify_hmac(body, _shopify_hmac(secret, body))


def test_verify_hmac_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(shopify_webhook, "SHOPIFY_WEBHOOK_SECRET", "test-secret")

    assert not shopify_webhook._verify_hmac(b'{"id":123}', "invalid")


def test_verify_hmac_rejects_missing_secret(monkeypatch):
    monkeypatch.setattr(shopify_webhook, "SHOPIFY_WEBHOOK_SECRET", "")

    assert not shopify_webhook._verify_hmac(b'{"id":123}', "anything")
