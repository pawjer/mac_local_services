"""Core protocols and interfaces for BLE presence detection system.

This module defines all the core interfaces that components must implement,
following the Dependency Inversion Principle.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Dict, Any, Optional, List, Callable
from abc import abstractmethod


@dataclass(frozen=True)
class BLEAdvertisement:
    """Immutable BLE advertisement data.

    Attributes:
        address: MAC address of the device (normalized to lowercase with colons)
        name: Advertised device name (if available)
        rssi: Received Signal Strength Indicator in dBm
        manufacturer_data: Raw manufacturer-specific data keyed by company ID
        service_uuids: List of advertised service UUIDs
        service_data: Service-specific data keyed by UUID
        tx_power: Advertised transmission power (if available)
        timestamp: When this advertisement was received
    """
    address: str
    name: Optional[str]
    rssi: int
    manufacturer_data: Dict[int, bytes]
    service_uuids: List[str]
    service_data: Dict[str, bytes]
    tx_power: Optional[int]
    timestamp: datetime


class DeviceIdentifier(Protocol):
    """Protocol for device identification strategies.

    Implementations use different methods to identify devices:
    - Name-based matching (exact or regex)
    - MAC address matching
    - Manufacturer data patterns (e.g., AirPods)
    - Service UUID presence
    """

    @abstractmethod
    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement matches this device.

        Args:
            advertisement: BLE advertisement data to check

        Returns:
            True if advertisement is from this device
        """
        ...

    @abstractmethod
    def get_device_id(self) -> str:
        """Get the unique device identifier.

        Returns:
            Device ID string
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the human-readable device name.

        Returns:
            Device name string
        """
        ...


class StateRepository(Protocol):
    """Protocol for persisting device presence states.

    Implementations can use different storage backends (JSON, Redis, SQLite, etc.)
    while maintaining the same interface.
    """

    @abstractmethod
    async def save(self, device_id: str, state: Any) -> None:
        """Save a device's presence state.

        Args:
            device_id: Unique device identifier
            state: DevicePresenceState to persist
        """
        ...

    @abstractmethod
    async def load(self, device_id: str) -> Optional[Any]:
        """Load a device's presence state.

        Args:
            device_id: Unique device identifier

        Returns:
            DevicePresenceState if found, None otherwise
        """
        ...

    @abstractmethod
    async def load_all(self) -> Dict[str, Any]:
        """Load all persisted device states.

        Returns:
            Dictionary mapping device IDs to DevicePresenceStates
        """
        ...


class StateObserver(Protocol):
    """Protocol for observing device presence state changes.

    Observers are notified when a device transitions between present/absent states.
    Common implementations include MQTT publishers, webhooks, logging, etc.
    """

    @abstractmethod
    async def on_state_change(self, device_id: str, old_state: Any, new_state: Any) -> None:
        """Called when device presence state changes.

        Args:
            device_id: Unique device identifier
            old_state: Previous DevicePresenceState
            new_state: New DevicePresenceState
        """
        ...


AdvertisementCallback = Callable[[BLEAdvertisement], None]
"""Type alias for BLE advertisement callback functions."""
