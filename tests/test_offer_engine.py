"""Unit tests for offer scoring."""
import pytest

from src.ai.offer_engine import _score


def test_score_max():
    assert _score(1.0, 100, 1.0, 1.0) == pytest.approx(1.0)


def test_score_zero():
    assert _score(0.0, 0, 0.0, 0.0) == pytest.approx(0.0)


def test_score_stock_clipped():
    score_large = _score(0.5, 9999, 0.5, 0.5)
    score_100 = _score(0.5, 100, 0.5, 0.5)
    assert score_large == pytest.approx(score_100)


def test_score_weights():
    assert _score(1.0, 0, 0.0, 0.0) == pytest.approx(0.40)
    assert _score(0.0, 100, 0.0, 0.0) == pytest.approx(0.20)
    assert _score(0.0, 0, 1.0, 0.0) == pytest.approx(0.25)
    assert _score(0.0, 0, 0.0, 1.0) == pytest.approx(0.15)


def test_score_clamps_inputs():
    assert _score(10.0, -100, 10.0, -5.0) == pytest.approx(0.65)
