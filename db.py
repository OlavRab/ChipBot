"""
Thin SQLite layer for server tier management.
Imported by both webapp.py and main.py.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get('DB_PATH', '/var/chips/chipbot.db')

TIERS: dict[str, int] = {
    'basic':   25,
    'pro':     50,
    'premium': 200,
}
DEFAULT_TIER = 'basic'


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS server_tiers (
                server_id TEXT PRIMARY KEY,
                tier      TEXT NOT NULL DEFAULT 'basic'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sound_plays (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at   TEXT NOT NULL,
                server_id   TEXT NOT NULL,
                server_name TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                username    TEXT NOT NULL,
                sound_name  TEXT NOT NULL
            )
        ''')


def get_tier(server_id: str) -> str:
    with _conn() as conn:
        row = conn.execute(
            'SELECT tier FROM server_tiers WHERE server_id = ?', (server_id,)
        ).fetchone()
        return row['tier'] if row else DEFAULT_TIER


def set_tier(server_id: str, tier: str) -> None:
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier!r}. Valid tiers: {list(TIERS)}")
    with _conn() as conn:
        conn.execute('''
            INSERT INTO server_tiers (server_id, tier) VALUES (?, ?)
            ON CONFLICT(server_id) DO UPDATE SET tier = excluded.tier
        ''', (server_id, tier))


def get_limit(server_id: str) -> int:
    return TIERS[get_tier(server_id)]


def log_play(server_id: str, server_name: str, user_id: str, username: str, sound_name: str) -> None:
    import datetime
    with _conn() as conn:
        conn.execute(
            'INSERT INTO sound_plays (played_at, server_id, server_name, user_id, username, sound_name) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (datetime.datetime.utcnow().isoformat(timespec='seconds'), server_id, server_name, user_id, username, sound_name),
        )


def recent_plays(limit: int = 200) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            'SELECT * FROM sound_plays ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def all_server_tiers() -> list[dict]:
    """Return all rows that have a tier explicitly set."""
    with _conn() as conn:
        rows = conn.execute('SELECT server_id, tier FROM server_tiers ORDER BY server_id').fetchall()
        return [dict(r) for r in rows]
