# test_scorer_m4.py — testy dla faz 17+18 scorera M4
import pytest
from datetime import date, timedelta
from services.ingestion.scorer import _deadline_proximity_bonus


def test_deadline_null():
    assert _deadline_proximity_bonus(None) == 0.0


def test_deadline_urgent():
    d = date.today() + timedelta(days=5)
    assert _deadline_proximity_bonus(d) > 0


def test_deadline_optimal():
    d = date.today() + timedelta(days=14)
    assert _deadline_proximity_bonus(d) > 0


def test_deadline_far():
    d = date.today() + timedelta(days=90)
    assert _deadline_proximity_bonus(d) == 0.0


def test_deadline_past():
    d = date.today() - timedelta(days=1)
    bonus = _deadline_proximity_bonus(d)
    assert bonus <= 0  # malus or zero
