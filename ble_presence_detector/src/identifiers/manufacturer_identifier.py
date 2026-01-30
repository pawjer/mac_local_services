"""Manufacturer data-based device identifier."""

from .base import BaseIdentifier
from ..core.protocols import BLEAdvertisement
from typing import Optional


class ManufacturerDataIdentifier(BaseIdentifier):
    """Identifies devices by manufacturer-specific data.

    Useful for devices like AirPods that don't always broadcast their name
    but include distinctive manufacturer data.

    Company IDs are registered with the Bluetooth SIG:
    - Apple: 76 (0x004C)
    - Microsoft: 6 (0x0006)
    - Google: 224 (0x00E0)
    """

    def __init__(self, device_id: str, device_name: str, company_id: int,
                 data_pattern: Optional[str] = None):
        """Initialize manufacturer data identifier.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            company_id: Bluetooth company identifier
            data_pattern: Optional hex pattern to match in manufacturer data

        Raises:
            ValueError: If data_pattern is not valid hex
        """
        super().__init__(device_id, device_name)
        self._company_id = company_id
        self._data_pattern = data_pattern

        if data_pattern:
            try:
                self._pattern_bytes = bytes.fromhex(data_pattern)
            except ValueError as e:
                raise ValueError(f"Invalid hex pattern '{data_pattern}': {e}")
        else:
            self._pattern_bytes = None

    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement has matching manufacturer data.

        Args:
            advertisement: BLE advertisement data

        Returns:
            True if manufacturer data matches
        """
        if self._company_id not in advertisement.manufacturer_data:
            return False

        if self._pattern_bytes is None:
            return True

        manufacturer_bytes = advertisement.manufacturer_data[self._company_id]
        return self._pattern_bytes in manufacturer_bytes

    def __repr__(self) -> str:
        """String representation for debugging."""
        pattern_str = f", pattern='{self._data_pattern}'" if self._data_pattern else ""
        return f"ManufacturerDataIdentifier(device_id='{self._device_id}', company_id={self._company_id}{pattern_str})"
