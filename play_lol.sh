#!/usr/bin/env bash
set -euo pipefail

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_CYAN='\033[0;36m'
COLOR_BOLD='\033[1m'
COLOR_RESET='\033[0m'

divider="─────────────────────────────────────────────────────────────────"

LOCKFILE="/Applications/League of Legends.app/Contents/LoL/lockfile"
MAX_WAIT=60

# ── Queue ID reference ──────────────────────────────────────────
# 400  = Thường (Normal Draft)
# 420  = Xếp Hạng Đơn/Đôi (Ranked Solo/Duo)
# 440  = Xếp Hạng Linh Hoạt (Ranked Flex)
# 450  = ARAM
# 480  = Đấu Siêu Tốc (Swiftplay)
# 870  = Co-op vs AI (Cực Dễ / Intro)
# 880  = Co-op vs AI (Dễ / Beginner)
# 890  = Co-op vs AI (Trung Cấp / Intermediate)
# 1700 = Võ Đài (Arena)
# 2300 = Loạn Đấu (Brawl)
DEFAULT_QUEUE=420

print_header() {
  echo ""
  echo -e "${COLOR_BOLD}${divider}${COLOR_RESET}"
  echo -e "${COLOR_BOLD}  League of Legends / Liên Minh Huyền Thoại — Play Game${COLOR_RESET}"
  echo -e "${COLOR_BOLD}${divider}${COLOR_RESET}"
  echo ""
}

die() { echo -e "  ${COLOR_RED}ERROR: $1${COLOR_RESET}"; echo ""; exit 1; }
info() { echo -e "  ${COLOR_CYAN}▸${COLOR_RESET} $1"; }
ok() { echo -e "  ${COLOR_GREEN}✓${COLOR_RESET} $1"; }
warn() { echo -e "  ${COLOR_YELLOW}▸${COLOR_RESET} $1"; }

get_riot_client_credentials() {
  local rc_line
  rc_line=$(ps aux | grep "Riot Client --app-port" | grep -v grep | head -1 || true)
  [[ -z "$rc_line" ]] && return 1

  RC_PORT=$(echo "$rc_line" | grep -oE '\-\-app-port=[0-9]+' | cut -d= -f2)
  RC_TOKEN=$(echo "$rc_line" | grep -oE '\-\-remoting-auth-token=[^ ]+' | cut -d= -f2)
  [[ -n "$RC_PORT" && -n "$RC_TOKEN" ]]
}

get_lcu_credentials() {
  [[ ! -f "$LOCKFILE" ]] && return 1
  local content
  content=$(cat "$LOCKFILE")
  LCU_PORT=$(echo "$content" | cut -d: -f3)
  LCU_TOKEN=$(echo "$content" | cut -d: -f4)
  [[ -n "$LCU_PORT" && -n "$LCU_TOKEN" ]]
}

lcu_get() {
  curl -s -k -u "riot:${LCU_TOKEN}" "https://127.0.0.1:${LCU_PORT}${1}" 2>/dev/null
}

lcu_post() {
  local url="$1"
  local data="${2:-}"
  if [[ -n "$data" ]]; then
    curl -s -k -u "riot:${LCU_TOKEN}" -X POST "https://127.0.0.1:${LCU_PORT}${url}" \
      -H "Content-Type: application/json" -d "$data" 2>/dev/null
  else
    curl -s -k -u "riot:${LCU_TOKEN}" -X POST "https://127.0.0.1:${LCU_PORT}${url}" 2>/dev/null
  fi
}

lcu_delete() {
  curl -s -k -u "riot:${LCU_TOKEN}" -X DELETE "https://127.0.0.1:${LCU_PORT}${1}" 2>/dev/null
}

rc_post() {
  curl -s -k -u "riot:${RC_TOKEN}" -X POST "https://127.0.0.1:${RC_PORT}${1}" 2>/dev/null
}

wait_for_lcu() {
  local elapsed=0
  while [[ $elapsed -lt $MAX_WAIT ]]; do
    if get_lcu_credentials; then
      local phase
      phase=$(lcu_get "/lol-gameflow/v1/gameflow-phase" 2>/dev/null || true)
      if [[ -n "$phase" && "$phase" != *"errorCode"* ]]; then
        return 0
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    printf "\r  ${COLOR_YELLOW}▸${COLOR_RESET} Waiting for League Client to be ready... ${elapsed}s"
  done
  echo ""
  return 1
}

launch_league_client() {
  info "League Client is not running. Launching via Riot Client..."

  if ! get_riot_client_credentials; then
    die "Riot Client is not running. Please open Riot Client first."
  fi

  rc_post "/product-launcher/v1/products/league_of_legends/patchlines/live" > /dev/null
  ok "Launch signal sent to Riot Client"

  if wait_for_lcu; then
    echo ""
    ok "League Client is ready"
  else
    die "League Client did not start within ${MAX_WAIT}s. Try launching manually."
  fi
}

