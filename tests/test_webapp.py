"""Tests for webapp.py — upload site routes and helpers."""
import io
import os
import sys
from unittest.mock import patch

import pytest

os.environ.setdefault('DISCORD_CLIENT_ID', 'test_client_id')
os.environ.setdefault('DISCORD_CLIENT_SECRET', 'test_secret')
os.environ.setdefault('DISCORD_REDIRECT_URI', 'http://localhost/auth/callback')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('SOUNDS_BASE', '/tmp/chipbot_test_sounds')

# Mock load_dotenv to prevent it from trying to load keys.env during import
with patch('dotenv.load_dotenv'):
    from webapp import app, _safe_sound_path, _is_mp3, _list_sounds

SOUNDS_BASE = os.environ['SOUNDS_BASE']
SERVER_ID = '123456789'


@pytest.fixture(autouse=True)
def clean_sounds(tmp_path, monkeypatch):
    """Redirect SOUNDS_BASE to a temp dir and clean up after each test."""
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(tmp_path))
    yield tmp_path


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def logged_in_client(client):
    """A client with a faked session (logged-in user, member of SERVER_ID)."""
    with client.session_transaction() as sess:
        sess['user'] = {'id': '999', 'username': 'TestUser', 'avatar': None}
        sess['access_token'] = 'fake_token'
        sess['guilds'] = {
            SERVER_ID: {'id': SERVER_ID, 'name': 'Test Server', 'icon': None}
        }
        sess['csrf'] = 'testcsrf'
    return client


# ---------------------------------------------------------------------------
# _safe_sound_path
# ---------------------------------------------------------------------------

def test_safe_sound_path_valid(tmp_path, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(tmp_path))
    result = _safe_sound_path(SERVER_ID, 'hello')
    assert result is not None
    assert result.endswith('hello.mp3')


def test_safe_sound_path_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(tmp_path))
    assert _safe_sound_path(SERVER_ID, '../../etc/passwd') is None


def test_safe_sound_path_slash_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(tmp_path))
    assert _safe_sound_path(SERVER_ID, 'foo/bar') is None


def test_safe_sound_path_special_chars_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(tmp_path))
    for bad in ['a;b', 'a b', 'a"b', 'a`b']:
        assert _safe_sound_path(SERVER_ID, bad) is None


# ---------------------------------------------------------------------------
# _is_mp3
# ---------------------------------------------------------------------------

def test_is_mp3_id3_header():
    assert _is_mp3(b'ID3\x03\x00\x00')


def test_is_mp3_sync_word():
    assert _is_mp3(b'\xff\xfb\x90\x00')


def test_is_mp3_rejects_wav():
    assert not _is_mp3(b'RIFF\x00\x00\x00\x00WAVE')


def test_is_mp3_rejects_ogg():
    assert not _is_mp3(b'OggS\x00')


def test_is_mp3_rejects_empty():
    assert not _is_mp3(b'')


# ---------------------------------------------------------------------------
# Routes — unauthenticated
# ---------------------------------------------------------------------------

