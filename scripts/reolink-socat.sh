#!/bin/bash
#
# Reolink socat proxy
# Forwards multiple ports to camera
#
# Environment variables:
#   REOLINK_IP    - Camera IP (required)
#   REOLINK_PORTS - Space-separated "local:remote" pairs
#

set -euo pipefail

REOLINK_IP="${REOLINK_IP:-10.0.0.128}"
REOLINK_PORTS="${REOLINK_PORTS:-18080:80 18554:554 18000:8000 19000:9000}"

# Kill any existing socat for this IP
pkill -9 -f "socat.*$REOLINK_IP" 2>/dev/null || true
sleep 0.5

echo "Starting Reolink proxy for $REOLINK_IP"

PIDS=""

for mapping in $REOLINK_PORTS; do
    local_port="${mapping%%:*}"
    remote_port="${mapping##*:}"
    
    echo "  :$local_port -> $REOLINK_IP:$remote_port"
    socat TCP-LISTEN:$local_port,fork,reuseaddr TCP:$REOLINK_IP:$remote_port &
    PIDS="$PIDS $!"
done

echo "Proxy running (PIDs:$PIDS)"

cleanup() {
    echo "Stopping socat processes..."
    for pid in $PIDS; do
        kill "$pid" 2>/dev/null || true
    done
}

trap cleanup EXIT INT TERM

wait
