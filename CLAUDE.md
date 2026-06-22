# ChipBot

Discord soundboard bot — plays custom .mp3 clips in voice channels, deployed on Railway.

## Stack
- Python 3.14, discord.py 2.x, Flask 3 (web dashboard + upload API)
- SQLite via `db.py` (thin wrapper, path: `/var/chips/chipbot.db`)
- Sound files stored at `SOUNDS_BASE` (env var, default `/var/chips`), organized as `<guild_id>/<name>.mp3`
- Deployed on Railway with Railpack; gunicorn serves Flask, discord.py runs in the same process
- Tests: pytest + pytest-asyncio

## Project layout
```
main.py       — Discord bot: slash commands, voice playback, sound management
webapp.py     — Flask app: web dashboard, sound upload/delete endpoints
db.py         — SQLite layer for server tier management
tests/        — pytest tests
docs/         — GitHub Pages landing page (privacy, ToS)
sounds_local/ — local sound files for dev/testing
```

## Key rules
- Sound files live under `SOUNDS_BASE/<guild_id>/<name>.mp3` — never assume a local path
- Tier limits (sounds per server): basic=25, pro=50, premium=200 — enforced in `db.py`
- Both `main.py` and `webapp.py` import `db` — keep that module side-effect-free
- Tests use `sounds_local/` fixtures; never touch Railway volume paths in tests

## Python best practices
- Use type hints on all function signatures
- Prefer `pathlib.Path` over `os.path` for new path manipulation; existing `os.path` calls in `safe_sound_path` are intentional (realpath traversal guard — do not refactor)
- Keep modules importable without side effects: no `client.run()`, no `load_dotenv()` at module level outside `if __name__ == "__main__"` guards where possible
- Do not use `global` state; pass config via parameters or environment variables
- Raise specific exceptions (`ValueError`, `PermissionError`) rather than returning `None` for logic errors — reserve `None` for "not found" cases
- Use `contextmanager` for resource cleanup (already done in `db.py` — follow that pattern)
- Dependencies: add via `poetry add <pkg>`; never edit `pyproject.toml` manually for deps

## Testing
- Run the suite: `pytest tests/ --ignore=tests/test_e2e.py -q` (e2e requires live Railway deployment)
- Test isolation: use `tmp_path` + `monkeypatch` to redirect `DB_PATH` and `SOUNDS_BASE` — never touch real paths
- Never import `discord`, `matplotlib`, or `dotenv` in tests directly — stub with `sys.modules` as shown in `test_safe_sound_path.py`
- Use a real SQLite temp DB in `db` tests (not mocks) — `db.init_db()` on a `tmp_path` file
- E2e tests (`test_e2e.py`) require `E2E_BASE_URL`, `TOKEN`, and `TEST_SECRET` env vars; skip locally

## Railway setup
Project: **ChipBot** — link your local clone once after cloning:
```bash
railway link 630345ad-d94a-4f68-afe0-b9573ca4948a
railway service 73509f03-7f77-4499-a592-d8a442209113
```
Environment: `production`. After linking, `railway logs` and `railway up` will target the right service.

For the Railway MCP server, set `RAILWAY_TOKEN` in your shell profile — generate one at Railway → Account Settings → Tokens.

## Running locally
```bash
source venv/bin/activate
python main.py          # Discord bot
python webapp.py        # Flask dashboard (separate process)
pytest                  # test suite
```

## Spec-driven development (OpenSpec)
Feature specs and change proposals live in `openspec/`:
- `openspec/specs/` — per-feature specs (why, not just what)
- `openspec/changes/` — change proposals with design + tasks

Slash commands available in Claude Code:
- `/opsx:propose "description"` — start a new change proposal
- `/opsx:apply` — implement an approved proposal task by task
- `/opsx:archive` — archive a completed change
- `/opsx:verify` — verify a change is complete
