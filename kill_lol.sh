#!/usr/bin/env bash
set -euo pipefail

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_CYAN='\033[0;36m'
COLOR_BOLD='\033[1m'
COLOR_RESET='\033[0m'

divider="─────────────────────────────────────────────────────────────────"

echo ""
echo -e "${COLOR_BOLD}$divider${COLOR_RESET}"
echo -e "${COLOR_BOLD}  League of Legends / Liên Minh Huyền Thoại — Process Killer${COLOR_RESET}"
echo -e "${COLOR_BOLD}$divider${COLOR_RESET}"
echo ""

killed=0

# --- 1. Kill LeagueClient (highest CPU) ---
# Find the LeagueClient main process (exclude UX, Helpers, CrashHandlers)
# Sort by CPU descending and pick the top one
client_line=$(ps aux \
  | grep "LeagueClient" \
  | grep -v grep \
  | grep -v "LeagueClientUx" \
  | grep -v "LeagueCrashHandler" \
  | grep -v "Helper" \
  | sort -k3 -rn \
  | head -1 || true)

if [[ -n "$client_line" ]]; then
  client_pid=$(echo "$client_line" | awk '{print $2}')
  client_cpu=$(echo "$client_line" | awk '{print $3}')
  echo -e "  ${COLOR_BOLD}[1] LeagueClient${COLOR_RESET}"
  echo -e "      PID: ${COLOR_CYAN}${client_pid}${COLOR_RESET}  |  CPU: ${COLOR_YELLOW}${client_cpu}%${COLOR_RESET}"
  if kill -9 "$client_pid" 2>/dev/null; then
    echo -e "      Status: ${COLOR_GREEN}Killed${COLOR_RESET}"
    killed=$((killed + 1))
  else
    echo -e "      Status: ${COLOR_RED}Failed to kill (permission denied or already dead)${COLOR_RESET}"
  fi
else
  echo -e "  ${COLOR_BOLD}[1] LeagueClient${COLOR_RESET}"
  echo -e "      Status: ${COLOR_YELLOW}Not running${COLOR_RESET}"
fi

echo ""

# --- 2. Kill LeagueOfLegends (In-Game) ---
game_line=$(ps aux \
  | grep -E "LeagueofLegends|LeagueOfLegends" \
  | grep -v grep \
  | grep -v "LeagueCrashHandler" \
  | sort -k3 -rn \
  | head -1 || true)

if [[ -n "$game_line" ]]; then
  game_pid=$(echo "$game_line" | awk '{print $2}')
  game_cpu=$(echo "$game_line" | awk '{print $3}')
  echo -e "  ${COLOR_BOLD}[2] LeagueOfLegends (In-Game)${COLOR_RESET}"
  echo -e "      PID: ${COLOR_CYAN}${game_pid}${COLOR_RESET}  |  CPU: ${COLOR_YELLOW}${game_cpu}%${COLOR_RESET}"
  if kill -9 "$game_pid" 2>/dev/null; then
    echo -e "      Status: ${COLOR_GREEN}Killed${COLOR_RESET}"
    killed=$((killed + 1))
  else
    echo -e "      Status: ${COLOR_RED}Failed to kill (permission denied or already dead)${COLOR_RESET}"
  fi
else
  echo -e "  ${COLOR_BOLD}[2] LeagueOfLegends (In-Game)${COLOR_RESET}"
  echo -e "      Status: ${COLOR_YELLOW}Not running${COLOR_RESET}"
fi

echo ""
echo -e "  $divider"
echo -e "  ${COLOR_BOLD}Result: ${killed}/2 processes killed.${COLOR_RESET}"
echo ""
