#!/bin/bash
#
# Spotify BT Control Script
# Wrapper for blueutil + AppleScript
#
# Usage:
#   ./spotify-bt-control.sh list                    # List paired audio devices
#   ./spotify-bt-control.sh connect <mac>           # Connect to device
#   ./spotify-bt-control.sh disconnect <mac>        # Disconnect device
#   ./spotify-bt-control.sh status                  # BT connection status
#   ./spotify-bt-control.sh spotify-play            # Play/resume Spotify
#   ./spotify-bt-control.sh spotify-pause           # Pause Spotify
#   ./spotify-bt-control.sh spotify-status          # Spotify status
#

set -euo pipefail

# === Configuration from ENV ===
BT_CONNECT_TIMEOUT="${BT_CONNECT_TIMEOUT:-5}"
BT_CONNECT_WAIT="${BT_CONNECT_WAIT:-2}"
BT_DISCONNECT_TIMEOUT="${BT_DISCONNECT_TIMEOUT:-3}"
SPOTIFY_LAUNCH_DELAY="${SPOTIFY_LAUNCH_DELAY:-2}"

# Audio device filter keywords (comma-separated)
# Default keywords if not set in ENV
AUDIO_DEVICE_KEYWORDS="${AUDIO_DEVICE_KEYWORDS:-speaker,headphone,headset,earphone,earbud,airpod,beats,jbl,bose,sony,soundbar,audio,music,soundcore,liberty,wh-,wf-,anker,jabra,sennheiser,marshall}"

# === Audio device detection heuristics ===
is_audio_device() {
    local name="$1"
    local name_lower
    name_lower=$(echo "$name" | tr '[:upper:]' '[:lower:]')
    
    # Check for common audio device keywords
    if [[ "$name_lower" =~ (speaker|headphone|headset|earphone|earbud|airpod|beats|jbl|bose|sony|soundbar|audio|music) ]]; then
        return 0
    fi
    
    return 1
}

# === Bluetooth Operations ===

cmd_list() {
    # Get paired devices from blueutil
    local devices
    devices=$(blueutil --paired --format json 2>/dev/null || echo "[]")
    
    # Parse and filter audio devices using keywords from ENV
    echo "$devices" | python3 -c "
import sys, json

# Get keywords from bash ENV variable
keywords_str = '''$AUDIO_DEVICE_KEYWORDS'''
keywords = [k.strip().lower() for k in keywords_str.split(',')]

try:
    devices = json.load(sys.stdin)
    audio_devices = []
    
    for device in devices:
        name = device.get('name', 'Unknown')
        address = device.get('address', '')
        connected = device.get('connected', False)
        
        # Check if name contains any keyword
        name_lower = name.lower()
        is_audio = any(keyword in name_lower for keyword in keywords)
        
        if is_audio:
            audio_devices.append({
                'address': address,
                'name': name,
                'connected': connected
            })
    
    print(json.dumps(audio_devices, indent=2))
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
"
}

