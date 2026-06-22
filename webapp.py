"""
ChipBot upload site — Flask web app with Discord OAuth.

Env vars required:
  DISCORD_CLIENT_ID      — from Discord Developer Portal
  DISCORD_CLIENT_SECRET  — from Discord Developer Portal
  DISCORD_REDIRECT_URI   — e.g. https://yoursite.com/auth/callback
  SECRET_KEY             — random secret for Flask sessions
  SOUNDS_BASE            — path to sounds directory (default /var/chips)
  WEB_PORT               — port to listen on (default 5000)
"""

import os
import re
import secrets
from functools import wraps
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, redirect, render_template,
    request, send_file, session, url_for,
)
import db as _db

load_dotenv('keys.env')

app = Flask(__name__)
_db.init_db()
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

SOUNDS_BASE = os.environ.get('SOUNDS_BASE', '/var/chips')
MAX_BYTES = 400 * 1024  # 400 KB

REVOLUT_PRO_LINK = os.environ.get('REVOLUT_PRO_LINK', '')
REVOLUT_PREMIUM_LINK = os.environ.get('REVOLUT_PREMIUM_LINK', '')

DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '')
DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', '')
DISCORD_API = 'https://discord.com/api/v10'
DISCORD_AUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_sound_path(server_id: str, name: str) -> Optional[str]:
    """Return absolute path or None if the name is unsafe."""
    if not re.match(r'^[\w\-]+$', name):
        return None
    server_dir = os.path.realpath(os.path.join(SOUNDS_BASE, server_id))
    target = os.path.realpath(os.path.join(server_dir, name + '.mp3'))
    if not target.startswith(server_dir + os.sep):
        return None
    return target


def _is_mp3(data: bytes) -> bool:
    """Basic magic-byte check — rejects files that are clearly not MP3."""
    return data[:3] == b'ID3' or (len(data) >= 2 and data[0] == 0xFF and data[1] in (0xE0, 0xE3, 0xF2, 0xF3, 0xFB))


def _list_sounds(server_id: str) -> list[str]:
    server_dir = os.path.join(SOUNDS_BASE, server_id)
    if not os.path.isdir(server_dir):
        return []
    return sorted(f[:-4] for f in os.listdir(server_dir) if f.endswith('.mp3'))


