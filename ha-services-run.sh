#!/bin/bash
#
# HA Services Runner
#
# Automatycznie uruchamia serwisy z katalogu local_services/
# Pliki *.service są ładowane w kolejności alfabetycznej (00-, 10-, 20-...)
#
# Użycie:
#   ./ha-services-run.sh              # Start all + monitor
#   ./ha-services-run.sh start        # Start all
#   ./ha-services-run.sh stop         # Stop all
#   ./ha-services-run.sh status       # Show status
#   ./ha-services-run.sh restart      # Restart all
#   ./ha-services-run.sh reload       # Start new, stop removed, keep running
#   ./ha-services-run.sh logs         # Tail all logs
#   ./ha-services-run.sh start NAME   # Start single service
#   ./ha-services-run.sh stop NAME    # Stop single service
#

set -euo pipefail

# === Znajdź katalog bazowy ===
if [ -L "${BASH_SOURCE[0]}" ]; then
    REAL_SCRIPT="$(readlink "${BASH_SOURCE[0]}")"
    HA_DIR="$(cd "$(dirname "$REAL_SCRIPT")" && pwd)"
else
    HA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

SERVICES_DIR="$HA_DIR/local_services"
LOG_DIR="$HA_DIR/logs"
PID_DIR="$HA_DIR/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# === Defaults ===
DEFAULT_TYPE="simple"
DEFAULT_RESTART="always"
DEFAULT_RESTART_DELAY=5
DEFAULT_WAIT_TIMEOUT=30

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# === Helpers ===

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

parse_service_file() {
    local file="$1"
    
    NAME=""
    TYPE="$DEFAULT_TYPE"
    CMD=""
    WAIT_FOR=""
    RESTART="$DEFAULT_RESTART"
    RESTART_DELAY="$DEFAULT_RESTART_DELAY"
    ENV_FILE=""
    STOP_PATTERN=""
    ENV_VARS=()
    
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | sed 's/^["'\'']\|["'\'']$//g')
        
        case "$key" in
            NAME) NAME="$value" ;;
            TYPE) TYPE="$value" ;;
            CMD) CMD="$value" ;;
            WAIT_FOR) WAIT_FOR="$value" ;;
            RESTART) RESTART="$value" ;;
            RESTART_DELAY) RESTART_DELAY="$value" ;;
            ENV_FILE) ENV_FILE="$value" ;;
            ENV) ENV_VARS+=("$value") ;;
            STOP_PATTERN) STOP_PATTERN="$value" ;;
        esac
    done < "$file"
    
    if [ -z "$NAME" ]; then
        NAME=$(basename "$file" .service | sed 's/^[0-9]*-//')
    fi
    
    if [ -z "$STOP_PATTERN" ]; then
        STOP_PATTERN=$(echo "$CMD" | awk '{print $1}')
    fi
}

wait_for() {
    local condition="$1"
    local timeout="${2:-$DEFAULT_WAIT_TIMEOUT}"
    
    [ -z "$condition" ] && return 0
    
    local type="${condition%%:*}"
    local target="${condition#*:}"
    
    case "$type" in
        tcp)
            local host="${target%%:*}"
            local port="${target##*:}"
            log_info "Waiting for $host:$port..."
            local i=0
            while [ $i -lt $timeout ]; do
                if nc -z "$host" "$port" 2>/dev/null; then
                    log_ok "$host:$port available"
                    return 0
                fi
                sleep 1
                i=$((i + 1))
            done
            log_warn "Timeout waiting for $host:$port"
            return 1
            ;;
        service)
            log_info "Waiting for service $target..."
            local i=0
            while [ $i -lt $timeout ]; do
                if is_running "$target"; then
                    log_ok "Service $target running"
                    return 0
                fi
                sleep 1
                i=$((i + 1))
            done
            log_warn "Timeout waiting for service $target"
            return 1
            ;;
        *)
            log_warn "Unknown wait type: $type"
            return 0
            ;;
    esac
}

is_running() {
    local name="$1"
    local pid_file="$PID_DIR/$name.pid"
    
    [ -f "$pid_file" ] || return 1
    
    local pid
    pid=$(head -1 "$pid_file")
    kill -0 "$pid" 2>/dev/null
}

get_pid() {
    local name="$1"
    local pid_file="$PID_DIR/$name.pid"
    
    [ -f "$pid_file" ] && head -1 "$pid_file"
}

