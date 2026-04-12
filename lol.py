"""
Cross-platform League of Legends helper utilities.

Handles process detection/killing, LCU API interaction, and Riot Client API
for both macOS and Windows.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import time
from pathlib import Path

import psutil
import requests

requests.packages.urllib3.disable_warnings()

log = logging.getLogger("lol")

SYSTEM = platform.system()  # "Darwin" or "Windows"

# Default lockfile paths per platform
_DEFAULT_LOCKFILE = {
    "Darwin": "/Applications/League of Legends.app/Contents/LoL/lockfile",
    "Windows": r"C:\Riot Games\League of Legends\lockfile",
}

# Process name patterns per platform
_LEAGUE_CLIENT_NAMES = {
    "Darwin": ["LeagueClient"],
    "Windows": ["LeagueClient.exe"],
}
_INGAME_NAMES = {
    "Darwin": ["LeagueofLegends", "LeagueOfLegends"],
    "Windows": ["League of Legends.exe"],
}
_RIOT_CLIENT_NAMES = {
    "Darwin": ["RiotClientServices"],
    "Windows": ["RiotClientServices.exe"],
}
_LEAGUE_CLIENT_UX_NAMES = {
    "Darwin": ["LeagueClientUx"],
    "Windows": ["LeagueClientUx.exe"],
}

# ── Helpers ──────────────────────────────────────────────────────


def _config_lockfile_path(config: dict | None = None) -> str:
    override = (config or {}).get("lockfile_path")
    if override:
        return override
    return _DEFAULT_LOCKFILE.get(SYSTEM, _DEFAULT_LOCKFILE["Windows"])


def _find_processes(name_list: list[str]) -> list[psutil.Process]:
    """Return running processes whose name matches any entry in *name_list*."""
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] in name_list:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def _find_processes_by_cmdline(keyword: str) -> list[psutil.Process]:
    """Return processes whose command-line contains *keyword*."""
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            cmdline = " ".join(proc.cmdline())
            if keyword in cmdline:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return found


def _kill_procs(procs: list[psutil.Process]) -> list[dict]:
    """Kill a list of processes, return summary dicts."""
    results = []
    for p in procs:
        try:
            pid = p.pid
            name = p.name()
            p.kill()
            results.append({"pid": pid, "name": name, "killed": True})
            log.info("Killed %s (PID %d)", name, pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            results.append({"pid": p.pid, "name": "?", "killed": False, "error": str(exc)})
            log.warning("Failed to kill PID %d: %s", p.pid, exc)
    return results


# ── Process Detection ────────────────────────────────────────────


def is_league_client_running() -> bool:
    return len(_find_processes(_LEAGUE_CLIENT_NAMES.get(SYSTEM, []))) > 0


def is_ingame_running() -> bool:
    return len(_find_processes(_INGAME_NAMES.get(SYSTEM, []))) > 0


def get_status(config: dict | None = None) -> dict:
    """Return a snapshot of League-related process state."""
    client_procs = _find_processes(_LEAGUE_CLIENT_NAMES.get(SYSTEM, []))
    ingame_procs = _find_processes(_INGAME_NAMES.get(SYSTEM, []))
    riot_procs = _find_processes(_RIOT_CLIENT_NAMES.get(SYSTEM, []))

    phase = None
    login_state = None
    logged_in_elsewhere = False
    try:
        creds = get_lcu_credentials(config)
        if creds:
            phase = lcu_get("/lol-gameflow/v1/gameflow-phase", creds)
            session = get_login_session(creds)
            if session:
                login_state = session.get("state")
                logged_in_elsewhere = is_logged_in_elsewhere(session)
    except Exception:
        pass

    return {
        "league_client_running": len(client_procs) > 0,
        "league_client_pids": [p.pid for p in client_procs],
        "ingame_running": len(ingame_procs) > 0,
        "ingame_pids": [p.pid for p in ingame_procs],
        "riot_client_running": len(riot_procs) > 0,
        "gameflow_phase": phase,
        "login_state": login_state,
        "logged_in_elsewhere": logged_in_elsewhere,
        "platform": SYSTEM,
    }


# ── Process Killing ──────────────────────────────────────────────


def kill_league_client() -> list[dict]:
    """Kill all LeagueClient processes (not UX helpers)."""
    procs = _find_processes(_LEAGUE_CLIENT_NAMES.get(SYSTEM, []))
    return _kill_procs(procs)


def kill_ingame() -> list[dict]:
    """Kill In-Game (LeagueOfLegends) processes."""
    procs = _find_processes(_INGAME_NAMES.get(SYSTEM, []))
    return _kill_procs(procs)


def kill_all_league() -> dict:
    """Kill both LeagueClient and In-Game processes. Also kills UX helpers and crash handlers."""
    client_results = kill_league_client()
    ingame_results = kill_ingame()

    # Also kill UX and helpers so the client shuts down cleanly
    ux_procs = _find_processes(_LEAGUE_CLIENT_UX_NAMES.get(SYSTEM, []))
    ux_results = _kill_procs(ux_procs)

    # Kill any remaining League helper processes
    helper_names_kw = "LeagueClientUx Helper" if SYSTEM == "Darwin" else "LeagueClientUx.exe"
    helper_procs = _find_processes_by_cmdline(helper_names_kw)
    helper_results = _kill_procs(helper_procs)

    crash_kw = "LeagueCrashHandler"
    crash_procs = _find_processes_by_cmdline(crash_kw)
    crash_results = _kill_procs(crash_procs)

    return {
        "league_client": client_results,
        "ingame": ingame_results,
        "ux": ux_results,
        "helpers": helper_results,
        "crash_handlers": crash_results,
    }


# ── Login Session Detection ──────────────────────────────────────


def get_login_session(creds: dict) -> dict | None:
    """Query /lol-login/v1/session and return the JSON dict, or None."""
    try:
        result = lcu_get("/lol-login/v1/session", creds)
        if isinstance(result, dict) and "errorCode" not in result:
            return result
    except Exception:
        pass
    return None


def is_logged_in_elsewhere(session: dict | None = None, creds: dict | None = None) -> bool:
    """
    Detect the "Account logged elsewhere" popup.
    Checks for: state == "LOGGING_OUT" and error.messageId == "LOGGED_IN_ELSEWHERE".
    """
    if session is None and creds is not None:
        session = get_login_session(creds)
    if not session:
        return False
    error = session.get("error") or {}
    return (
        session.get("state") == "LOGGING_OUT"
        and error.get("messageId") == "LOGGED_IN_ELSEWHERE"
    )


def check_needs_restart(config: dict | None = None) -> dict:
    """
    Check if League Client needs a restart cycle.
    Returns {"needs_restart": bool, "reason": str|None, ...}
    """
    if not is_league_client_running():
        return {"needs_restart": True, "reason": "process_down"}

    creds = get_lcu_credentials(config)
    if not creds:
        return {"needs_restart": False, "reason": None}

    session = get_login_session(creds)
    if is_logged_in_elsewhere(session):
        return {"needs_restart": True, "reason": "logged_in_elsewhere"}

    return {"needs_restart": False, "reason": None}


# ── LCU Credentials ─────────────────────────────────────────────


def get_lcu_credentials(config: dict | None = None) -> dict | None:
    """
    Read the League Client lockfile and return credentials dict:
    {"port": int, "token": str, "pid": int, "protocol": str}
    Returns None if lockfile doesn't exist or is unreadable.
    """
    lockfile = Path(_config_lockfile_path(config))
    if not lockfile.exists():
        return None
    try:
        content = lockfile.read_text().strip()
        # Format: LeagueClient:{pid}:{port}:{token}:{protocol}
        parts = content.split(":")
        if len(parts) < 5:
            return None
        return {
            "pid": int(parts[1]),
            "port": int(parts[2]),
            "token": parts[3],
            "protocol": parts[4],
        }
    except Exception as exc:
        log.warning("Failed to read lockfile %s: %s", lockfile, exc)
        return None


# ── Riot Client Credentials ──────────────────────────────────────


def get_riot_client_credentials() -> dict | None:
    """
    Parse Riot Client port and auth token from the running RiotClientServices
    or 'Riot Client' process command-line arguments.
    Returns {"port": int, "token": str} or None.
    """
    candidates = _find_processes(_RIOT_CLIENT_NAMES.get(SYSTEM, []))

    # Also look for the UI process which has --app-port and --remoting-auth-token
    ui_keyword = "Riot Client --app-port" if SYSTEM == "Darwin" else "Riot Client.exe"
    candidates += _find_processes_by_cmdline(ui_keyword)

    for proc in candidates:
        try:
            cmdline = " ".join(proc.cmdline())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        port_match = re.search(r"--app-port=(\d+)", cmdline)
        token_match = re.search(r"--remoting-auth-token=(\S+)", cmdline)
        if port_match and token_match:
            return {
                "port": int(port_match.group(1)),
                "token": token_match.group(1),
            }

    # Fallback: if RiotClientServices is running, look at all Riot Client processes
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"] or ""
            if "Riot" not in name and "riot" not in name:
                continue
            cmdline = " ".join(proc.cmdline())
            port_match = re.search(r"--app-port=(\d+)", cmdline)
            token_match = re.search(r"--remoting-auth-token=(\S+)", cmdline)
            if port_match and token_match:
                return {
                    "port": int(port_match.group(1)),
                    "token": token_match.group(1),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return None


# ── LCU API ──────────────────────────────────────────────────────


def lcu_get(endpoint: str, creds: dict) -> any:
    url = f"https://127.0.0.1:{creds['port']}{endpoint}"
    resp = requests.get(url, auth=("riot", creds["token"]), verify=False, timeout=10)
    try:
        return resp.json()
    except Exception:
        return resp.text


def lcu_post(endpoint: str, creds: dict, data: dict | None = None) -> any:
    url = f"https://127.0.0.1:{creds['port']}{endpoint}"
    kwargs = {"auth": ("riot", creds["token"]), "verify": False, "timeout": 30}
    if data is not None:
        kwargs["json"] = data
    resp = requests.post(url, **kwargs)
    try:
        return resp.json()
    except Exception:
        return resp.text


def rc_post(endpoint: str, rc_creds: dict) -> any:
    url = f"https://127.0.0.1:{rc_creds['port']}{endpoint}"
    resp = requests.post(url, auth=("riot", rc_creds["token"]), verify=False, timeout=30)
    try:
        return resp.json()
    except Exception:
        return resp.text


# ── High-Level Actions ───────────────────────────────────────────


def launch_league_client(config: dict | None = None, max_wait: int = 90) -> dict:
    """
    Launch League Client via Riot Client API.
    Waits up to *max_wait* seconds for the client to become responsive.
    Returns a result dict with status details.
    """
    rc_creds = get_riot_client_credentials()
    if not rc_creds:
        return {"ok": False, "error": "Riot Client is not running"}

    log.info("Launching League Client via Riot Client API (port %d)...", rc_creds["port"])
    try:
        result = rc_post(
            "/product-launcher/v1/products/league_of_legends/patchlines/live",
            rc_creds,
        )
        log.info("Launch signal sent, response: %s", result)
    except Exception as exc:
        return {"ok": False, "error": f"Failed to send launch signal: {exc}"}

    # Wait for League Client to become ready
    log.info("Waiting up to %ds for League Client to be ready...", max_wait)
    start = time.time()
    while time.time() - start < max_wait:
        creds = get_lcu_credentials(config)
        if creds:
            try:
                phase = lcu_get("/lol-gameflow/v1/gameflow-phase", creds)
                if phase and "errorCode" not in str(phase):
                    elapsed = round(time.time() - start, 1)
                    log.info("League Client ready (phase=%s) after %.1fs", phase, elapsed)
                    return {"ok": True, "phase": phase, "elapsed": elapsed}
            except Exception:
                pass
        time.sleep(2)

    return {"ok": False, "error": f"League Client not ready after {max_wait}s"}


def relaunch_league_client(config: dict | None = None, max_wait: int = 90) -> dict:
    """
    Kill In-Game process if present, then launch League Client.
    Used by Machine 2 after its client goes down.
    """
    # Kill In-Game if it appeared
    ingame_killed = kill_ingame()
    if ingame_killed:
        log.info("Killed In-Game processes before relaunch: %s", ingame_killed)
        time.sleep(2)

    result = launch_league_client(config, max_wait)

    # Check again if In-Game appeared after launch and kill it
    time.sleep(3)
    if is_ingame_running():
        log.info("In-Game process appeared after launch, killing it...")
        kill_ingame()
        time.sleep(2)

    return result


def load_config(path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    config_path = Path(path)
    if not config_path.exists():
        log.warning("Config file %s not found, using defaults", path)
        return {}
    with open(config_path) as f:
        return json.load(f)
