"""
End-to-end tests against the live Railway deployment.

Requires env vars (or keys.env):
  E2E_BASE_URL  — base URL of the deployed app (default: https://chipbot-production.up.railway.app)
  TOKEN         — Discord bot token (to verify bot is online)
  LOG_TOKEN     — token for the /log endpoint
"""
import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv('keys.env')

BASE_URL = os.environ.get('E2E_BASE_URL', 'https://chipbot-production.up.railway.app').rstrip('/')
BOT_TOKEN = os.environ.get('TOKEN', '')
LOG_TOKEN = os.environ.get('LOG_TOKEN', '')

DISCORD_API = 'https://discord.com/api/v10'


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
