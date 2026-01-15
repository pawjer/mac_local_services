#!/bin/bash
#
# Home Assistant Full Directory Backup
# Backs up entire HA directory with space checking
#
# Environment variables:
#   HA_DIR               - Path to HA directory (default: ~/Devel/HomeAssistant)
#   BACKUP_DIR           - Where to store backups (default: ~/backups/ha-full)
#   BACKUP_INTERVAL_HOURS - Hours between backups (default: 24)
#   BACKUP_KEEP_DAYS     - Days to keep backups (default: 7)
#   MIN_FREE_SPACE_GB    - Minimum free space required in GB (default: 10)
#

set -euo pipefail

HA_DIR="${HA_DIR:-$HOME/Devel/HomeAssistant}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/ha-full}"
BACKUP_INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
MIN_FREE_SPACE_GB="${MIN_FREE_SPACE_GB:-10}"

BACKUP_INTERVAL_SECONDS=$((BACKUP_INTERVAL_HOURS * 3600))
MIN_FREE_SPACE_BYTES=$((MIN_FREE_SPACE_GB * 1024 * 1024 * 1024))

mkdir -p "$BACKUP_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Get free space in bytes (macOS compatible)
get_free_space() {
    local path="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        df -k "$path" | awk 'NR==2 {print $4 * 1024}'
    else
        df -B1 "$path" | awk 'NR==2 {print $4}'
    fi
}

# Get directory size in bytes
get_dir_size() {
    local path="$1"
    du -sk "$path" 2>/dev/null | awk '{print $1 * 1024}'
}

# Format bytes to human readable
format_bytes() {
    local bytes=$1
    if [ $bytes -ge 1073741824 ]; then
        echo "$(echo "scale=1; $bytes / 1073741824" | bc)GB"
    elif [ $bytes -ge 1048576 ]; then
        echo "$(echo "scale=1; $bytes / 1048576" | bc)MB"
    else
        echo "${bytes}B"
    fi
}

check_space() {
    local free_space
    free_space=$(get_free_space "$BACKUP_DIR")
    
    local ha_size
    ha_size=$(get_dir_size "$HA_DIR")
    
    # Estimate compressed size (rough: 30% of original)
    local estimated_backup=$((ha_size * 30 / 100))
    
    # Required: estimated backup + minimum free space
    local required=$((estimated_backup + MIN_FREE_SPACE_BYTES))
    
    log "Space check:"
    log "  HA directory size: $(format_bytes $ha_size)"
    log "  Estimated backup:  $(format_bytes $estimated_backup)"
    log "  Free space:        $(format_bytes $free_space)"
    log "  Min required:      $(format_bytes $MIN_FREE_SPACE_BYTES)"
    
    if [ "$free_space" -lt "$required" ]; then
        log "ERROR: Not enough space! Need $(format_bytes $required), have $(format_bytes $free_space)"
        return 1
    fi
    
    log "  ✓ Space OK"
    return 0
}

do_backup() {
    if [ ! -d "$HA_DIR" ]; then
        log "ERROR: HA directory not found: $HA_DIR"
        return 1
    fi
    
    # Check space first
    if ! check_space; then
        return 1
    fi
    
    local timestamp=$(date '+%Y%m%d-%H%M%S')
    local backup_file="$BACKUP_DIR/ha-full-$timestamp.tar.gz"
    
    log "Creating backup: $(basename "$backup_file")"
    
    # Exclusions
    local excludes=(
        --exclude='*.log'
        --exclude='*.log.*'
        --exclude='.pids'
        --exclude='logs'
        --exclude='backups'
        --exclude='__pycache__'
        --exclude='.cache'
        --exclude='*.pyc'
        --exclude='home-assistant_v2.db-shm'
        --exclude='home-assistant_v2.db-wal'
        --exclude='.git'
        --exclude='node_modules'
        --exclude='core'
    )
    
    local start_time=$(date +%s)
    
    # Create backup
    tar -czf "$backup_file" \
        "${excludes[@]}" \
        -C "$(dirname "$HA_DIR")" \
        "$(basename "$HA_DIR")" 2>/dev/null || {
            log "ERROR: Backup failed"
            rm -f "$backup_file"
            return 1
        }
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local backup_size=$(get_dir_size "$backup_file")
    
    log "✓ Backup complete: $(format_bytes $backup_size) in ${duration}s"
    
    return 0
}

cleanup_old() {
    log "Cleaning backups older than $BACKUP_KEEP_DAYS days..."
    local count=$(find "$BACKUP_DIR" -name "ha-full-*.tar.gz" -mtime +$BACKUP_KEEP_DAYS -type f 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$count" -gt 0 ]; then
        find "$BACKUP_DIR" -name "ha-full-*.tar.gz" -mtime +$BACKUP_KEEP_DAYS -type f -delete
        log "Removed $count old backup(s)"
    fi
}

show_status() {
    echo ""
    log "=== Backup Status ==="
    
    local count=$(ls -1 "$BACKUP_DIR"/ha-full-*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$count" -eq 0 ]; then
        log "No backups found"
        return
    fi
    
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local free_space=$(get_free_space "$BACKUP_DIR")
    
    log "Backups: $count files, $total_size total"
    log "Free space: $(format_bytes $free_space)"
    echo ""
    
    log "Recent backups:"
    ls -lht "$BACKUP_DIR"/ha-full-*.tar.gz 2>/dev/null | head -5 | while read line; do
        echo "  $line"
    done
}

# === Main ===

log "=== HA Full Backup Service ==="
log "HA directory: $HA_DIR"
log "Backup dir:   $BACKUP_DIR"
log "Interval:     ${BACKUP_INTERVAL_HOURS}h"
log "Retention:    ${BACKUP_KEEP_DAYS} days"
log "Min free:     ${MIN_FREE_SPACE_GB}GB"
echo ""

# Initial backup
do_backup || true
cleanup_old
show_status
echo ""

log "Running backup loop (Ctrl+C to stop)..."

while true; do
    sleep "$BACKUP_INTERVAL_SECONDS"
    echo ""
    log "=== Scheduled backup ==="
    do_backup || true
    cleanup_old
    show_status
done
