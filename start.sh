#!/bin/bash
set -e

# Web upload site — Railway exposes $PORT externally
gunicorn webapp:app --bind 0.0.0.0:${PORT:-5000} --workers 2 &

# Discord bot — keep_alive uses an internal port, not exposed
FLASK_PORT=8081 python main.py
