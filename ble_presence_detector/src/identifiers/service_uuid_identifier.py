"""Service UUID-based device identifier."""

from typing import List
from .base import BaseIdentifier
from ..core.protocols import BLEAdvertisement


class ServiceUUIDIdentifier(BaseIdentifier):
    """Identifies devices by advertised service UUIDs.

    Can require all specified UUIDs (AND logic) or any UUID (OR logic).

    Common service UUIDs:
    - Heart Rate: 0x180D
    - Cycling Speed and Cadence: 0x1816
    - Cycling Power: 0x1818
    - Fitness Machine: 0x1826
    """

    def __init__(self, device_id: str, device_name: str, uuids: List[str],
                 require_all: bool = False):
        """Initialize service UUID identifier.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            uuids: List of service UUIDs to match (already normalized to lowercase)
            require_all: If True, all UUIDs must be present (AND). If False, any UUID (OR).
        """
        super().__init__(device_id, device_name)
        self._uuids = set(uuid.lower() for uuid in uuids)
        self._require_all = require_all

    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement has matching service UUIDs.

        Args:
            advertisement: BLE advertisement data

        Returns:
            True if service UUIDs match according to require_all setting
        """
        if not advertisement.service_uuids:
            return False

        advertised_uuids = set(uuid.lower() for uuid in advertisement.service_uuids)

        if self._require_all:
            return self._uuids.issubset(advertised_uuids)
        else:
            return bool(self._uuids.intersection(advertised_uuids))

    def __repr__(self) -> str:
        """String representation for debugging."""
        logic = "AND" if self._require_all else "OR"
        uuids_str = ", ".join(self._uuids)
        return f"ServiceUUIDIdentifier(device_id='{self._device_id}', uuids=[{uuids_str}], logic={logic})"
