import os
from threading import Thread

from flask import Flask, abort, send_file, request

app = Flask('')

# Token-based auth replaces the old IP-based check (IP was spoofable via X-Forwarded-For)
_LOG_TOKEN = os.environ.get('LOG_TOKEN', '')


def _authorized() -> bool:
    return bool(_LOG_TOKEN) and request.args.get('token') == _LOG_TOKEN


@app.route('/')
def home():
    return "Alive"


@app.route('/log')
def log():
    if not _authorized():
        abort(403)
    try:
        return send_file(os.path.abspath('soundboard.csv'))
    except FileNotFoundError:
        abort(404)


def run():
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', '8080'))
    app.run(host=host, port=port)


def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