load_env_file() {
    local env_file="$1"
    
    [ -z "$env_file" ] && return 0
    
    local full_path="$SERVICES_DIR/$env_file"
    [ -f "$full_path" ] || full_path="$HA_DIR/$env_file"
    
    if [ -f "$full_path" ]; then
        while IFS='=' read -r key value; do
            [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
            key=$(echo "$key" | xargs)
            export "$key"="$value"
        done < "$full_path"
    else
        log_warn "ENV_FILE not found: $env_file"
    fi
}

# === Service Management ===

start_service() {
    local service_file="$1"
    
    parse_service_file "$service_file"
    
    if is_running "$NAME"; then
        log_warn "$NAME already running (PID: $(get_pid "$NAME"))"
        return 0
    fi
    
    log_info "Starting $NAME..."
    
    if [ -n "$WAIT_FOR" ]; then
        wait_for "$WAIT_FOR" || return 1
    fi
    
    load_env_file "$ENV_FILE"
    for env_var in "${ENV_VARS[@]:-}"; do
        [ -n "$env_var" ] && export "${env_var%%=*}"="${env_var#*=}"
    done
    
    local log_file="$LOG_DIR/$NAME.log"
    local pid_file="$PID_DIR/$NAME.pid"
    
    echo "--- Start $(date) ---" >> "$log_file"
    
    case "$TYPE" in
        simple)
            eval "$CMD" >> "$log_file" 2>&1 &
            echo $! > "$pid_file"
            ;;
        script)
            local script_path="$SERVICES_DIR/$CMD"
            [ -f "$script_path" ] || script_path="$HA_DIR/$CMD"
            
            if [ -x "$script_path" ]; then
                "$script_path" >> "$log_file" 2>&1 &
                echo $! > "$pid_file"
            else
                log_error "Script not found or not executable: $CMD"
                return 1
            fi
            ;;
        *)
            log_error "Unknown TYPE: $TYPE"
            return 1
            ;;
    esac
    
    sleep 0.5
    
    if is_running "$NAME"; then
        log_ok "$NAME started (PID: $(get_pid "$NAME"))"
    else
        log_error "$NAME failed to start. Check $log_file"
        rm -f "$pid_file"
        return 1
    fi
}

