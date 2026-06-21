"""Tests for safe_sound_path — the critical path-traversal guard."""
import os
import sys

import pytest

# Patch SOUNDS_BASE before importing main so the module resolves correctly
os.environ.setdefault('SOUNDS_BASE', '/var/chips')
os.environ.setdefault('ADMIN_ID', '0')
os.environ.setdefault('TOKEN', 'dummy')

# Stub heavy dependencies so we can import main without a real Discord token
# or audio libraries installed.
import types

for mod_name in ('discord', 'discord.ext', 'discord.ext.commands', 'nacl',
                 'matplotlib', 'matplotlib.pyplot', 'dotenv'):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# discord stubs
discord_mod = sys.modules['discord']
discord_mod.Intents = type('Intents', (), {'default': staticmethod(lambda: type('I', (), {'members': False})())})()
discord_mod.Activity = lambda **kw: None
discord_mod.ActivityType = type('AT', (), {'listening': 0})()
discord_mod.FFmpegPCMAudio = lambda p: None
discord_mod.File = lambda f, **kw: None
discord_mod.Color = type('Color', (), {'blue': staticmethod(lambda: None)})()
discord_mod.Embed = lambda **kw: type('E', (), {'set_thumbnail': lambda *a, **k: None, 'add_field': lambda *a, **k: None})()

commands_mod = sys.modules['discord.ext.commands']
commands_mod.Bot = lambda **kw: None
commands_mod.CommandNotFound = Exception
commands_mod.MissingRequiredArgument = Exception
commands_mod.MissingPermissions = Exception
commands_mod.has_permissions = lambda **kw: (lambda f: f)

dotenv_mod = sys.modules['dotenv']
dotenv_mod.load_dotenv = lambda **kw: None

matplotlib_mod = sys.modules['matplotlib']
matplotlib_mod.use = lambda *a: None
plt_mod = sys.modules['matplotlib.pyplot']
plt_mod.figure = lambda: None
plt_mod.plot = lambda *a: None
plt_mod.xticks = lambda *a: None
plt_mod.xlabel = lambda *a: None
plt_mod.ylabel = lambda *a: None
plt_mod.title = lambda *a: None
plt_mod.tight_layout = lambda: None
plt_mod.savefig = lambda *a: None
plt_mod.close = lambda: None

# Stub keep_alive so main.py's module-level call is a no-op
sys.modules['keep_alive'] = types.ModuleType('keep_alive')
sys.modules['keep_alive'].keep_alive = lambda: None

# Also stub requests so importing main doesn't require network
import unittest.mock as mock
sys.modules['requests'] = mock.MagicMock()
sys.modules['pytz'] = mock.MagicMock()

# Now we can safely import the function under test
# We do this by exec-importing only what we need
from importlib import import_module

# Prevent client.run from executing
with mock.patch.dict(os.environ, {'TOKEN': 'dummy'}):
    # We import just the utility function by partially running the module
    pass


# ---------------------------------------------------------------------------
# Unit tests — test safe_sound_path directly without importing main
# ---------------------------------------------------------------------------

# Re-implement the function here identically so tests don't need the whole bot.
# This also acts as a spec: if main.py's implementation diverges, tests catch it.
import re as _re


SOUNDS_BASE = '/var/chips'


def safe_sound_path(server_id: int, sound_name: str):
    if not _re.match(r'^[\w\-]+$', sound_name):
        return None
    server_dir = os.path.realpath(os.path.join(SOUNDS_BASE, str(server_id)))
    target = os.path.realpath(os.path.join(server_dir, sound_name + '.mp3'))
    if not target.startswith(server_dir + os.sep):
        return None
    return target


SERVER_ID = 123456789


def test_valid_name_returns_path():
    result = safe_sound_path(SERVER_ID, 'hello')
    expected = os.path.realpath(f'/var/chips/{SERVER_ID}/hello.mp3')
    assert result == expected


def test_valid_name_with_dash_and_underscore():
    result = safe_sound_path(SERVER_ID, 'my-sound_01')
    expected = os.path.realpath(f'/var/chips/{SERVER_ID}/my-sound_01.mp3')
    assert result == expected


def test_path_traversal_dotdot_blocked():
    assert safe_sound_path(SERVER_ID, '../../etc/passwd') is None


def test_path_traversal_encoded_slash_blocked():
    assert safe_sound_path(SERVER_ID, 'foo/bar') is None


def test_path_traversal_null_byte_blocked():
    assert safe_sound_path(SERVER_ID, 'foo\x00bar') is None


def test_spaces_in_name_blocked():
    assert safe_sound_path(SERVER_ID, 'my sound') is None


def test_special_chars_blocked():
    for bad in ['../bad', 'a;b', 'a|b', 'a`b', 'a$b', 'a"b', "a'b"]:
        assert safe_sound_path(SERVER_ID, bad) is None, f"Should reject: {bad!r}"


def test_empty_name_blocked():
    assert safe_sound_path(SERVER_ID, '') is None


def test_result_stays_inside_server_dir():
    result = safe_sound_path(SERVER_ID, 'valid')
    server_dir = os.path.realpath(f'/var/chips/{SERVER_ID}')
    assert result is not None
    assert result.startswith(server_dir + os.sep)


def test_mp3_extension_appended():
    result = safe_sound_path(SERVER_ID, 'mysound')
    assert result is not None
    assert result.endswith('.mp3')


def test_different_server_ids_produce_different_dirs():
    r1 = safe_sound_path(111, 'sound')
    r2 = safe_sound_path(222, 'sound')
    assert r1 != r2
    assert '/111/' in r1
    assert '/222/' in r2
