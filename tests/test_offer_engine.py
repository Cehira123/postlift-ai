"""
offer_engine の単体テスト
"""
import pytest
from src.ai.offer_engine import _score


def test_score_max():
    """粗利100%, 在庫100, 承諾率100% → スコア 1.0"""
    assert _score(1.0, 100, 1.0) == pytest.approx(1.0)


def test_score_zero():
    """全部 0 → スコア 0.0"""
    assert _score(0.0, 0, 0.0) == pytest.approx(0.0)


def test_score_stock_clipped():
    """在庫 9999 は 100 にクリップされる → stock_norm = 1.0"""
    score_large = _score(0.5, 9999, 0.5)
    score_100 = _score(0.5, 100, 0.5)
    assert score_large == pytest.approx(score_100)


def test_score_weights():
    """重み: margin=0.5, stock=0.2, accept=0.3"""
    # margin=1, stock=0, accept=0 → 0.5
    assert _score(1.0, 0, 0.0) == pytest.approx(0.5)
    # margin=0, stock=100, accept=0 → 0.2
    assert _score(0.0, 100, 0.0) == pytest.approx(0.2)
    # margin=0, stock=0, accept=1 → 0.3
    assert _score(0.0, 0, 1.0) == pytest.approx(0.3)
