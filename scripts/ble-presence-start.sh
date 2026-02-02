#!/bin/bash
#
# BLE Presence Detector starter
# Tracks BLE devices and publishes presence to MQTT
#

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BLE_DIR="$PROJECT_ROOT/ble_presence_detector"

# Configuration with defaults
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_TOPIC_PREFIX="${MQTT_TOPIC_PREFIX:-home/presence}"
MQTT_QOS="${MQTT_QOS:-1}"
MQTT_CLIENT_ID="${MQTT_CLIENT_ID:-ble_presence_detector}"
SCAN_INTERVAL="${SCAN_INTERVAL:-5.0}"
SCAN_DURATION="${SCAN_DURATION:-3.0}"
STATE_FILE="${STATE_FILE:-state.json}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "Starting BLE Presence Detector..."
echo "  MQTT: $MQTT_HOST:$MQTT_PORT"
echo "  Topic prefix: $MQTT_TOPIC_PREFIX"
echo "  Scan: ${SCAN_INTERVAL}s interval, ${SCAN_DURATION}s duration"
echo "  Log level: $LOG_LEVEL"

cd "$BLE_DIR"

exec ./venv/bin/python -m src.main config/devices.yaml
