"""
HTTP server for League of Legends process management.
Runs on Machine 1 (Windows PC). Accepts commands from Machine 2 (Mac Mini).

Usage:
    python server.py                # uses config.json in same directory
    python server.py --port 5555    # override port
"""

import argparse
import logging
from functools import wraps

from flask import Flask, jsonify, request

import lol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("server")

app = Flask(__name__)
config: dict = {}


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = config.get("secret", "")
        if not secret:
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {secret}":
            log.warning("Unauthorized request from %s", request.remote_addr)
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/status", methods=["GET"])
@require_auth
def api_status():
    """Return current League process state."""
    status = lol.get_status()
    log.info("Status requested: %s", status)
    return jsonify({"ok": True, **status})


@app.route("/api/kill", methods=["POST"])
@require_auth
def api_kill():
    """Kill In-Game and LeagueClient processes."""
    log.info("Kill requested from %s", request.remote_addr)
    result = lol.kill_all_league()
    log.info("Kill result: %s", result)
    return jsonify({"ok": True, "result": result})


@app.route("/api/launch", methods=["POST"])
@require_auth
def api_launch():
    """Launch League Client via Riot Client API."""
    log.info("Launch requested from %s", request.remote_addr)
    result = lol.launch_league_client(config)
    log.info("Launch result: %s", result)
    if result.get("ok"):
        return jsonify(result)
    else:
        return jsonify(result), 500


@app.route("/api/ping", methods=["GET"])
def api_ping():
    """Health check, no auth required."""
    return jsonify({"ok": True, "platform": lol.SYSTEM})


def main():
    global config

    parser = argparse.ArgumentParser(description="LoL Helper HTTP Server")
    parser.add_argument("--port", type=int, default=None, help="Server port (overrides config)")
    parser.add_argument("--config", default="config.json", help="Config file path")
    args = parser.parse_args()

    config = lol.load_config(args.config)
    port = args.port or config.get("server_port", 5555)

    log.info("Starting LoL Helper server on port %d (platform: %s)", port, lol.SYSTEM)
    log.info("Endpoints: /api/status, /api/kill, /api/launch, /api/ping")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
