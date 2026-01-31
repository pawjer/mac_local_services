"""MQTT publisher for device presence states."""

import json
import logging
from typing import Optional, List, Tuple
from collections import deque
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

from ..config.models import MQTTConfig
from ..core.protocols import StateObserver
from ..tracking.models import DevicePresenceState
from ..core.exceptions import PublishingError


logger = logging.getLogger(__name__)


class MQTTPublisher(StateObserver):
    """Publishes device presence states to MQTT.

    Implements the Observer pattern - receives notifications from
    PresenceTracker when device states change and publishes to MQTT.

    MQTT Topics:
    - {prefix}/{device_id}/state: "present" or "absent"
    - {prefix}/{device_id}/attributes: JSON with details
    """

    def __init__(self, config: MQTTConfig):
        """Initialize MQTT publisher.

        Args:
            config: MQTT configuration
        """
        self._config = config
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._reconnect_count = 0
        self._pending_messages: deque = deque(maxlen=100)  # Buffer up to 100 messages

        logger.info(f"MQTT publisher initialized for {config.host}:{config.port}")

    async def connect(self) -> None:
        """Connect to MQTT broker.

        Raises:
            PublishingError: If connection fails
        """
        try:
            self._client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=self._config.client_id
            )

            if self._config.username and self._config.password:
                self._client.username_pw_set(
                    self._config.username,
                    self._config.password
                )

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            # Enable automatic reconnection with exponential backoff
            # Min delay: 1 second, Max delay: 120 seconds (2 minutes)
            self._client.reconnect_delay_set(min_delay=1, max_delay=120)

            logger.info(f"Connecting to MQTT broker at {self._config.host}:{self._config.port}")
            self._client.connect(
                self._config.host,
                self._config.port,
                keepalive=60
            )

            self._client.loop_start()

            import asyncio
            for _ in range(50):
                if self._connected:
                    logger.info("Successfully connected to MQTT broker")
                    return
                await asyncio.sleep(0.1)

            raise PublishingError("Failed to connect to MQTT broker (timeout)")

        except Exception as e:
            raise PublishingError(f"Failed to connect to MQTT broker: {e}")

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from MQTT broker")

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def _flush_pending_messages(self) -> None:
        """Publish any messages that were buffered during disconnection."""
        if not self._pending_messages:
            return

        count = len(self._pending_messages)
        logger.info(f"Flushing {count} pending message(s) to MQTT broker")

        while self._pending_messages:
            device_id, state = self._pending_messages.popleft()
            try:
                self._publish_state(device_id, state)
                self._publish_attributes(device_id, state)
                logger.debug(f"Flushed pending message for {device_id}")
            except Exception as e:
                logger.error(f"Failed to flush message for {device_id}: {e}")
                # Re-add to queue if publish fails
                self._pending_messages.append((device_id, state))
                break  # Stop flushing if we hit an error

        if self._pending_messages:
            logger.warning(f"Still have {len(self._pending_messages)} pending message(s)")
        else:
            logger.info("All pending messages flushed successfully")

    async def on_state_change(self, device_id: str,
                             old_state: DevicePresenceState,
                             new_state: DevicePresenceState) -> None:
        """Called when device presence state changes.

        Publishes state and attributes to MQTT. If disconnected, buffers
        the message for later delivery.

        Args:
            device_id: Device ID
            old_state: Previous state
            new_state: New state
        """
        if not self._connected or not self._client:
            # Buffer message for delivery when reconnected
            self._pending_messages.append((device_id, new_state))
            logger.warning(
                f"Not connected to MQTT, buffering state for {device_id} "
                f"({len(self._pending_messages)} pending)"
            )
            return

        try:
            self._publish_state(device_id, new_state)
            self._publish_attributes(device_id, new_state)

            logger.info(
                f"Published state for '{new_state.device_name}' ({device_id}): "
                f"{'present' if new_state.present else 'absent'}"
            )

        except Exception as e:
            logger.error(f"Failed to publish state for {device_id}: {e}", exc_info=True)

    def _publish_state(self, device_id: str, state: DevicePresenceState) -> None:
        """Publish state topic.

        Args:
            device_id: Device ID
            state: Current state
        """
        topic = f"{self._config.topic_prefix}/{device_id}/state"
        payload = "present" if state.present else "absent"

        self._client.publish(
            topic,
            payload,
            qos=self._config.qos,
            retain=True
        )

        logger.debug(f"Published to {topic}: {payload}")

    def _publish_attributes(self, device_id: str, state: DevicePresenceState) -> None:
        """Publish attributes topic with detailed information.

        Args:
            device_id: Device ID
            state: Current state
        """
        topic = f"{self._config.topic_prefix}/{device_id}/attributes"

        attributes = {
            "device_id": state.device_id,
            "device_name": state.device_name,
            "present": state.present,
            "confidence": round(state.confidence, 3),
            "last_seen": state.last_seen.isoformat(),
            "state_changes": state.state_changes
        }

        if state.last_detection:
            attributes["rssi"] = state.last_detection.rssi
            attributes["timestamp"] = state.last_detection.timestamp.isoformat()

            if state.last_detection.distance_estimate is not None:
                attributes["distance_m"] = round(state.last_detection.distance_estimate, 2)

        avg_rssi = state.get_average_rssi()
        if avg_rssi is not None:
            attributes["average_rssi"] = round(avg_rssi, 1)

        avg_distance = state.get_average_distance()
        if avg_distance is not None:
            attributes["average_distance_m"] = round(avg_distance, 2)

        payload = json.dumps(attributes)

        self._client.publish(
            topic,
            payload,
            qos=self._config.qos,
            retain=True
        )

        logger.debug(f"Published to {topic}: {payload}")

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """Called when connected to MQTT broker.

        Args:
            client: MQTT client
            userdata: User data
            flags: Connection flags
            reason_code: Connection result code
            properties: Connection properties
        """
        if reason_code == 0:
            self._connected = True
            if self._reconnect_count > 0:
                logger.info(f"Reconnected to MQTT broker after {self._reconnect_count} attempt(s)")
                self._reconnect_count = 0
            else:
                logger.info("Connected to MQTT broker")

            # Flush any pending messages
            self._flush_pending_messages()
        else:
            self._connected = False
            logger.error(f"Failed to connect to MQTT broker: reason_code={reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        """Called when disconnected from MQTT broker.

        Automatically triggers reconnection with exponential backoff.

        Args:
            client: MQTT client
            userdata: User data
            flags: Disconnect flags
            reason_code: Disconnect reason code
            properties: Disconnect properties
        """
        self._connected = False
        if reason_code == 0:
            logger.info("Cleanly disconnected from MQTT broker")
        else:
            self._reconnect_count += 1
            logger.warning(
                f"Lost connection to MQTT broker (reason_code={reason_code}). "
                f"Auto-reconnect attempt #{self._reconnect_count} starting..."
            )
