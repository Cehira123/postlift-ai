"""
offer_engine の単体テスト
重み: WEIGHT_MARGIN=0.4, WEIGHT_STOCK=0.2, WEIGHT_ACCEPT_RATE=0.25, WEIGHT_CUSTOMER=0.15
"""
import pytest
from src.ai.offer_engine import _score


def test_score_max():
    """全パラメータ最大値 → スコア 1.0"""
    assert _score(1.0, 100, 1.0, 1.0) == pytest.approx(1.0)


def test_score_zero():
    """全パラメータ 0 → スコア 0.0"""
    assert _score(0.0, 0, 0.0, 0.0) == pytest.approx(0.0)


def test_score_stock_clipped():
    """在庫 9999 は 100 にクリップされる → stock_norm = 1.0"""
    score_large = _score(0.5, 9999, 0.5, 0.5)
    score_100   = _score(0.5, 100,  0.5, 0.5)
    assert score_large == pytest.approx(score_100)


def test_score_weights():
    """各重み単独の確認 (customer_rfm=0.0 で除外)"""
    # margin=1 のみ → 0.40
    assert _score(1.0, 0, 0.0, 0.0) == pytest.approx(0.40)
    # stock=100 のみ → 0.20
    assert _score(0.0, 100, 0.0, 0.0) == pytest.approx(0.20)
    # accept_rate=1 のみ → 0.25
    assert _score(0.0, 0, 1.0, 0.0) == pytest.approx(0.25)
    # customer_rfm=1 のみ → 0.15
    assert _score(0.0, 0, 0.0, 1.0) == pytest.approx(0.15)
