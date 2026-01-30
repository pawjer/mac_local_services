"""Integration tests for full system flow."""

import pytest
from datetime import datetime
from pathlib import Path

from src.core.protocols import BLEAdvertisement
from src.config.models import DeviceConfig, NameIdentifierConfig
from src.identifiers.factory import IdentifierFactory
from src.tracking.presence_tracker import PresenceTracker
from src.repository.json_repository import JSONStateRepository


@pytest.mark.asyncio
async def test_end_to_end_flow(temp_state_file):
    """Test advertisement -> identification -> tracking -> persistence."""

    config = DeviceConfig(
        id="test_device",
        name="Test Device",
        identifiers=[
            NameIdentifierConfig(pattern="iPhone", regex=False)
        ],
        confidence_threshold=0.5,
        decay_rate=0.1
    )

    identifiers_map = {
        config.id: IdentifierFactory.create_identifiers(config)
    }

    tracker = PresenceTracker(
        device_configs=[config],
        identifiers_map=identifiers_map
    )

    repository = JSONStateRepository(temp_state_file)

    advertisement = BLEAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        name="iPhone",
        rssi=-65,
        manufacturer_data={},
        service_uuids=[],
        service_data={},
        tx_power=-59,
        timestamp=datetime.now()
    )

    await tracker.process_advertisement(advertisement)

    state = tracker.get_state("test_device")
    assert state is not None
    assert state.confidence == 1.0
    assert state.last_detection is not None
    assert state.last_detection.rssi == -65

    await repository.save("test_device", state)

    loaded_state = await repository.load("test_device")
    assert loaded_state is not None
    assert loaded_state.device_id == "test_device"
    assert loaded_state.confidence == 1.0


@pytest.mark.asyncio
async def test_state_persistence(temp_state_file):
    """Test state persistence and restoration."""
    from src.tracking.models import DevicePresenceState

    repository = JSONStateRepository(temp_state_file)

    state = DevicePresenceState(
        device_id="test",
        device_name="Test Device",
        present=True,
        confidence=0.8,
        last_seen=datetime.now()
    )

    state.add_detection(rssi=-65)

    await repository.save("test", state)

    loaded = await repository.load("test")

    assert loaded.device_id == state.device_id
    assert loaded.device_name == state.device_name
    assert loaded.present == state.present
    assert abs(loaded.confidence - state.confidence) < 0.001


@pytest.mark.asyncio
async def test_multiple_identifiers(temp_state_file):
    """Test device with multiple identification strategies."""
    from src.config.models import MACIdentifierConfig

    config = DeviceConfig(
        id="test_device",
        name="Test Device",
        identifiers=[
            NameIdentifierConfig(pattern="iPhone", regex=False),
            MACIdentifierConfig(address="aa:bb:cc:dd:ee:ff")
        ],
        confidence_threshold=0.5,
        decay_rate=0.1
    )

    identifiers_map = {
        config.id: IdentifierFactory.create_identifiers(config)
    }

    tracker = PresenceTracker(
        device_configs=[config],
        identifiers_map=identifiers_map
    )

    ad_by_name = BLEAdvertisement(
        address="11:22:33:44:55:66",
        name="iPhone",
        rssi=-65,
        manufacturer_data={},
        service_uuids=[],
        service_data={},
        tx_power=-59,
        timestamp=datetime.now()
    )

    await tracker.process_advertisement(ad_by_name)
    state = tracker.get_state("test_device")
    assert state.confidence == 1.0

    ad_by_mac = BLEAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        name="Unknown Device",
        rssi=-70,
        manufacturer_data={},
        service_uuids=[],
        service_data={},
        tx_power=-59,
        timestamp=datetime.now()
    )

    await tracker.process_advertisement(ad_by_mac)
    state = tracker.get_state("test_device")
    assert state.confidence == 1.0
