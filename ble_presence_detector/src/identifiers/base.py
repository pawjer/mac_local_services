"""Base class for device identifiers."""

from abc import ABC, abstractmethod
from ..core.protocols import BLEAdvertisement, DeviceIdentifier


class BaseIdentifier(ABC, DeviceIdentifier):
    """Abstract base class for device identification strategies.

    This implements the Strategy pattern, allowing different identification
    methods to be used interchangeably. All identifiers must implement the
    matches() method to determine if a BLE advertisement is from their device.

    Attributes:
        device_id: Unique identifier for the device
        device_name: Human-readable device name
    """

    def __init__(self, device_id: str, device_name: str):
        """Initialize the identifier.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
        """
        self._device_id = device_id
        self._device_name = device_name

    @abstractmethod
    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement matches this device.

        Args:
            advertisement: BLE advertisement data to check

        Returns:
            True if advertisement is from this device
        """
        pass

    def get_device_id(self) -> str:
        """Get the unique device identifier.

        Returns:
            Device ID string
        """
        return self._device_id

    def get_name(self) -> str:
        """Get the human-readable device name.

        Returns:
            Device name string
        """
        return self._device_name

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(device_id='{self._device_id}', device_name='{self._device_name}')"
