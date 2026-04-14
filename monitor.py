"""
Monitor and orchestrator for League Client restart workflow.
Runs on Machine 2 (Mac Mini). Detects when League Client goes down
and coordinates the 3-step restart with Machine 1 (Windows PC).

Usage:
    python3 monitor.py                # uses config.json in same directory
    python3 monitor.py --config config.json
"""

import argparse
import logging
import time

import requests

import lol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("monitor")

# ANSI colors for terminal output
G = "\033[0;32m"  # green
R = "\033[0;31m"  # red
Y = "\033[1;33m"  # yellow
C = "\033[0;36m"  # cyan
B = "\033[1m"     # bold
RST = "\033[0m"   # reset


def peer_url(config: dict, path: str) -> str:
    host = config["peer_host"]
    port = config.get("peer_port", 5555)
    return f"http://{host}:{port}{path}"


def peer_headers(config: dict) -> dict:
    secret = config.get("secret", "")
    if secret:
        return {"Authorization": f"Bearer {secret}"}
    return {}


def peer_post(config: dict, path: str, timeout: int = 120) -> dict:
    """Send POST to Machine 1's server and return JSON response."""
    url = peer_url(config, path)
    headers = peer_headers(config)
    log.info("POST %s", url)
    resp = requests.post(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def peer_get(config: dict, path: str, timeout: int = 10) -> dict:
    url = peer_url(config, path)
    headers = peer_headers(config)
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def check_peer_alive(config: dict) -> bool:
    """Check if Machine 1's server is reachable."""
    try:
        result = peer_get(config, "/api/ping", timeout=5)
        return result.get("ok", False)
    except Exception:
        return False


def run_restart_workflow(config: dict) -> bool:
    """
    Execute the 3-step restart workflow:
      Step 1: Tell Machine 1 to kill In-Game + LeagueClient
      Step 2: Locally relaunch League Client (kill In-Game if appears)
      Step 3: Tell Machine 1 to relaunch League Client
    Returns True on success.
    """
    print()
    print(f"  {B}{'═' * 60}{RST}")
    print(f"  {B}{Y}  RESTART WORKFLOW TRIGGERED{RST}")
    print(f"  {B}{'═' * 60}{RST}")
    print()

    # ── Step 1: Tell Machine 1 to kill processes ─────────────
    print(f"  {B}[Step 1/3]{RST} Telling Machine 1 to kill League processes...")
    try:
        result = peer_post(config, "/api/kill")
        if result.get("ok"):
            print(f"  {G}✓{RST} Machine 1: processes killed")
            log.info("Step 1 done: %s", result)
        else:
            print(f"  {R}✗{RST} Machine 1: kill failed — {result}")
            log.error("Step 1 failed: %s", result)
            return False
    except Exception as exc:
        print(f"  {R}✗{RST} Machine 1: unreachable — {exc}")
        log.error("Step 1 error: %s", exc)
        return False

    time.sleep(3)

    # ── Step 2: Locally relaunch League Client ───────────────
    print(f"  {B}[Step 2/3]{RST} Relaunching League Client locally (Machine 2)...")
    result = lol.relaunch_league_client(config)
    if result.get("ok"):
        print(f"  {G}✓{RST} Machine 2: League Client is ready (phase={result.get('phase')})")
        log.info("Step 2 done: %s", result)
    else:
        err = result.get("error", "")
        if "login_error" in err:
            print(f"  {R}✗{RST} Machine 2: login error detected — client killed & retried but still failed")
            print(f"  {Y}  Detail: {result.get('detail', result.get('login_detail', ''))}{RST}")
        else:
            print(f"  {R}✗{RST} Machine 2: relaunch failed — {err}")
        log.error("Step 2 failed: %s", result)
        return False

    time.sleep(2)

    # ── Step 3: Tell Machine 1 to relaunch League Client ─────
    print(f"  {B}[Step 3/3]{RST} Telling Machine 1 to relaunch League Client...")
    try:
        result = peer_post(config, "/api/launch", timeout=120)
        if result.get("ok"):
            print(f"  {G}✓{RST} Machine 1: League Client is ready (phase={result.get('phase')})")
            log.info("Step 3 done: %s", result)
        else:
            print(f"  {R}✗{RST} Machine 1: launch failed — {result.get('error')}")
            log.error("Step 3 failed: %s", result)
            return False
    except Exception as exc:
        print(f"  {R}✗{RST} Machine 1: unreachable — {exc}")
        log.error("Step 3 error: %s", exc)
        return False

    print()
    print(f"  {G}{B}  WORKFLOW COMPLETE — Both machines have League Client running{RST}")
    print(f"  {B}{'═' * 60}{RST}")
    print()
    return True


def monitor_loop(config: dict):
    """Main polling loop. Detects League Client going down and triggers restart."""
    poll_interval = config.get("poll_interval", 5)
    was_running = None
    restart_count = 0

    print()
    print(f"  {B}{'─' * 60}{RST}")
    print(f"  {B}  LoL Helper Monitor — Machine 2 (Mac Mini){RST}")
    print(f"  {B}{'─' * 60}{RST}")
    print(f"  Peer: {C}{config.get('peer_host', '?')}:{config.get('peer_port', 5555)}{RST}")
    print(f"  Poll interval: {C}{poll_interval}s{RST}")
    print()

    # Verify peer connectivity
    print(f"  {Y}▸{RST} Checking Machine 1 connectivity...")
    if check_peer_alive(config):
        print(f"  {G}✓{RST} Machine 1 is reachable")
    else:
        print(f"  {R}✗{RST} Machine 1 is NOT reachable at {config.get('peer_host')}:{config.get('peer_port', 5555)}")
        print(f"  {Y}  Continuing anyway — will retry when workflow triggers{RST}")

    print()
    print(f"  {C}▸{RST} Monitoring League Client status... (Ctrl+C to stop)")
    print()

    while True:
        try:
            running = lol.is_league_client_running()

            if was_running is None:
                state = f"{G}running{RST}" if running else f"{R}not running{RST}"
                print(f"  [{time.strftime('%H:%M:%S')}] Initial state: League Client is {state}")
                was_running = running
            elif was_running and not running:
                # League Client just went down
                restart_count += 1
                print(f"  [{time.strftime('%H:%M:%S')}] {R}{B}League Client went DOWN{RST} (restart #{restart_count})")
                log.info("League Client went down — triggering restart workflow #%d", restart_count)

                success = run_restart_workflow(config)
                if success:
                    was_running = lol.is_league_client_running()
                    print(f"  [{time.strftime('%H:%M:%S')}] {C}▸{RST} Resuming monitoring...")
                else:
                    log.warning("Restart workflow failed, will retry on next poll cycle")
                    was_running = False
                print()
            elif not was_running and running:
                print(f"  [{time.strftime('%H:%M:%S')}] {G}League Client is back up{RST}")
                was_running = True
            else:
                was_running = running

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n  {Y}Monitor stopped by user.{RST}\n")
            break
        except Exception as exc:
            log.error("Monitor loop error: %s", exc, exc_info=True)
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="LoL Helper Monitor (Machine 2)")
    parser.add_argument("--config", default="config.json", help="Config file path")
    args = parser.parse_args()

    config = lol.load_config(args.config)

    if config.get("peer_host", "").endswith("XXX"):
        print(f"\n  {R}ERROR: Please edit config.json and set peer_host to Machine 1's IP address.{RST}\n")
        return

    monitor_loop(config)


if __name__ == "__main__":
    main()