def test_index_logged_out(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Login with Discord' in resp.data


def test_server_redirects_when_logged_out(client):
    resp = client.get(f'/server/{SERVER_ID}')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_upload_redirects_when_logged_out(client):
    resp = client.post(f'/server/{SERVER_ID}/upload', data={})
    assert resp.status_code == 302


def test_delete_redirects_when_logged_out(client):
    resp = client.post(f'/server/{SERVER_ID}/delete/mysound', data={})
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Routes — authenticated
# ---------------------------------------------------------------------------

def test_index_logged_in_shows_servers(logged_in_client):
    resp = logged_in_client.get('/')
    assert resp.status_code == 200
    assert b'Test Server' in resp.data


def test_server_page_renders(logged_in_client, clean_sounds):
    resp = logged_in_client.get(f'/server/{SERVER_ID}')
    assert resp.status_code == 200
    assert b'Upload a Sound' in resp.data


def test_server_page_lists_sounds(logged_in_client, clean_sounds):
    server_dir = clean_sounds / SERVER_ID
    server_dir.mkdir()
    (server_dir / 'airhorn.mp3').write_bytes(b'ID3\x00')
    resp = logged_in_client.get(f'/server/{SERVER_ID}')
    assert b'airhorn' in resp.data


def test_upload_valid_mp3(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    mp3_bytes = b'ID3\x03\x00\x00' + b'\x00' * 100
    data = {
        'name': 'testclip',
        'file': (io.BytesIO(mp3_bytes), 'clip.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
    )
    assert resp.status_code == 302
    assert (clean_sounds / SERVER_ID / 'testclip.mp3').exists()


def test_upload_rejects_oversized_file(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    big = b'ID3\x03\x00\x00' + b'\x00' * (401 * 1024)
    data = {
        'name': 'toobig',
        'file': (io.BytesIO(big), 'big.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert b'too large' in resp.data
    assert not (clean_sounds / SERVER_ID / 'toobig.mp3').exists()


def test_upload_rejects_non_mp3(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    data = {
        'name': 'fakeclip',
        'file': (io.BytesIO(b'RIFF\x00\x00\x00\x00WAVE'), 'fake.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert b'Only .mp3' in resp.data
    assert not (clean_sounds / SERVER_ID / 'fakeclip.mp3').exists()


def test_upload_rejects_invalid_name(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    data = {
        'name': '../../etc/passwd',
        'file': (io.BytesIO(b'ID3\x03\x00\x00'), 'x.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert b'Sound name may only contain' in resp.data or b'Invalid' in resp.data


def test_delete_existing_sound(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    server_dir = clean_sounds / SERVER_ID
    server_dir.mkdir()
    sound_file = server_dir / 'boom.mp3'
    sound_file.write_bytes(b'ID3\x00')
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/delete/boom',
        data={'csrf': 'testcsrf'},
    )
    assert resp.status_code == 302
    assert not sound_file.exists()


def test_delete_nonexistent_sound(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/delete/ghost',
        data={'csrf': 'testcsrf'},
        follow_redirects=True,
    )
    assert b'not found' in resp.data.lower()


def test_audio_serves_file(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    server_dir = clean_sounds / SERVER_ID
    server_dir.mkdir()
    (server_dir / 'jingle.mp3').write_bytes(b'ID3\x03\x00\x00' + b'\x00' * 50)
    resp = logged_in_client.get(f'/server/{SERVER_ID}/audio/jingle')
    assert resp.status_code == 200
    assert resp.content_type == 'audio/mpeg'


def test_audio_404_for_missing(logged_in_client, clean_sounds, monkeypatch):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    resp = logged_in_client.get(f'/server/{SERVER_ID}/audio/missing')
    assert resp.status_code == 404


def test_non_member_cannot_access_server(client):
    with client.session_transaction() as sess:
        sess['user'] = {'id': '999', 'username': 'TestUser', 'avatar': None}
        sess['access_token'] = 'fake_token'
        sess['guilds'] = {}  # not a member of any server
        sess['csrf'] = 'testcsrf'
    resp = client.get(f'/server/{SERVER_ID}')
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tier / upload-limit tests
# ---------------------------------------------------------------------------

import db


@pytest.fixture(autouse=False)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr('db.DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    yield


def test_server_page_shows_tier_and_limit(logged_in_client, clean_sounds, isolated_db):
    resp = logged_in_client.get(f'/server/{SERVER_ID}')
    assert resp.status_code == 200
    assert b'Basic' in resp.data
    assert b'25' in resp.data  # default limit


def test_upload_blocked_at_basic_limit(logged_in_client, clean_sounds, monkeypatch, isolated_db):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    server_dir = clean_sounds / SERVER_ID
    server_dir.mkdir()
    # Fill up to the basic limit (25)
    for i in range(25):
        (server_dir / f'sound{i}.mp3').write_bytes(b'ID3\x00')

    mp3 = b'ID3\x03\x00\x00' + b'\x00' * 100
    data = {
        'name': 'one_too_many',
        'file': (io.BytesIO(mp3), 'x.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert b'limit reached' in resp.data.lower()
    assert not (server_dir / 'one_too_many.mp3').exists()


def test_upload_allowed_after_tier_upgrade(logged_in_client, clean_sounds, monkeypatch, isolated_db):
    monkeypatch.setattr('webapp.SOUNDS_BASE', str(clean_sounds))
    server_dir = clean_sounds / SERVER_ID
    server_dir.mkdir()
    # Fill to basic limit
    for i in range(25):
        (server_dir / f'sound{i}.mp3').write_bytes(b'ID3\x00')

    # Upgrade to pro
    db.set_tier(SERVER_ID, 'pro')

    mp3 = b'ID3\x03\x00\x00' + b'\x00' * 100
    data = {
        'name': 'extra_sound',
        'file': (io.BytesIO(mp3), 'x.mp3'),
        'csrf': 'testcsrf',
    }
    resp = logged_in_client.post(
        f'/server/{SERVER_ID}/upload',
        data=data,
        content_type='multipart/form-data',
    )
    assert resp.status_code == 302
    assert (server_dir / 'extra_sound.mp3').exists()