def _discord_get(path: str) -> dict:
    """GET from Discord API using the session's access token."""
    resp = requests.get(
        f"{DISCORD_API}{path}",
        headers={"Authorization": f"Bearer {session['access_token']}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# CSRF — simple token in session, checked on every state-changing POST
# ---------------------------------------------------------------------------

def _csrf_token() -> str:
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(16)
    return session['csrf']


def _check_csrf():
    if request.form.get('csrf') != session.get('csrf'):
        abort(403)


app.jinja_env.globals['csrf_token'] = _csrf_token


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            session['next'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def guild_member_required(f):
    """Verify the logged-in user is a member of the requested server."""
    @wraps(f)
    def wrapper(server_id: str, *args, **kwargs):
        guilds = session.get('guilds', {})
        if server_id not in guilds:
            # Re-fetch guild list in case it changed
            try:
                raw = _discord_get('/users/@me/guilds')
                guilds = {g['id']: g for g in raw}
                session['guilds'] = guilds
            except requests.RequestException:
                abort(503)
        if server_id not in guilds:
            abort(403)
        return f(server_id, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# OAuth routes
# ---------------------------------------------------------------------------

@app.route('/auth/login')
def login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds',
        'state': state,
    }
    return redirect(f"{DISCORD_AUTH_URL}?{urlencode(params)}")


@app.route('/auth/callback')
def callback():
    session_state = session.pop('oauth_state', None)
    if not session_state or request.args.get('state') != session_state:
        abort(403)
    code = request.args.get('code')
    if not code:
        abort(400)

    # Exchange code for token
    token_resp = requests.post(DISCORD_TOKEN_URL, data={
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
    }, timeout=10)
    if not token_resp.ok:
        abort(400)
    token_data = token_resp.json()
    session['access_token'] = token_data['access_token']

    # Fetch user profile and guild list
    user = _discord_get('/users/@me')
    guilds_raw = _discord_get('/users/@me/guilds')

    session['user'] = {
        'id': user['id'],
        'username': user['username'],
        'avatar': user.get('avatar'),
    }
    session['guilds'] = {g['id']: g for g in guilds_raw}

    next_url = session.pop('next', url_for('index'))
    return redirect(next_url)


@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Main pages
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user' not in session:
        return render_template('index.html', user=None)

    guilds = session.get('guilds', {})
    # Annotate each guild with its sound count
    server_list = []
    for gid, g in guilds.items():
        count = len(_list_sounds(gid))
        server_list.append({
            'id': gid,
            'name': g['name'],
            'icon': g.get('icon'),
            'count': count,
            'limit': _db.get_limit(gid),
            'tier': _db.get_tier(gid),
        })
    server_list.sort(key=lambda g: (-g['count'], g['name']))
    return render_template('index.html', user=session['user'], servers=server_list)


@app.route('/server/<server_id>')
@login_required
@guild_member_required
def server(server_id: str):
    guild = session['guilds'][server_id]
    sounds = _list_sounds(server_id)
    tier = _db.get_tier(server_id)
    limit = _db.TIERS[tier]
    return render_template(
        'server.html',
        guild=guild, server_id=server_id, sounds=sounds, user=session['user'],
        tier=tier, limit=limit,
    )


@app.route('/server/<server_id>/upload', methods=['POST'])
@login_required
@guild_member_required
def upload(server_id: str):
    _check_csrf()
    sound_name = request.form.get('name', '').strip().lower()
    file = request.files.get('file')

    if not sound_name:
        flash('Sound name is required.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    if not re.match(r'^[\w\-]+$', sound_name):
        flash('Sound name may only contain letters, numbers, dashes, and underscores.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    if not file or file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    current_count = len(_list_sounds(server_id))
    limit = _db.get_limit(server_id)
    if current_count >= limit:
        tier = _db.get_tier(server_id)
        flash(
            f'Sound limit reached ({current_count}/{limit} — {tier.capitalize()} tier). '
            'Upgrade your server to add more sounds.',
            'danger',
        )
        return redirect(url_for('server', server_id=server_id))

    data = file.read()

    if len(data) > MAX_BYTES:
        flash(f'File is too large. Maximum size is {MAX_BYTES // 1024} KB.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    if not _is_mp3(data):
        flash('Only .mp3 files are accepted.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    path = _safe_sound_path(server_id, sound_name)
    if path is None:
        flash('Invalid sound name.', 'danger')
        return redirect(url_for('server', server_id=server_id))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)

    flash(f'"{sound_name}" uploaded successfully! Use /sound {sound_name} in Discord.', 'success')
    return redirect(url_for('server', server_id=server_id))


@app.route('/server/<server_id>/delete/<sound_name>', methods=['POST'])
@login_required
@guild_member_required
def delete(server_id: str, sound_name: str):
    _check_csrf()
    path = _safe_sound_path(server_id, sound_name)
    if path is None or not os.path.isfile(path):
        flash('Sound not found.', 'danger')
        return redirect(url_for('server', server_id=server_id))
    os.remove(path)
    flash(f'"{sound_name}" has been deleted.', 'success')
    return redirect(url_for('server', server_id=server_id))


@app.route('/admin')
@login_required
def admin_panel():
    if session['user']['id'] != os.environ.get('ADMIN_ID', ''):
        abort(403)
    guilds = session.get('guilds', {})
    tier_rows = {r['server_id']: r['tier'] for r in _db.all_server_tiers()}
    servers = []
    for gid, g in guilds.items():
        servers.append({
            'id': gid,
            'name': g['name'],
            'tier': tier_rows.get(gid, _db.DEFAULT_TIER),
            'count': len(_list_sounds(gid)),
            'limit': _db.get_limit(gid),
        })
    servers.sort(key=lambda s: s['name'])
    return render_template('admin.html', servers=servers, tiers=list(_db.TIERS), user=session['user'])


@app.route('/admin/set-tier', methods=['POST'])
@login_required
def admin_set_tier():
    if session['user']['id'] != os.environ.get('ADMIN_ID', ''):
        abort(403)
    _check_csrf()
    server_id = request.form.get('server_id', '').strip()
    tier = request.form.get('tier', '').strip()
    if not server_id or tier not in _db.TIERS:
        flash('Invalid server or tier.', 'danger')
    else:
        _db.set_tier(server_id, tier)
        flash(f'Server {server_id} set to {tier.capitalize()} tier.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/server/<server_id>/upgrade')
@login_required
@guild_member_required
def upgrade(server_id: str):
    guild = session['guilds'][server_id]
    tier = _db.get_tier(server_id)
    return render_template(
        'upgrade.html',
        guild=guild,
        server_id=server_id,
        user=session['user'],
        tier=tier,
        pro_link=REVOLUT_PRO_LINK,
        premium_link=REVOLUT_PREMIUM_LINK,
    )


@app.route('/server/<server_id>/audio/<sound_name>')
@login_required
@guild_member_required
def audio(server_id: str, sound_name: str):
    """Serve a sound file for in-browser preview."""
    path = _safe_sound_path(server_id, sound_name)
    if path is None or not os.path.isfile(path):
        abort(404)
    return send_file(path, mimetype='audio/mpeg')


# ---------------------------------------------------------------------------
# Test helpers — only active when TEST_MODE=1 and TEST_SECRET is set
# ---------------------------------------------------------------------------

_TEST_MODE = os.environ.get('TEST_MODE', '') == '1'
_TEST_SECRET = os.environ.get('TEST_SECRET', '')


@app.route('/test/login', methods=['POST'])
def test_login():
    """Create a test session. Requires TEST_MODE=1 and correct TEST_SECRET header."""
    if not _TEST_MODE or not _TEST_SECRET:
        abort(404)
    if request.headers.get('X-Test-Secret') != _TEST_SECRET:
        abort(403)
    data = request.get_json(force=True) or {}
    server_id = data.get('server_id', 'test_server')
    session['user'] = {'id': 'test_user', 'username': 'TestUser', 'avatar': None}
    session['guilds'] = {server_id: {'id': server_id, 'name': 'Test Server', 'icon': None}}
    session['csrf'] = 'test-csrf-token'
    return {'ok': True, 'csrf': 'test-csrf-token'}


@app.route('/test/cleanup/<server_id>/<sound_name>', methods=['POST'])
def test_cleanup(server_id: str, sound_name: str):
    """Delete a test sound. Requires TEST_MODE=1 and correct TEST_SECRET header."""
    if not _TEST_MODE or not _TEST_SECRET:
        abort(404)
    if request.headers.get('X-Test-Secret') != _TEST_SECRET:
        abort(403)
    path = _safe_sound_path(server_id, sound_name)
    if path and os.path.isfile(path):
        os.remove(path)
    return {'ok': True}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('WEB_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
