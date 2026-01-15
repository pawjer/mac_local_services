#!/bin/bash
#
# Home Assistant Database Rolling Backup
# Backs up home-assistant_v2.db with rotation
#
# Environment variables:
#   HA_CONFIG            - Path to HA config (default: /Users/proboszcz/Devel/HomeAssistant/config)
#   BACKUP_DIR           - Where to store backups (default: ~/backups/ha-db)
#   BACKUP_INTERVAL_HOURS - Hours between backups (default: 1)
#   BACKUP_KEEP_DAYS     - Days to keep backups (default: 7)
#

set -euo pipefail

HA_CONFIG="${HA_CONFIG:-/Users/proboszcz/Devel/HomeAssistant/config}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/ha-db}"
BACKUP_INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-1}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

BACKUP_INTERVAL_SECONDS=$((BACKUP_INTERVAL_HOURS * 3600))

DB_FILE="$HA_CONFIG/home-assistant_v2.db"

mkdir -p "$BACKUP_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

do_backup() {
    if [ ! -f "$DB_FILE" ]; then
        log "WARN: Database not found: $DB_FILE"
        return 1
    fi
    
    local timestamp=$(date '+%Y%m%d-%H%M%S')
    local backup_file="$BACKUP_DIR/ha-db-$timestamp.db"
    local size_before=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE" 2>/dev/null)
    
    log "Backing up database ($(numfmt --to=iec $size_before 2>/dev/null || echo "${size_before}B"))..."
    
    # Use sqlite3 backup if available (safer), otherwise cp
    if command -v sqlite3 &>/dev/null; then
        sqlite3 "$DB_FILE" ".backup '$backup_file'"
    else
        cp "$DB_FILE" "$backup_file"
    fi
    
    # Compress
    if command -v gzip &>/dev/null; then
        gzip "$backup_file"
        backup_file="$backup_file.gz"
    fi
    
    local size_after=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
    log "OK: $(basename "$backup_file") ($(numfmt --to=iec $size_after 2>/dev/null || echo "${size_after}B"))"
    
    return 0
}

cleanup_old() {
    log "Cleaning backups older than $BACKUP_KEEP_DAYS days..."
    local count=$(find "$BACKUP_DIR" -name "ha-db-*.db*" -mtime +$BACKUP_KEEP_DAYS -type f | wc -l | tr -d ' ')
    
    if [ "$count" -gt 0 ]; then
        find "$BACKUP_DIR" -name "ha-db-*.db*" -mtime +$BACKUP_KEEP_DAYS -type f -delete
        log "Removed $count old backup(s)"
    fi
}

show_status() {
    local count=$(ls -1 "$BACKUP_DIR"/ha-db-*.db* 2>/dev/null | wc -l | tr -d ' ')
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local oldest=$(ls -1t "$BACKUP_DIR"/ha-db-*.db* 2>/dev/null | tail -1 | xargs basename 2>/dev/null || echo "none")
    local newest=$(ls -1t "$BACKUP_DIR"/ha-db-*.db* 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "none")
    
    log "Status: $count backups, $total_size total"
    log "  Oldest: $oldest"
    log "  Newest: $newest"
}

# === Main ===

log "=== HA Database Backup Service ==="
log "Database: $DB_FILE"
log "Backup dir: $BACKUP_DIR"
log "Interval: ${BACKUP_INTERVAL_HOURS}h"
log "Retention: ${BACKUP_KEEP_DAYS} days"
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
    do_backup || true
    cleanup_old
done
