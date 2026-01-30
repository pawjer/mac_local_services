"""MAC address-based device identifier."""

from .base import BaseIdentifier
from ..core.protocols import BLEAdvertisement


class MACAddressIdentifier(BaseIdentifier):
    """Identifies devices by their MAC address.

    MAC addresses are normalized to lowercase with colons for comparison.
    """

    def __init__(self, device_id: str, device_name: str, mac_address: str):
        """Initialize MAC address identifier.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            mac_address: MAC address (already normalized by config validator)
        """
        super().__init__(device_id, device_name)
        self._mac_address = mac_address.lower()

    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement MAC matches.

        Args:
            advertisement: BLE advertisement data

        Returns:
            True if MAC address matches
        """
        return advertisement.address.lower() == self._mac_address

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MACAddressIdentifier(device_id='{self._device_id}', mac='{self._mac_address}')"