show_queue_menu() {
  echo ""
  echo -e "  ${COLOR_BOLD}Select game mode:${COLOR_RESET}"
  echo ""
  echo -e "    ${COLOR_CYAN}1${COLOR_RESET})  Xếp Hạng Đơn/Đôi  (Ranked Solo/Duo)     [420]"
  echo -e "    ${COLOR_CYAN}2${COLOR_RESET})  Xếp Hạng Linh Hoạt (Ranked Flex)          [440]"
  echo -e "    ${COLOR_CYAN}3${COLOR_RESET})  Thường              (Normal Draft)         [400]"
  echo -e "    ${COLOR_CYAN}4${COLOR_RESET})  ARAM                                       [450]"
  echo -e "    ${COLOR_CYAN}5${COLOR_RESET})  Đấu Siêu Tốc       (Swiftplay)            [480]"
  echo -e "    ${COLOR_CYAN}6${COLOR_RESET})  Võ Đài              (Arena)                [1700]"
  echo -e "    ${COLOR_CYAN}7${COLOR_RESET})  Loạn Đấu            (Brawl)                [2300]"
  echo -e "    ${COLOR_CYAN}8${COLOR_RESET})  Co-op vs AI (Trung Cấp)                    [890]"
  echo ""
  printf "  Choice [1]: "
  read -r choice
  case "${choice:-1}" in
    1) QUEUE_ID=420  ;;
    2) QUEUE_ID=440  ;;
    3) QUEUE_ID=400  ;;
    4) QUEUE_ID=450  ;;
    5) QUEUE_ID=480  ;;
    6) QUEUE_ID=1700 ;;
    7) QUEUE_ID=2300 ;;
    8) QUEUE_ID=890  ;;
    *) QUEUE_ID=420  ;;
  esac
}

accept_match() {
  info "Waiting for match to be found..."
  local elapsed=0
  local max_queue_wait=600  # 10 minutes
  while [[ $elapsed -lt $max_queue_wait ]]; do
    local phase
    phase=$(lcu_get "/lol-gameflow/v1/gameflow-phase" 2>/dev/null | tr -d '"')

    case "$phase" in
      "Matchmaking")
        ;;
      "ReadyCheck")
        ok "Match found! Auto-accepting..."
        lcu_post "/lol-matchmaking/v1/ready-check/accept" > /dev/null
        ok "Match accepted!"
        return 0
        ;;
      "ChampSelect")
        ok "Already in Champion Select"
        return 0
        ;;
      "InProgress")
        ok "Game is already in progress"
        return 0
        ;;
      "Lobby")
        warn "Returned to lobby (match declined or dodged)"
        return 1
        ;;
      "None"|"EndOfGame"|"PreEndOfGame"|"WaitingForStats")
        warn "Game flow changed to: ${phase}"
        return 1
        ;;
    esac

    sleep 1
    elapsed=$((elapsed + 1))
    local mins=$((elapsed / 60))
    local secs=$((elapsed % 60))
    printf "\r  ${COLOR_YELLOW}▸${COLOR_RESET} Queue time: %02d:%02d  " "$mins" "$secs"
  done
  echo ""
  warn "Queue timed out after 10 minutes."
  return 1
}

# ── Main ────────────────────────────────────────────────────────
print_header

# Step 1: Ensure League Client is running
league_running=false
if ps aux | grep "LeagueClient" | grep -v grep | grep -v "LeagueClientUx" | grep -v "LeagueCrashHandler" | grep -qv "Helper" 2>/dev/null; then
  league_running=true
fi

if ! $league_running; then
  launch_league_client
else
  ok "League Client is already running"
  get_lcu_credentials || die "Could not read League Client lockfile"
fi

# Step 2: Show summoner info
summoner=$(lcu_get "/lol-summoner/v1/current-summoner")
game_name=$(echo "$summoner" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d['gameName']}#{d['tagLine']}\")" 2>/dev/null || echo "Unknown")
info "Logged in as: ${COLOR_BOLD}${game_name}${COLOR_RESET}"

# Step 3: Check current phase
phase=$(lcu_get "/lol-gameflow/v1/gameflow-phase" | tr -d '"')
info "Current phase: ${COLOR_YELLOW}${phase}${COLOR_RESET}"

if [[ "$phase" == "Matchmaking" ]]; then
  ok "Already in matchmaking queue"
  accept_match
  exit $?
elif [[ "$phase" == "ChampSelect" ]]; then
  ok "Already in Champion Select — nothing to do"
  exit 0
elif [[ "$phase" == "InProgress" ]]; then
  ok "Game is already in progress — nothing to do"
  exit 0
elif [[ "$phase" == "ReadyCheck" ]]; then
  ok "Match found! Auto-accepting..."
  lcu_post "/lol-matchmaking/v1/ready-check/accept" > /dev/null
  ok "Match accepted!"
  exit 0
fi

# Step 4: Select queue or use arg
if [[ -n "${1:-}" ]]; then
  QUEUE_ID="$1"
  info "Using queue ID from argument: ${QUEUE_ID}"
else
  show_queue_menu
fi

# Step 5: Create lobby
echo ""
info "Creating lobby (queue ${QUEUE_ID})..."
result=$(lcu_post "/lol-lobby/v2/lobby" "{\"queueId\": ${QUEUE_ID}}")
if echo "$result" | grep -q "canStartActivity"; then
  ok "Lobby created"
else
  error_msg=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message','Unknown error'))" 2>/dev/null || echo "$result")
  die "Failed to create lobby: ${error_msg}"
fi

# Step 6: Start matchmaking
info "Starting matchmaking search..."
search_result=$(lcu_post "/lol-lobby/v2/lobby/matchmaking/search")
if [[ -z "$search_result" ]]; then
  ok "Matchmaking started!"
else
  warn "Matchmaking response: ${search_result}"
fi

# Step 7: Wait for match and auto-accept
echo ""
accept_match
echo ""
