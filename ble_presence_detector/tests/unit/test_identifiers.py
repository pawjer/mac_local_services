"""Unit tests for device identifiers."""

import pytest
from datetime import datetime

from src.core.protocols import BLEAdvertisement
from src.identifiers.name_identifier import NameBasedIdentifier
from src.identifiers.mac_identifier import MACAddressIdentifier
from src.identifiers.manufacturer_identifier import ManufacturerDataIdentifier
from src.identifiers.service_uuid_identifier import ServiceUUIDIdentifier
from src.identifiers.factory import IdentifierFactory
from src.config.models import DeviceConfig


class TestNameBasedIdentifier:
    """Test name-based identification."""

    def test_exact_match(self):
        """Test exact name matching."""
        identifier = NameBasedIdentifier("test", "Test Device", "iPhone", use_regex=False)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="iPhone",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        identifier = NameBasedIdentifier("test", "Test Device", "iphone", use_regex=False)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="iPhone",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_regex_match(self):
        """Test regex pattern matching."""
        identifier = NameBasedIdentifier("test", "Test Device", "iPhone.*Pro", use_regex=True)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="iPhone 15 Pro",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_no_match(self):
        """Test non-matching name."""
        identifier = NameBasedIdentifier("test", "Test Device", "iPhone", use_regex=False)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Android Phone",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)

    def test_none_name(self):
        """Test advertisement with no name."""
        identifier = NameBasedIdentifier("test", "Test Device", "iPhone", use_regex=False)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name=None,
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)


class TestMACAddressIdentifier:
    """Test MAC address identification."""

    def test_match(self):
        """Test MAC address matching."""
        identifier = MACAddressIdentifier("test", "Test Device", "aa:bb:cc:dd:ee:ff")

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_case_insensitive(self):
        """Test case-insensitive MAC matching."""
        identifier = MACAddressIdentifier("test", "Test Device", "AA:BB:CC:DD:EE:FF")

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_no_match(self):
        """Test non-matching MAC."""
        identifier = MACAddressIdentifier("test", "Test Device", "aa:bb:cc:dd:ee:ff")

        ad = BLEAdvertisement(
            address="11:22:33:44:55:66",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)


class TestManufacturerDataIdentifier:
    """Test manufacturer data identification."""

    def test_company_id_only(self):
        """Test matching by company ID only."""
        identifier = ManufacturerDataIdentifier("test", "Test Device", 76)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={76: bytes.fromhex("0719010203")},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_company_id_with_pattern(self):
        """Test matching by company ID and data pattern."""
        identifier = ManufacturerDataIdentifier("test", "Test Device", 76, "0719")

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={76: bytes.fromhex("0719010203")},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_wrong_company_id(self):
        """Test non-matching company ID."""
        identifier = ManufacturerDataIdentifier("test", "Test Device", 76)

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={6: bytes.fromhex("0719010203")},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)

    def test_wrong_pattern(self):
        """Test non-matching data pattern."""
        identifier = ManufacturerDataIdentifier("test", "Test Device", 76, "0719")

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={76: bytes.fromhex("0820010203")},
            service_uuids=[],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)


class TestServiceUUIDIdentifier:
    """Test service UUID identification."""

    def test_or_logic(self):
        """Test OR logic (any UUID matches)."""
        identifier = ServiceUUIDIdentifier(
            "test", "Test Device",
            ["00001818-0000-1000-8000-00805f9b34fb"],
            require_all=False
        )

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=["00001818-0000-1000-8000-00805f9b34fb", "0000180a-0000-1000-8000-00805f9b34fb"],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_and_logic(self):
        """Test AND logic (all UUIDs must match)."""
        identifier = ServiceUUIDIdentifier(
            "test", "Test Device",
            ["00001818-0000-1000-8000-00805f9b34fb", "0000180a-0000-1000-8000-00805f9b34fb"],
            require_all=True
        )

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=["00001818-0000-1000-8000-00805f9b34fb", "0000180a-0000-1000-8000-00805f9b34fb"],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert identifier.matches(ad)

    def test_and_logic_missing_uuid(self):
        """Test AND logic with missing UUID."""
        identifier = ServiceUUIDIdentifier(
            "test", "Test Device",
            ["00001818-0000-1000-8000-00805f9b34fb", "0000180a-0000-1000-8000-00805f9b34fb"],
            require_all=True
        )

        ad = BLEAdvertisement(
            address="aa:bb:cc:dd:ee:ff",
            name="Device",
            rssi=-65,
            manufacturer_data={},
            service_uuids=["00001818-0000-1000-8000-00805f9b34fb"],
            service_data={},
            tx_power=None,
            timestamp=datetime.now()
        )

        assert not identifier.matches(ad)


class TestIdentifierFactory:
    """Test identifier factory."""

    def test_create_name_identifier(self, name_identifier_config):
        """Test creating name identifier."""
        config = DeviceConfig(
            id="test",
            name="Test",
            identifiers=[name_identifier_config],
            confidence_threshold=0.5,
            decay_rate=0.1
        )

        identifiers = IdentifierFactory.create_identifiers(config)
        assert len(identifiers) == 1
        assert isinstance(identifiers[0], NameBasedIdentifier)

    def test_create_multiple_identifiers(self):
        """Test creating multiple identifiers."""
        from src.config.models import NameIdentifierConfig, MACIdentifierConfig

        config = DeviceConfig(
            id="test",
            name="Test",
            identifiers=[
                NameIdentifierConfig(pattern="iPhone", regex=False),
                MACIdentifierConfig(address="AA:BB:CC:DD:EE:FF")
            ],
            confidence_threshold=0.5,
            decay_rate=0.1
        )

        identifiers = IdentifierFactory.create_identifiers(config)
        assert len(identifiers) == 2
