"""
End-to-end tests against the live Railway deployment.

Requires env vars (or keys.env):
  E2E_BASE_URL  — base URL of the deployed app (default: https://chipbot-production.up.railway.app)
  TOKEN         — Discord bot token (to verify bot is online)
  TEST_SECRET   — secret for test backdoor endpoints (requires TEST_MODE=1 on the server)
"""
import io
import os
import struct

import pytest
import requests
from dotenv import load_dotenv

load_dotenv('keys.env')

BASE_URL = os.environ.get('E2E_BASE_URL', 'https://chipbot-production.up.railway.app').rstrip('/')
BOT_TOKEN = os.environ.get('TOKEN', '')
TEST_SECRET = os.environ.get('TEST_SECRET', '')

DISCORD_API = 'https://discord.com/api/v10'
TEST_SERVER_ID = 'e2e_test_server'
TEST_SOUND_NAME = 'e2e_test_sound'


# ---------------------------------------------------------------------------
# Web app
# ---------------------------------------------------------------------------

def test_homepage_returns_200():
    r = requests.get(f'{BASE_URL}/', timeout=10)
    assert r.status_code == 200
    assert 'text/html' in r.headers.get('Content-Type', '')


def test_homepage_contains_chipbot():
    r = requests.get(f'{BASE_URL}/', timeout=10)
    assert 'ChipBot' in r.text


def test_login_redirects_to_discord():
    r = requests.get(f'{BASE_URL}/auth/login', timeout=10, allow_redirects=False)
    assert r.status_code == 302
    assert 'discord.com/api/oauth2/authorize' in r.headers.get('Location', '')


def test_callback_without_state_returns_403():
    # No session cookie → state mismatch → 403
    r = requests.get(f'{BASE_URL}/auth/callback?code=fake', timeout=10, cookies={})
    assert r.status_code == 403


def test_server_page_without_auth_redirects():
    r = requests.get(f'{BASE_URL}/server/123456789', timeout=10, allow_redirects=False)
    assert r.status_code in (302, 401)


def test_admin_page_without_auth_redirects():
    r = requests.get(f'{BASE_URL}/admin', timeout=10, allow_redirects=False)
    assert r.status_code in (302, 401)


def test_upload_without_auth_redirects():
    r = requests.post(f'{BASE_URL}/server/123456789/upload', timeout=10, allow_redirects=False)
    assert r.status_code in (302, 401)


# ---------------------------------------------------------------------------
# Discord bot online
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not BOT_TOKEN, reason='TOKEN not set')
def test_bot_is_online_and_authenticated():
    r = requests.get(
        f'{DISCORD_API}/users/@me',
        headers={'Authorization': f'Bot {BOT_TOKEN}'},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get('bot') is True


@pytest.mark.skipif(not BOT_TOKEN, reason='TOKEN not set')
def test_bot_username_is_chipbot():
    r = requests.get(
        f'{DISCORD_API}/users/@me',
        headers={'Authorization': f'Bot {BOT_TOKEN}'},
        timeout=10,
    )
    data = r.json()
    assert 'ChipBot' in data.get('username', '') or 'chip' in data.get('username', '').lower()


# ---------------------------------------------------------------------------
# Upload flow (requires TEST_MODE=1 + TEST_SECRET on the server)
# ---------------------------------------------------------------------------

def _minimal_mp3() -> bytes:
    """Return a minimal valid MP3 frame (ID3 header + one silent frame)."""
    # ID3v2 header: "ID3" + version 2.3 + flags + size (0)
    id3 = b'ID3\x03\x00\x00\x00\x00\x00\x00'
    # One valid MPEG1 Layer3 frame header (silence): sync + 0xFB + 0x90 + 0x00
    frame = b'\xff\xfb\x90\x00' + b'\x00' * 413
    return id3 + frame


@pytest.fixture(scope='module')
def test_session():
    """Create an authenticated test session and return (session, csrf_token)."""
    if not TEST_SECRET:
        pytest.skip('TEST_SECRET not set — test endpoints not available')
    s = requests.Session()
    r = s.post(
        f'{BASE_URL}/test/login',
        json={'server_id': TEST_SERVER_ID},
        headers={'X-Test-Secret': TEST_SECRET},
        timeout=10,
    )
    if r.status_code == 404:
        pytest.skip('TEST_MODE not enabled on server')
    assert r.status_code == 200, f'test/login failed: {r.status_code} {r.text}'
    csrf = r.json()['csrf']
    yield s, csrf
    # Cleanup: remove test sound if it exists
    s.post(
        f'{BASE_URL}/test/cleanup/{TEST_SERVER_ID}/{TEST_SOUND_NAME}',
        headers={'X-Test-Secret': TEST_SECRET},
        timeout=10,
    )


@pytest.mark.skipif(not TEST_SECRET, reason='TEST_SECRET not set')
def test_upload_sound(test_session):
    s, csrf = test_session
    mp3_data = _minimal_mp3()
    r = s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/upload',
        data={'name': TEST_SOUND_NAME, 'csrf': csrf},
        files={'file': (f'{TEST_SOUND_NAME}.mp3', io.BytesIO(mp3_data), 'audio/mpeg')},
        timeout=15,
        allow_redirects=True,
    )
    assert r.status_code == 200
    assert TEST_SOUND_NAME in r.text or 'uploaded successfully' in r.text.lower()


