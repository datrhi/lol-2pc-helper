#!/usr/bin/env bash
set -euo pipefail

# Process names to detect for League of Legends / Liên Minh Huyền Thoại
PROCESS_PATTERNS=(
  "LeagueClient"
  "LeagueClientUx"
  "LeagueofLegends"       # note: binary uses lowercase 'of'
  "LeagueOfLegends"
  "LeagueCrashHandler"
  "RiotClientServices"
  "Riot Client"
)

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_CYAN='\033[0;36m'
COLOR_BOLD='\033[1m'
COLOR_RESET='\033[0m'

divider="─────────────────────────────────────────────────────────────────"

print_header() {
  echo ""
  echo -e "${COLOR_BOLD}$divider${COLOR_RESET}"
  echo -e "${COLOR_BOLD}  League of Legends / Liên Minh Huyền Thoại — Process Scanner${COLOR_RESET}"
  echo -e "${COLOR_BOLD}$divider${COLOR_RESET}"
  echo -e "  Scan time: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
}

scan_processes() {
  local found=0
  local total_cpu=0
  local total_mem=0

  printf "  ${COLOR_BOLD}%-7s  %-42s  %6s  %6s${COLOR_RESET}\n" "PID" "PROCESS" "CPU%" "MEM%"
  echo "  $divider"

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local pid cpu mem command
    pid=$(echo "$line" | awk '{print $2}')
    cpu=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    command=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | xargs)

    local proc_name=""
    for pattern in "${PROCESS_PATTERNS[@]}"; do
      if echo "$command" | grep -q "$pattern"; then
        # Extract the meaningful binary name from the full path
        # e.g. ".../LeagueClientUx Helper (Renderer).app/.../LeagueClientUx Helper (Renderer)"
        local bin_path
        bin_path=$(echo "$command" | sed 's/ --.*//')
        if echo "$bin_path" | grep -q "Helper (Renderer)"; then
          proc_name="LeagueClientUx Helper (Renderer)"
        elif echo "$bin_path" | grep -q "Helper (GPU)"; then
          proc_name="LeagueClientUx Helper (GPU)"
        elif echo "$bin_path" | grep -q "Riot Client Helper (Renderer)"; then
          proc_name="Riot Client Helper (Renderer)"
        elif echo "$bin_path" | grep -q "Riot Client Helper (GPU)"; then
          proc_name="Riot Client Helper (GPU)"
        elif echo "$bin_path" | grep -q "Riot Client Helper"; then
          proc_name="Riot Client Helper"
        elif echo "$bin_path" | grep -q "LeagueClientUx Helper"; then
          proc_name="LeagueClientUx Helper"
        elif echo "$bin_path" | grep -q "LeagueCrashHandler"; then
          proc_name="LeagueCrashHandler"
        elif echo "$bin_path" | grep -q "LeagueClientUx"; then
          proc_name="LeagueClientUx"
        elif echo "$bin_path" | grep -q "LeagueClient"; then
          proc_name="LeagueClient"
        elif echo "$bin_path" | grep -q "LeagueofLegends\|LeagueOfLegends"; then
          proc_name="LeagueOfLegends (In-Game)"
        elif echo "$bin_path" | grep -q "RiotClientServices"; then
          proc_name="RiotClientServices"
        elif echo "$bin_path" | grep -q "Riot Client"; then
          proc_name="Riot Client"
        else
          proc_name="$pattern"
        fi
        break
      fi
    done

    [[ -z "$proc_name" ]] && continue

    # Trim long names
    if [[ ${#proc_name} -gt 42 ]]; then
      proc_name="${proc_name:0:39}..."
    fi

    printf "  ${COLOR_CYAN}%-7s${COLOR_RESET}  %-42s  %6s  %6s\n" "$pid" "$proc_name" "$cpu" "$mem"
    found=$((found + 1))
    total_cpu=$(echo "$total_cpu + $cpu" | bc)
    total_mem=$(echo "$total_mem + $mem" | bc)
  done < <(ps aux | grep -E "$(IFS='|'; echo "${PROCESS_PATTERNS[*]}")" | grep -v grep)

  echo "  $divider"

  if [[ $found -eq 0 ]]; then
    echo -e "  ${COLOR_RED}No League of Legends / Liên Minh Huyền Thoại processes found.${COLOR_RESET}"
  else
    printf "  ${COLOR_YELLOW}Total: %d processes${COLOR_RESET}  |  " "$found"
    printf "${COLOR_YELLOW}CPU: %.1f%%${COLOR_RESET}  |  " "$total_cpu"
    printf "${COLOR_YELLOW}MEM: %.1f%%${COLOR_RESET}\n" "$total_mem"
  fi
  echo ""

  # Detect game state
  local client_running=false
  local game_running=false

  if ps aux | grep -E "LeagueClient" | grep -v grep | grep -v "LeagueClientUx" | grep -v "LeagueCrashHandler" | grep -qv "Helper"; then
    client_running=true
  fi
  if ps aux | grep -E "LeagueofLegends|LeagueOfLegends" | grep -v grep | grep -v "LeagueCrashHandler" | grep -qv "Helper"; then
    game_running=true
  fi

  echo -e "  ${COLOR_BOLD}Game State:${COLOR_RESET}"
  if $game_running; then
    echo -e "    League Client : ${COLOR_GREEN}Running${COLOR_RESET}"
    echo -e "    In-Game       : ${COLOR_GREEN}Yes (match in progress)${COLOR_RESET}"
  elif $client_running; then
    echo -e "    League Client : ${COLOR_GREEN}Running${COLOR_RESET}"
    echo -e "    In-Game       : ${COLOR_RED}No${COLOR_RESET}"
  else
    echo -e "    League Client : ${COLOR_RED}Not running${COLOR_RESET}"
    echo -e "    In-Game       : ${COLOR_RED}No${COLOR_RESET}"
  fi

  # Detect region from process args
  local region
  region=$(ps aux | grep "LeagueClient" | grep -v grep | grep -oE '\-\-region=[A-Z0-9]+' | head -1 | cut -d= -f2)
  local locale
  locale=$(ps aux | grep "LeagueClient" | grep -v grep | grep -oE '\-\-locale=[a-z_A-Z]+' | head -1 | cut -d= -f2)

  if [[ -n "${region:-}" ]]; then
    echo -e "    Region        : ${COLOR_CYAN}${region}${COLOR_RESET}"
  fi
  if [[ -n "${locale:-}" ]]; then
    echo -e "    Locale        : ${COLOR_CYAN}${locale}${COLOR_RESET}"
  fi

  echo ""
  return $found
}

# --- Main ---
print_header

if [[ "${1:-}" == "--watch" ]]; then
  interval="${2:-5}"
  echo -e "  ${COLOR_YELLOW}Watch mode: refreshing every ${interval}s (Ctrl+C to stop)${COLOR_RESET}"
  while true; do
    clear
    print_header
    scan_processes || true
    sleep "$interval"
  done
else
  scan_processes || true
fi
