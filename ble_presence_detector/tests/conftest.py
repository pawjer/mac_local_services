"""Pytest fixtures for testing."""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict

from src.core.protocols import BLEAdvertisement
from src.config.models import (
    DeviceConfig, NameIdentifierConfig, MACIdentifierConfig,
    ManufacturerIdentifierConfig, ServiceUUIDIdentifierConfig
)


@pytest.fixture
def sample_advertisement() -> BLEAdvertisement:
    """Create a sample BLE advertisement for testing."""
    return BLEAdvertisement(
        address="aa:bb:cc:dd:ee:ff",
        name="Test Device",
        rssi=-65,
        manufacturer_data={76: bytes.fromhex("0719010203")},
        service_uuids=["00001818-0000-1000-8000-00805f9b34fb"],
        service_data={},
        tx_power=-59,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_device_config() -> DeviceConfig:
    """Create a sample device configuration."""
    return DeviceConfig(
        id="test_device",
        name="Test Device",
        identifiers=[
            NameIdentifierConfig(pattern="Test Device", regex=False)
        ],
        confidence_threshold=0.5,
        decay_rate=0.1
    )


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    """Create a temporary state file path."""
    return tmp_path / "state.json"


@pytest.fixture
def name_identifier_config() -> NameIdentifierConfig:
    """Create a name identifier config."""
    return NameIdentifierConfig(pattern="iPhone", regex=False)


@pytest.fixture
def mac_identifier_config() -> MACIdentifierConfig:
    """Create a MAC identifier config."""
    return MACIdentifierConfig(address="AA:BB:CC:DD:EE:FF")


@pytest.fixture
def manufacturer_identifier_config() -> ManufacturerIdentifierConfig:
    """Create a manufacturer identifier config."""
    return ManufacturerIdentifierConfig(company_id=76, data_pattern="0719")


@pytest.fixture
def service_uuid_identifier_config() -> ServiceUUIDIdentifierConfig:
    """Create a service UUID identifier config."""
    return ServiceUUIDIdentifierConfig(
        uuids=["00001818-0000-1000-8000-00805f9b34fb"],
        require_all=False
    )
