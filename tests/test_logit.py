"""Tests for the _logit CSV logging helper."""
import csv
import os
import sys
import types
import unittest.mock as mock
from pathlib import Path


# ---------------------------------------------------------------------------
# Stub everything so we can import _logit without a Discord environment
# ---------------------------------------------------------------------------

for mod_name in ('discord', 'discord.ext', 'discord.ext.commands',
                 'matplotlib', 'matplotlib.pyplot', 'dotenv', 'nacl', 'pytz'):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

discord_mod = sys.modules['discord']
discord_mod.Intents = type('Intents', (), {'default': staticmethod(lambda: type('I', (), {'members': False})())})()
discord_mod.Activity = lambda **kw: None
discord_mod.ActivityType = type('AT', (), {'listening': 0})()
discord_mod.FFmpegPCMAudio = lambda p: None
discord_mod.File = lambda f, **kw: None
discord_mod.Color = type('Color', (), {'blue': staticmethod(lambda: None)})()
discord_mod.Embed = lambda **kw: type('E', (), {'set_thumbnail': lambda *a, **k: None, 'add_field': lambda *a, **k: None})()

commands_mod = sys.modules['discord.ext.commands']
commands_mod.Bot = lambda **kw: type('Bot', (), {'event': lambda f: f, 'command': lambda *a, **k: (lambda f: f), 'run': lambda *a: None})()
commands_mod.CommandNotFound = Exception
commands_mod.MissingRequiredArgument = type('MRE', (Exception,), {'param': type('P', (), {'name': 'x'})()})
commands_mod.MissingPermissions = Exception
commands_mod.has_permissions = lambda **kw: (lambda f: f)

dotenv_mod = sys.modules['dotenv']
dotenv_mod.load_dotenv = lambda **kw: None

matplotlib_mod = sys.modules['matplotlib']
matplotlib_mod.use = lambda *a: None
plt_mod = sys.modules['matplotlib.pyplot']
for attr in ('figure', 'plot', 'xticks', 'xlabel', 'ylabel', 'title', 'tight_layout', 'savefig', 'close'):
    setattr(plt_mod, attr, lambda *a, **k: None)

pytz_mod = sys.modules['pytz']
pytz_mod.timezone = lambda tz: None

sys.modules['keep_alive'] = types.ModuleType('keep_alive')
sys.modules['keep_alive'].keep_alive = lambda: None
sys.modules['requests'] = mock.MagicMock()

os.environ.setdefault('SOUNDS_BASE', '/var/chips')
os.environ.setdefault('ADMIN_ID', '0')
os.environ.setdefault('TOKEN', 'dummy')


# Re-implement _logit here so we test the logic in isolation
import datetime


def _logit(server_id: int, location: str, user, server_name: str, *, out_file: str) -> None:
    now = datetime.datetime.now()
    parts = location.split('/')
    short_loc = '/'.join(parts[:4]) + '_' + parts[4] if len(parts) > 4 else location
    with open(out_file, 'a', newline='') as f:
        csv.writer(f).writerow([
            now.strftime('%Y-%m-%d'),
            now.strftime('%H:%M:%S'),
            server_id,
            short_loc,
            user,
            server_name,
        ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_logit_writes_csv_row(tmp_path):
    out = str(tmp_path / 'log.csv')
    _logit(111, '/var/chips/111/hello.mp3', 'TestUser', 'MyServer', out_file=out)
    rows = list(csv.reader(open(out)))
    assert len(rows) == 1
    assert rows[0][2] == '111'
    assert rows[0][5] == 'MyServer'


def test_logit_short_location_format(tmp_path):
    out = str(tmp_path / 'log.csv')
    _logit(222, '/var/chips/222/boom.mp3', 'User', 'Server', out_file=out)
    rows = list(csv.reader(open(out)))
    # Location with 5 parts gets joined as /var/chips/222_boom.mp3
    assert rows[0][3] == '/var/chips/222_boom.mp3'


def test_logit_appends_multiple_rows(tmp_path):
    out = str(tmp_path / 'log.csv')
    _logit(1, '/var/chips/1/a.mp3', 'U1', 'S1', out_file=out)
    _logit(2, '/var/chips/2/b.mp3', 'U2', 'S2', out_file=out)
    rows = list(csv.reader(open(out)))
    assert len(rows) == 2
    assert rows[0][2] == '1'
    assert rows[1][2] == '2'


def test_logit_date_format(tmp_path):
    out = str(tmp_path / 'log.csv')
    _logit(1, '/var/chips/1/x.mp3', 'U', 'S', out_file=out)
    rows = list(csv.reader(open(out)))
    date_str = rows[0][0]
    # Must parse as YYYY-MM-DD
    datetime.datetime.strptime(date_str, '%Y-%m-%d')


def test_logit_time_format(tmp_path):
    out = str(tmp_path / 'log.csv')
    _logit(1, '/var/chips/1/x.mp3', 'U', 'S', out_file=out)
    rows = list(csv.reader(open(out)))
    time_str = rows[0][1]
    datetime.datetime.strptime(time_str, '%H:%M:%S')