@pytest.mark.skipif(not TEST_SECRET, reason='TEST_SECRET not set')
def test_upload_rejects_oversized_file(test_session):
    s, csrf = test_session
    big_mp3 = b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'\x00' * (401 * 1024)
    r = s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/upload',
        data={'name': 'oversized_sound', 'csrf': csrf},
        files={'file': ('oversized.mp3', io.BytesIO(big_mp3), 'audio/mpeg')},
        timeout=15,
        allow_redirects=True,
    )
    assert r.status_code == 200
    assert 'too large' in r.text.lower() or 'Maximum size' in r.text


@pytest.mark.skipif(not TEST_SECRET, reason='TEST_SECRET not set')
def test_upload_rejects_non_mp3(test_session):
    s, csrf = test_session
    fake_file = b'This is not an MP3 file at all'
    r = s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/upload',
        data={'name': 'fake_sound', 'csrf': csrf},
        files={'file': ('fake.mp3', io.BytesIO(fake_file), 'audio/mpeg')},
        timeout=15,
        allow_redirects=True,
    )
    assert r.status_code == 200
    assert 'mp3' in r.text.lower() or 'accepted' in r.text.lower()


@pytest.mark.skipif(not TEST_SECRET, reason='TEST_SECRET not set')
def test_upload_rejects_invalid_sound_name(test_session):
    s, csrf = test_session
    mp3_data = _minimal_mp3()
    r = s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/upload',
        data={'name': '../evil/../name', 'csrf': csrf},
        files={'file': ('evil.mp3', io.BytesIO(mp3_data), 'audio/mpeg')},
        timeout=15,
        allow_redirects=True,
    )
    assert r.status_code == 200
    assert 'only contain' in r.text.lower() or 'invalid' in r.text.lower()


@pytest.mark.skipif(not TEST_SECRET, reason='TEST_SECRET not set')
def test_delete_sound(test_session):
    s, csrf = test_session
    # Upload first to ensure the sound exists
    mp3_data = _minimal_mp3()
    s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/upload',
        data={'name': TEST_SOUND_NAME, 'csrf': csrf},
        files={'file': (f'{TEST_SOUND_NAME}.mp3', io.BytesIO(mp3_data), 'audio/mpeg')},
        timeout=15,
    )
    r = s.post(
        f'{BASE_URL}/server/{TEST_SERVER_ID}/delete/{TEST_SOUND_NAME}',
        data={'csrf': csrf},
        timeout=10,
        allow_redirects=True,
    )
    assert r.status_code == 200
    assert TEST_SOUND_NAME not in r.text or 'deleted' in r.text.lower()