stop_service() {
    local name="$1"
    local pid_file="$PID_DIR/$name.pid"
    
    local stop_pattern="$name"
    for f in "$SERVICES_DIR"/*.service; do
        [ -f "$f" ] || continue
        parse_service_file "$f"
        if [ "$NAME" = "$name" ]; then
            stop_pattern="$STOP_PATTERN"
            break
        fi
    done
    
    if [ -f "$pid_file" ]; then
        local pids
        pids=$(cat "$pid_file")
        
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        
        sleep 0.5
        
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null || true
        done
        
        rm -f "$pid_file"
    fi
    
    pkill -9 -f "$stop_pattern" 2>/dev/null || true
    
    log_ok "$name stopped"
}

# === Commands ===

cmd_start() {
    local target="${1:-}"
    
    if [ -n "$target" ]; then
        for f in "$SERVICES_DIR"/*.service; do
            [ -f "$f" ] || continue
            parse_service_file "$f"
            if [ "$NAME" = "$target" ]; then
                start_service "$f"
                return
            fi
        done
        log_error "Service not found: $target"
        return 1
    fi
    
    log_info "Starting all services..."
    echo ""
    
    for f in $(ls "$SERVICES_DIR"/*.service 2>/dev/null | sort); do
        [ -f "$f" ] || continue
        start_service "$f"
    done
    
    echo ""
    cmd_status
}

cmd_stop() {
    local target="${1:-}"
    
    if [ -n "$target" ]; then
        stop_service "$target"
        return
    fi
    
    log_info "Stopping all services..."
    
    for f in $(ls "$SERVICES_DIR"/*.service 2>/dev/null | sort -r); do
        [ -f "$f" ] || continue
        parse_service_file "$f"
        stop_service "$NAME"
    done
    
    rm -f "$PID_DIR"/*.pid
    
    log_ok "All services stopped"
}

cmd_restart() {
    local target="${1:-}"
    cmd_stop "$target"
    sleep 1
    cmd_start "$target"
}

cmd_status() {
    echo ""
    echo "=== Service Status ==="
    echo ""
    printf "%-20s %-10s %-10s %s\n" "NAME" "STATUS" "PID" "INFO"
    printf "%-20s %-10s %-10s %s\n" "----" "------" "---" "----"
    
    for f in $(ls "$SERVICES_DIR"/*.service 2>/dev/null | sort); do
        [ -f "$f" ] || continue
        parse_service_file "$f"
        
        local status="stopped"
        local pid="-"
        local info=""
        
        if is_running "$NAME"; then
            status="${GREEN}running${NC}"
            pid=$(get_pid "$NAME")
        else
            status="${RED}stopped${NC}"
            if [ -f "$LOG_DIR/$NAME.log" ]; then
                local last_line
                last_line=$(tail -1 "$LOG_DIR/$NAME.log" 2>/dev/null || echo "")
                if [[ "$last_line" =~ error|Error|ERROR|fatal|Fatal|FATAL ]]; then
                    info="(error in log)"
                fi
            fi
        fi
        
        printf "%-20s %-10b %-10s %s\n" "$NAME" "$status" "$pid" "$info"
    done
    
    echo ""
}

cmd_reload() {
    log_info "Reloading services..."
    
    # Get currently running services (as simple list)
    local running_services=""
    for pid_file in "$PID_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        local name
        name=$(basename "$pid_file" .pid)
        if is_running "$name"; then
            running_services="$running_services $name"
        fi
    done
    
    # Get configured services
    local configured_services=""
    local configured_files=""
    for f in "$SERVICES_DIR"/*.service; do
        [ -f "$f" ] || continue
        parse_service_file "$f"
        configured_services="$configured_services $NAME"
        configured_files="$configured_files $NAME:$f"
    done
    
    # Stop removed services (running but not configured)
    for name in $running_services; do
        if ! echo "$configured_services" | grep -qw "$name"; then
            log_info "Stopping removed service: $name"
            stop_service "$name"
        fi
    done
    
    # Start new services (configured but not running)
    for entry in $configured_files; do
        local name="${entry%%:*}"
        local file="${entry#*:}"
        if ! echo "$running_services" | grep -qw "$name"; then
            log_info "Starting new service: $name"
            start_service "$file"
        else
            log_info "Keeping running: $name"
        fi
    done
    
    echo ""
    cmd_status
}

cmd_logs() {
    local target="${1:-}"
    
    if [ -n "$target" ]; then
        tail -f "$LOG_DIR/$target.log"
    else
        tail -f "$LOG_DIR"/*.log
    fi
}

cmd_monitor() {
    cmd_start
    
    echo ""
    log_info "Monitoring services (Ctrl+C to stop)..."
    echo ""
    
    trap 'echo ""; cmd_stop; exit 0' INT TERM
    
    while true; do
        sleep 10
        
        for f in $(ls "$SERVICES_DIR"/*.service 2>/dev/null | sort); do
            [ -f "$f" ] || continue
            parse_service_file "$f"
            
            if [ "$RESTART" = "always" ] && ! is_running "$NAME"; then
                log_warn "$NAME crashed, restarting in ${RESTART_DELAY}s..."
                sleep "$RESTART_DELAY"
                start_service "$f"
            fi
        done
    done
}

cmd_help() {
    echo "HA Services Runner"
    echo ""
    echo "Usage: $0 [command] [service]"
    echo ""
    echo "Commands:"
    echo "  (none)     Start all services and monitor"
    echo "  start      Start all services (or single if name given)"
    echo "  stop       Stop all services (or single if name given)"
    echo "  restart    Restart all services (or single if name given)"
    echo "  reload     Start new, stop removed, keep running"
    echo "  status     Show service status"
    echo "  logs       Tail logs (all or single service)"
    echo "  help       Show this help"
    echo ""
    echo "Services directory: $SERVICES_DIR"
    echo ""
}

# === Main ===

if [ ! -d "$SERVICES_DIR" ]; then
    log_error "Services directory not found: $SERVICES_DIR"
    log_info "Create it with: mkdir -p $SERVICES_DIR"
    exit 1
fi

if ! ls "$SERVICES_DIR"/*.service &>/dev/null; then
    log_warn "No .service files found in $SERVICES_DIR"
    exit 1
fi

check_deps() {
    local missing=""
    for f in "$SERVICES_DIR"/*.service; do
        [ -f "$f" ] || continue
        parse_service_file "$f"
        local bin
        bin=$(echo "$CMD" | awk '{print $1}')
        if [ "$TYPE" = "simple" ] && ! command -v "$bin" &>/dev/null; then
            missing="$missing $bin"
        fi
    done
    
    if [ -n "$missing" ]; then
        log_error "Missing dependencies:$missing"
        exit 1
    fi
}

check_deps

command="${1:-}"
target="${2:-}"

case "$command" in
    start)   cmd_start "$target" ;;
    stop)    cmd_stop "$target" ;;
    restart) cmd_restart "$target" ;;
    reload)  cmd_reload ;;
    status)  cmd_status ;;
    logs)    cmd_logs "$target" ;;
    help|-h|--help) cmd_help ;;
    "")      cmd_monitor ;;
    *)
        log_error "Unknown command: $command"
        cmd_help
        exit 1
        ;;
esac
