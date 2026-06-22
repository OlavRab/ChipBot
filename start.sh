#!/bin/bash
set -e

# Web upload site — Railway exposes $PORT externally
gunicorn webapp:app --bind 0.0.0.0:${PORT:-5000} --workers 2 &
GUNICORN_PID=$!

# Discord bot
python main.py &
BOT_PID=$!

# On SIGTERM (Railway shutdown), kill both child processes cleanly
trap "kill $GUNICORN_PID $BOT_PID 2>/dev/null; wait" SIGTERM SIGINT

wait $BOT_PID