cmd_connect() {
    local mac="${1:-}"

    if [ -z "$mac" ]; then
        echo '{"error": "MAC address required"}' >&2
        exit 1
    fi

    # Normalize MAC address for comparison (uppercase with colons)
    local mac_normalized
    mac_normalized=$(echo "$mac" | tr '[:lower:]' '[:upper:]' | tr '-' ':')

    # DEBUG: Log environment and input
    echo "DEBUG: BLUEUTIL_USE_SYSTEM_PROFILER=$BLUEUTIL_USE_SYSTEM_PROFILER" >&2
    echo "DEBUG: Input MAC: $mac" >&2
    echo "DEBUG: Normalized MAC: $mac_normalized" >&2

    # Check if device is paired using JSON format
    local paired_devices
    paired_devices=$(blueutil --paired --format json 2>&1)

    # DEBUG: Log blueutil output
    echo "DEBUG: blueutil output: $paired_devices" >&2

    if ! echo "$paired_devices" | python3 -c "
import sys, json
try:
    devices = json.load(sys.stdin)
    target_mac = '''$mac_normalized'''
    print(f'DEBUG: Parsed {len(devices)} devices', file=sys.stderr)
    print(f'DEBUG: Looking for: {target_mac}', file=sys.stderr)
    for d in devices:
        addr = d.get('address', '').upper()
        print(f'DEBUG: Found device: {addr}', file=sys.stderr)
    found = any(d.get('address', '').upper() == target_mac for d in devices)
    print(f'DEBUG: Match found: {found}', file=sys.stderr)
    sys.exit(0 if found else 1)
except Exception as e:
    print(f'DEBUG: Python error: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"; then
        echo "{\"error\": \"Device $mac_normalized not paired\"}" >&2
        exit 1
    fi

    # Format MAC address for blueutil commands (lowercase with dashes)
    mac=$(echo "$mac_normalized" | tr '[:upper:]' '[:lower:]' | tr ':' '-')
    
    # Connect
    if blueutil --connect "$mac" 2>/dev/null; then
        # Wait a bit for connection to establish
        sleep "$BT_CONNECT_WAIT"
        
        # Verify connection
        if blueutil --is-connected "$mac" 2>/dev/null | grep -q "1"; then
            echo "{\"success\": true, \"address\": \"$mac\", \"connected\": true}"
        else
            echo "{\"success\": false, \"address\": \"$mac\", \"error\": \"Connection failed\"}" >&2
            exit 1
        fi
    else
        echo "{\"error\": \"Failed to connect to $mac\"}" >&2
        exit 1
    fi
}

cmd_disconnect() {
    local mac="${1:-}"

    if [ -z "$mac" ]; then
        echo '{"error": "MAC address required"}' >&2
        exit 1
    fi

    # Normalize and format MAC address for blueutil commands (lowercase with dashes)
    mac=$(echo "$mac" | tr '[:upper:]' '[:lower:]' | tr ':' '-')
    
    # Disconnect
    if blueutil --disconnect "$mac" 2>/dev/null; then
        echo "{\"success\": true, \"address\": \"$mac\", \"connected\": false}"
    else
        echo "{\"error\": \"Failed to disconnect $mac\"}" >&2
        exit 1
    fi
}

cmd_status() {
    # Get all connected devices
    local devices
    devices=$(blueutil --connected --format json 2>/dev/null || echo "[]")
    
    echo "$devices" | python3 -c "
import sys, json

try:
    devices = json.load(sys.stdin)
    connected = []
    
    for device in devices:
        connected.append({
            'address': device.get('address', ''),
            'name': device.get('name', 'Unknown'),
            'connected': True
        })
    
    print(json.dumps({'connected_devices': connected}, indent=2))
except Exception as e:
    print(json.dumps({'error': str(e)}), file=sys.stderr)
    sys.exit(1)
"
}

# === Spotify Operations ===

cmd_spotify_play() {
    osascript -e "tell application \"Spotify\"
        if it is not running then
            launch
            delay $SPOTIFY_LAUNCH_DELAY
        end if
        
        if player state is paused or player state is stopped then
            play
        end if
    end tell" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo '{"success": true, "state": "playing"}'
    else
        echo '{"error": "Failed to control Spotify"}' >&2
        exit 1
    fi
}

cmd_spotify_pause() {
    osascript -e 'tell application "Spotify"
        if it is running then
            pause
        end if
    end tell' 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo '{"success": true, "state": "paused"}'
    else
        echo '{"error": "Failed to pause Spotify"}' >&2
        exit 1
    fi
}

cmd_spotify_status() {
    local status
    status=$(osascript -e 'tell application "Spotify"
        if it is not running then
            return "not_running"
        end if
        
        set playerState to player state as string
        set trackName to ""
        set artistName to ""
        set albumName to ""
        
        if playerState is not "stopped" then
            try
                set trackName to name of current track
                set artistName to artist of current track
                set albumName to album of current track
            end try
        end if
        
        return playerState & "|" & trackName & "|" & artistName & "|" & albumName
    end tell' 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo '{"running": false, "state": "not_running"}'
        exit 0
    fi
    
    # Parse the result
    IFS='|' read -r state track artist album <<< "$status"
    
    python3 -c "
import sys, json

state = '''$state'''.strip()
track = '''$track'''.strip()
artist = '''$artist'''.strip()
album = '''$album'''.strip()

result = {
    'running': state != 'not_running',
    'state': state
}

if track:
    result['track'] = {
        'name': track,
        'artist': artist,
        'album': album
    }

print(json.dumps(result, indent=2))
"
}

# === Main ===

command="${1:-}"

case "$command" in
    list)
        cmd_list
        ;;
    connect)
        cmd_connect "${2:-}"
        ;;
    disconnect)
        cmd_disconnect "${2:-}"
        ;;
    status)
        cmd_status
        ;;
    spotify-play)
        cmd_spotify_play
        ;;
    spotify-pause)
        cmd_spotify_pause
        ;;
    spotify-status)
        cmd_spotify_status
        ;;
    *)
        echo "Usage: $0 {list|connect|disconnect|status|spotify-play|spotify-pause|spotify-status}" >&2
        exit 1
        ;;
esac
