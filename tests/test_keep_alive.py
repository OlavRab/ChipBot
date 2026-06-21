"""Tests for the keep_alive Flask endpoints."""
import os
import tempfile

import pytest

os.environ.setdefault('LOG_TOKEN', 'supersecret')
os.environ.setdefault('FLASK_HOST', '127.0.0.1')
os.environ.setdefault('FLASK_PORT', '8081')

from keep_alive import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# / health check
# ---------------------------------------------------------------------------

def test_home_returns_alive(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Alive' in resp.data


# ---------------------------------------------------------------------------
# /log — token auth
# ---------------------------------------------------------------------------

def test_log_without_token_returns_403(client):
    resp = client.get('/log')
    assert resp.status_code == 403


def test_log_with_wrong_token_returns_403(client):
    resp = client.get('/log?token=wrongtoken')
    assert resp.status_code == 403


def test_log_with_correct_token_and_missing_file_returns_404(client):
    resp = client.get('/log?token=supersecret')
    assert resp.status_code == 404


def test_log_with_correct_token_returns_file(client, tmp_path):
    csv_file = tmp_path / 'soundboard.csv'
    csv_file.write_text('date,time,server\n2024-01-01,12:00:00,123\n')
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        resp = client.get('/log?token=supersecret')
        assert resp.status_code == 200
        assert b'2024-01-01' in resp.data
    finally:
        os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# _authorized helper
# ---------------------------------------------------------------------------

def test_authorized_returns_false_with_no_token(monkeypatch):
    monkeypatch.setenv('LOG_TOKEN', '')
    import keep_alive as ka
    # Reload the module to pick up the new env var
    import importlib
    importlib.reload(ka)
    with app.test_request_context('/log'):
        assert not ka._authorized()


def test_authorized_returns_true_with_correct_token(monkeypatch):
    import keep_alive as ka
    ka._LOG_TOKEN = 'supersecret'
    with app.test_request_context('/log?token=supersecret'):
        assert ka._authorized()


def test_authorized_returns_false_with_wrong_token(monkeypatch):
    import keep_alive as ka
    ka._LOG_TOKEN = 'supersecret'
    with app.test_request_context('/log?token=notright'):
        assert not ka._authorized()
