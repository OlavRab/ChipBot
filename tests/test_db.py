"""Tests for db.py — tier management."""
import os
import pytest
import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr('db.DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    yield


def test_default_tier_is_basic():
    assert db.get_tier('123') == 'basic'


def test_default_limit_is_25():
    assert db.get_limit('123') == 25


def test_set_tier_pro():
    db.set_tier('123', 'pro')
    assert db.get_tier('123') == 'pro'
    assert db.get_limit('123') == 50


def test_set_tier_premium():
    db.set_tier('123', 'premium')
    assert db.get_tier('123') == 'premium'
    assert db.get_limit('123') == 200


def test_set_tier_back_to_basic():
    db.set_tier('123', 'premium')
    db.set_tier('123', 'basic')
    assert db.get_tier('123') == 'basic'


def test_set_invalid_tier_raises():
    with pytest.raises(ValueError):
        db.set_tier('123', 'enterprise')


def test_different_servers_independent():
    db.set_tier('aaa', 'pro')
    db.set_tier('bbb', 'premium')
    assert db.get_tier('aaa') == 'pro'
    assert db.get_tier('bbb') == 'premium'
    assert db.get_tier('ccc') == 'basic'


def test_all_server_tiers_empty_initially():
    assert db.all_server_tiers() == []


def test_all_server_tiers_after_sets():
    db.set_tier('111', 'pro')
    db.set_tier('222', 'premium')
    rows = {r['server_id']: r['tier'] for r in db.all_server_tiers()}
    assert rows == {'111': 'pro', '222': 'premium'}


def test_upsert_overwrites():
    db.set_tier('999', 'basic')
    db.set_tier('999', 'pro')
    db.set_tier('999', 'premium')
    assert db.get_tier('999') == 'premium'
    rows = db.all_server_tiers()
    assert len(rows) == 1


def test_tiers_dict_covers_all_valid_tiers():
    for t in ('basic', 'pro', 'premium'):
        assert t in db.TIERS
        assert isinstance(db.TIERS[t], int)
        assert db.TIERS[t] > 0
