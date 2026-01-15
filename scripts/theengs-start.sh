#!/bin/bash
#
# TheengsGateway starter
# Uses THEENGS_BINDKEYS from environment
#

set -euo pipefail

MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_TOPIC="${MQTT_TOPIC:-home/TheengsGateway}"

CMD="TheengsGateway -H $MQTT_HOST -P $MQTT_PORT -pt $MQTT_TOPIC"

# Add bindkeys if set
if [ -n "${THEENGS_BINDKEYS:-}" ]; then
    CMD="$CMD -b '$THEENGS_BINDKEYS'"
fi

echo "Starting TheengsGateway..."
echo "  MQTT: $MQTT_HOST:$MQTT_PORT"
echo "  Topic: $MQTT_TOPIC"
[ -n "${THEENGS_BINDKEYS:-}" ] && echo "  Bindkeys: configured"

eval exec $CMD
