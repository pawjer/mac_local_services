#!/usr/bin/env python3
"""Test script to verify MQTT auto-reconnection.

This script simulates a network interruption and verifies that:
1. Messages are buffered during disconnection
2. Auto-reconnection occurs
3. Buffered messages are flushed on reconnection
"""

import asyncio
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.loader import ConfigLoader
from src.config.models import MQTTConfig
from src.publishing.mqtt_publisher import MQTTPublisher
from src.tracking.models import DevicePresenceState
from datetime import datetime


async def test_reconnect():
    """Test MQTT auto-reconnection."""

    print("=" * 60)
    print("MQTT Auto-Reconnection Test")
    print("=" * 60)
    print()

    # Create test config
    config = MQTTConfig(
        host="10.9.0.3",
        port=1883,
        topic_prefix="home/presence/test",
        qos=1,
        client_id="reconnect_test"
    )

    publisher = MQTTPublisher(config)

    # Test 1: Initial connection
    print("Test 1: Initial Connection")
    print("-" * 40)
    try:
        await publisher.connect()
        print("✓ Connected successfully")
        print(f"✓ Connection status: {publisher.is_connected()}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    print()

    # Test 2: Publish a message while connected
    print("Test 2: Publish While Connected")
    print("-" * 40)
    test_state = DevicePresenceState(
        device_id="test_device",
        device_name="Test Device",
        present=True,
        confidence=1.0,
        last_seen=datetime.now()
    )

    await publisher.on_state_change("test_device", test_state, test_state)
    print("✓ Published test message")
    print()

    # Test 3: Simulate disconnection by publishing while broker is unavailable
    print("Test 3: Simulate Disconnection")
    print("-" * 40)
    print("Note: To fully test, stop the MQTT broker now")
    print("      Messages will be buffered and published on reconnect")
    print()

    # Give user time to stop broker
    print("Waiting 5 seconds...")
    await asyncio.sleep(5)

    # Try to publish while potentially disconnected
    for i in range(3):
        test_state.present = (i % 2 == 0)
        test_state.confidence = 1.0 - (i * 0.2)
        await publisher.on_state_change("test_device", test_state, test_state)
        print(f"  Message {i+1}: present={test_state.present}, confidence={test_state.confidence:.1f}")
        await asyncio.sleep(1)

    print()

    # Test 4: Verify reconnection
    print("Test 4: Auto-Reconnection")
    print("-" * 40)
    print("If broker was stopped, paho-mqtt will auto-reconnect")
    print("Check logs above for reconnection messages")
    print()
    print("Waiting 10 seconds for potential reconnection...")
    await asyncio.sleep(10)

    print(f"Final connection status: {publisher.is_connected()}")
    print()

    # Cleanup
    print("Disconnecting...")
    await publisher.disconnect()
    print()

    print("=" * 60)
    print("Test Complete")
    print("=" * 60)
    print()
    print("What to verify:")
    print("1. Initial connection successful")
    print("2. If broker stopped: messages buffered (check warning logs)")
    print("3. If broker restarted: auto-reconnect happened (check info logs)")
    print("4. Buffered messages flushed on reconnect")
    print()


if __name__ == "__main__":
    asyncio.run(test_reconnect())
