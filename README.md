# ChipBot

A Discord soundboard bot. Upload custom `.mp3` clips to your server and play them in voice channels with a single slash command — with autocomplete.

![ChipBot](cover.png)

## Features

- **`/chip [name]`** — Play a chip in your current voice channel (with autocomplete)
- **`/chiplist`** — See all chips uploaded to your server
- **`/rmchip [name]`** — Delete a chip (requires Manage Server)
- **`/leave`** — Disconnect the bot from voice
- **Web upload interface** — Log in with Discord, pick your server, upload `.mp3` files up to 400 KB
- **Per-server tiers** — Basic (25), Pro (50), Premium (200) chips
- **Usage logging** — Play events stored in SQLite with stdout streaming

Bonus commands: `/ping`, `/serverinfo`, `/joke`, `/crypto`, `/space`

## Self-hosting

### Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) installed and on `PATH`
- A Discord application with a bot token ([Discord Developer Portal](https://discord.com/developers/applications))

### Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/OlavRab/ChipBot.git
   cd ChipBot
   ```

2. **Install dependencies**
   ```bash
   pip install poetry
   poetry install
   ```

3. **Configure environment**

   Copy `keys.env.example` to `keys.env` and fill in your values:
   ```bash
   cp keys.env.example keys.env
   ```

   | Variable | Description |
   |---|---|
   | `TOKEN` | Discord bot token |
   | `DISCORD_CLIENT_ID` | Discord application client ID |
   | `DISCORD_CLIENT_SECRET` | Discord OAuth client secret |
   | `DISCORD_REDIRECT_URI` | OAuth callback URL (e.g. `http://localhost:5000/auth/callback`) |
   | `SECRET_KEY` | Flask session secret (any random string) |
   | `UPLOAD_URL` | Public URL of the web interface |
   | `SOUNDS_BASE` | Directory to store uploaded `.mp3` files (default: `/var/chips`) |
   | `DB_PATH` | Path to the SQLite database (default: `/var/chips/chipbot.db`) |
   | `ADMIN_ID` | Your Discord user ID for admin commands |

4. **Run**
   ```bash
   bash start.sh
   ```

   This starts both the Discord bot (`main.py`) and the web upload interface (`webapp.py`) in a single process.

### Discord bot permissions

When inviting the bot, it needs:
- `bot` scope with: **Send Messages**, **Connect**, **Speak**, **Use Voice Activity**
- `applications.commands` scope for slash commands

## Deployment

ChipBot is designed to run on [Railway](https://railway.app). The `railpack.json` and `start.sh` handle the build and start command. Mount a persistent volume at `/var/chips` for sounds and the SQLite database to survive redeploys.

## Project structure

```
main.py       — Discord bot (slash commands, voice, logging)
webapp.py     — Flask web interface (upload, OAuth, tier management)
db.py         — SQLite layer (tiers, play event logging)
start.sh      — Entrypoint: runs bot + web server together
templates/    — Jinja2 HTML templates
static/       — CSS and assets
docs/         — Privacy policy and Terms of Service
```

## License

MIT
